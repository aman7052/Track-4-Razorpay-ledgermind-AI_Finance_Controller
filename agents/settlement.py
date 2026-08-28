from typing import Optional
from schemas.models import (
    InvoiceData, 
    ReconciliationReport, 
    AnomalyRiskReport, 
    SettlementPlan
)
from services.razorpay_mock import RazorpayMockService
from services.email_service import DisputeEmailService
from database.db import get_db_cursor

class SettlementAgent:
    """
    Agent 4: Autonomous Financial Decision & Settlement Engine.
    Triggers RazorpayX Payouts for clean invoices or auto-drafts itemized disputes for flagged invoices.
    """
    def __init__(self, razorpay_service: Optional[RazorpayMockService] = None):
        self.razorpay_service = razorpay_service or RazorpayMockService()

    def process_settlement(
        self,
        invoice: InvoiceData,
        recon_report: ReconciliationReport,
        risk_report: AnomalyRiskReport,
        auto_payout_threshold: float = 20.0
    ) -> SettlementPlan:
        # Determine vendor category from DB if available
        vendor_category = "IT_SERVICES"
        vendor_email = "accounts@vendor.com"
        db_bank_acct = invoice.bank_account_no or ""
        db_ifsc = invoice.ifsc_code or ""

        if recon_report.vendor_id:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT * FROM vendors WHERE id = ?", (recon_report.vendor_id,))
                v_row = cursor.fetchone()
                if v_row:
                    vendor_category = v_row["category"]
                    vendor_email = v_row["email"]
                    db_bank_acct = v_row["bank_account"]
                    db_ifsc = v_row["ifsc"]

        # Calculate standard TDS
        section, rate, tds_amount, net_payable = self.razorpay_service.calculate_tds(
            invoice.total_amount, vendor_category
        )

        # 1. Condition for Autonomous Payout
        is_clean_match = (recon_report.status == "PERFECT_MATCH" or recon_report.is_reconciled)
        is_low_risk = (risk_report.overall_risk_score < auto_payout_threshold)

        if is_clean_match and is_low_risk:
            # Record in audit ledger first
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO audit_ledger (
                        invoice_no, vendor_id, matched_po_id, audit_status, variance_amount, risk_score, settlement_status, action_taken, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice.invoice_number,
                    recon_report.vendor_id,
                    recon_report.matched_po_id,
                    "PERFECT_MATCH",
                    0.0,
                    risk_report.overall_risk_score,
                    "PROCESSING",
                    "AUTO_PAYOUT_TRIGGERED",
                    f"Approved autonomously (Risk Score: {risk_report.overall_risk_score}/100)"
                ))

            # Execute Simulated Razorpay Payout
            payout_resp = self.razorpay_service.create_payout(
                invoice_no=invoice.invoice_number,
                vendor_id=recon_report.vendor_id or 1,
                vendor_name=recon_report.vendor_name,
                bank_account=db_bank_acct,
                ifsc=db_ifsc,
                gross_amount=invoice.total_amount,
                vendor_category=vendor_category,
                mode="IMPS"
            )

            return SettlementPlan(
                invoice_number=invoice.invoice_number,
                decision="AUTO_PAYOUT_TRIGGERED",
                gross_amount=invoice.total_amount,
                tds_section=section,
                tds_rate_pct=rate,
                tds_deduction_amount=tds_amount,
                net_payable_amount=net_payable,
                payout_response=payout_resp,
                dispute_email_draft=None,
                dispute_reason=None
            )

        # 2. Condition for Fraud / Duplicate Blocking
        elif risk_report.is_duplicate:
            reason = f"Duplicate invoice: already settled in ledger (Risk Score: {risk_report.overall_risk_score}/100)"
            
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO audit_ledger (
                        invoice_no, vendor_id, matched_po_id, audit_status, variance_amount, risk_score, settlement_status, action_taken, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice.invoice_number,
                    recon_report.vendor_id,
                    recon_report.matched_po_id,
                    "DUPLICATE_INVOICE",
                    invoice.total_amount,
                    risk_report.overall_risk_score,
                    "BLOCKED_DUPLICATE",
                    "FRAUD_PREVENTION_BLOCKED",
                    reason
                ))

            email_draft = DisputeEmailService.generate_dispute_email(
                recon_report=recon_report,
                risk_report=risk_report,
                vendor_email=vendor_email
            )

            return SettlementPlan(
                invoice_number=invoice.invoice_number,
                decision="HOLD_FOR_CFO_REVIEW",
                gross_amount=invoice.total_amount,
                tds_section=section,
                tds_rate_pct=rate,
                tds_deduction_amount=tds_amount,
                net_payable_amount=net_payable,
                payout_response=None,
                dispute_email_draft=email_draft,
                dispute_reason=reason
            )

        # 3. Condition for Rate/Qty Mismatch or High Risk
        else:
            reason = f"Reconciliation discrepancy ({recon_report.status}, Variance: ₹{recon_report.net_variance_amount:+,.2f}, Risk: {risk_report.overall_risk_score}/100)"
            
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO audit_ledger (
                        invoice_no, vendor_id, matched_po_id, audit_status, variance_amount, risk_score, settlement_status, action_taken, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice.invoice_number,
                    recon_report.vendor_id,
                    recon_report.matched_po_id,
                    recon_report.status,
                    recon_report.net_variance_amount,
                    risk_report.overall_risk_score,
                    "DISPUTED",
                    "DISPUTE_RAISED",
                    reason
                ))

            email_draft = DisputeEmailService.generate_dispute_email(
                recon_report=recon_report,
                risk_report=risk_report,
                vendor_email=vendor_email
            )

            return SettlementPlan(
                invoice_number=invoice.invoice_number,
                decision="DISPUTE_RAISED",
                gross_amount=invoice.total_amount,
                tds_section=section,
                tds_rate_pct=rate,
                tds_deduction_amount=tds_amount,
                net_payable_amount=net_payable,
                payout_response=None,
                dispute_email_draft=email_draft,
                dispute_reason=reason
            )
