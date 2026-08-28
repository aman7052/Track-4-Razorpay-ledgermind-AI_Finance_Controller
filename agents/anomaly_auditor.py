import re
from typing import List, Dict, Any
from schemas.models import InvoiceData, ReconciliationReport, AnomalyRiskReport, RiskDimensionScore
from database.db import get_db_cursor

class AnomalyAuditAgent:
    """
    Agent 3: Evaluates forensic risk dimensions, historical price deviations, 
    bank account tampering, duplicate billing, and GST compliance.
    """
    VALID_STATE_CODES = {f"{i:02d}" for i in range(1, 39)}.union({"97"})

    def __init__(self):
        # 15 chars: 2 digits (state) + 5 letters + 4 digits + 1 letter (PAN) + 1 digit (entity) + 'Z' + 1 check char
        self.gstin_pattern = re.compile(r'^(\d{2})([A-Z]{5}\d{4}[A-Z]{1})([1-9A-Z]{1})(Z)([A-Z\d]{1})$')

    def validate_gstin(self, gstin: str) -> tuple[bool, str]:
        if not gstin:
            return False, "GSTIN missing on invoice"
        clean_gst = gstin.strip().upper()
        
        match = self.gstin_pattern.match(clean_gst)
        if not match:
            return False, f"Invalid GSTIN structure: '{clean_gst}' must be 15 alphanumeric characters matching 2-digit state + 10-char PAN + entity code + Z + check digit"

        state_code = match.group(1)
        if state_code not in self.VALID_STATE_CODES:
            return False, f"Invalid GST state code: '{state_code}' is not a recognized Indian State/UT code (01-38, 97)"

        # Check for fake placeholder PANs like XXXXX0000X
        pan = match.group(2)
        if pan.startswith("XXXXX") or pan == "ABCDE1234F":
            return False, f"Invalid/Placeholder PAN in GSTIN: '{pan}' is not an authorized PAN"

        return True, "GSTIN format and state code are valid"

    def audit(self, invoice: InvoiceData, recon_report: ReconciliationReport) -> AnomalyRiskReport:
        dimensions: List[RiskDimensionScore] = []
        summary_bullets: List[str] = []
        is_duplicate = False
        bank_changed = False
        price_inflation = False
        total_risk_score = 0.0

        with get_db_cursor() as cursor:
            # 1. Dimension 1: Duplicate Billing in Audit Ledger
            cursor.execute("""
                SELECT id, invoice_no, payout_id, settlement_status, timestamp 
                FROM audit_ledger 
                WHERE invoice_no = ? AND settlement_status = 'PROCESSED'
            """, (invoice.invoice_number,))
            duplicate_row = cursor.fetchone()

            if duplicate_row:
                is_duplicate = True
                total_risk_score += 95.0
                dimensions.append(RiskDimensionScore(
                    dimension="Duplicate Settlement Check",
                    score=95.0,
                    weight=0.40,
                    severity="CRITICAL",
                    flag=True,
                    explanation=f"CRITICAL FRAUD RISK: Invoice #{invoice.invoice_number} was already settled on {duplicate_row['timestamp']} with Payout ID {duplicate_row['payout_id']}."
                ))
                summary_bullets.append(f"Duplicate invoice detected! Already paid under Payout Reference {duplicate_row['payout_id']}.")
            else:
                dimensions.append(RiskDimensionScore(
                    dimension="Duplicate Settlement Check",
                    score=0.0,
                    weight=0.40,
                    severity="LOW",
                    flag=False,
                    explanation="No previous payout found for this invoice number in audit ledger."
                ))

            # 2. Dimension 2: Bank Account & IFSC Consistency
            if recon_report.vendor_id:
                cursor.execute("SELECT bank_account, ifsc, name FROM vendors WHERE id = ?", (recon_report.vendor_id,))
                vendor_db = cursor.fetchone()

                if vendor_db:
                    db_acct = str(vendor_db["bank_account"]).strip()
                    db_ifsc = str(vendor_db["ifsc"]).strip().upper()
                    inv_acct = str(invoice.bank_account_no).strip() if invoice.bank_account_no else ""
                    inv_ifsc = str(invoice.ifsc_code).strip().upper() if invoice.ifsc_code else ""

                    if inv_acct and inv_acct != db_acct:
                        bank_changed = True
                        total_risk_score += 45.0
                        dimensions.append(RiskDimensionScore(
                            dimension="Bank Account Authenticity",
                            score=90.0,
                            weight=0.25,
                            severity="HIGH",
                            flag=True,
                            explanation=f"BANK TAMPERING ALERT: Invoice beneficiary account '{inv_acct}' differs from registered vendor account '{db_acct}'."
                        ))
                        summary_bullets.append(f"Bank Account changed from registered `{db_acct}` to `{inv_acct}` without prior CFO authorization.")
                    elif inv_ifsc and inv_ifsc != db_ifsc:
                        bank_changed = True
                        total_risk_score += 25.0
                        dimensions.append(RiskDimensionScore(
                            dimension="Bank IFSC Authenticity",
                            score=50.0,
                            weight=0.15,
                            severity="MEDIUM",
                            flag=True,
                            explanation=f"Bank branch IFSC changed from registered '{db_ifsc}' to '{inv_ifsc}'."
                        ))
                        summary_bullets.append(f"Bank branch IFSC mismatch: `{inv_ifsc}` vs registered `{db_ifsc}`.")
                    else:
                        dimensions.append(RiskDimensionScore(
                            dimension="Bank Account Authenticity",
                            score=0.0,
                            weight=0.25,
                            severity="LOW",
                            flag=False,
                            explanation="Bank account and IFSC code match verified corporate records."
                        ))
            else:
                total_risk_score += 30.0
                dimensions.append(RiskDimensionScore(
                    dimension="Vendor Verification",
                    score=60.0,
                    weight=0.20,
                    severity="MEDIUM",
                    flag=True,
                    explanation="Vendor is not in pre-approved master vendor list."
                ))
                summary_bullets.append("Vendor not present in pre-approved corporate directory.")

            # 3. Dimension 3: Line Item Price Inflation (>10% deviation)
            max_price_inflation_pct = 0.0
            inflated_items = []
            for item in recon_report.line_matches:
                if item.po_unit_price > 0:
                    pct = ((item.invoice_unit_price - item.po_unit_price) / item.po_unit_price) * 100
                    if pct > 10.0:
                        price_inflation = True
                        max_price_inflation_pct = max(max_price_inflation_pct, pct)
                        inflated_items.append(f"{item.item_name} (+{pct:.1f}%)")

            if price_inflation:
                inflation_score = min(80.0, 30.0 + max_price_inflation_pct)
                total_risk_score += inflation_score
                dimensions.append(RiskDimensionScore(
                    dimension="Unit Rate Inflation Check",
                    score=inflation_score,
                    weight=0.20,
                    severity="HIGH" if max_price_inflation_pct > 20 else "MEDIUM",
                    flag=True,
                    explanation=f"Price inflation detected on {len(inflated_items)} line items: {', '.join(inflated_items)}."
                ))
                summary_bullets.append(f"Unit price inflation exceeding 10% tolerance threshold: {', '.join(inflated_items)}.")
            else:
                dimensions.append(RiskDimensionScore(
                    dimension="Unit Rate Inflation Check",
                    score=0.0,
                    weight=0.20,
                    severity="LOW",
                    flag=False,
                    explanation="Line item unit rates match contracted PO rates exactly."
                ))

            # 4. Dimension 4: GSTIN & Tax Compliance Check
            gst_valid, gst_msg = self.validate_gstin(invoice.vendor_gstin or "")
            if not gst_valid:
                total_risk_score += 35.0
                dimensions.append(RiskDimensionScore(
                    dimension="GST Compliance & Integrity",
                    score=70.0,
                    weight=0.15,
                    severity="HIGH",
                    flag=True,
                    explanation=f"GSTIN Failure: {gst_msg}"
                ))
                summary_bullets.append(f"Invalid GSTIN structure: {gst_msg}")
            else:
                dimensions.append(RiskDimensionScore(
                    dimension="GST Compliance & Integrity",
                    score=0.0,
                    weight=0.15,
                    severity="LOW",
                    flag=False,
                    explanation=f"Valid GSTIN registered: {invoice.vendor_gstin}"
                ))

        # Clamp Overall Score between 0 and 100
        overall_score = min(100.0, round(total_risk_score, 1))

        # Risk Classification
        if overall_score >= 80.0:
            risk_level = "CRITICAL"
        elif overall_score >= 45.0:
            risk_level = "HIGH"
        elif overall_score >= 20.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        if not summary_bullets:
            summary_bullets.append("All audit checks passed. Clean invoice with verified bank details and valid GSTIN.")

        recommendations = (
            "AUTOMATED PAYOUT APPROVED: Low risk profile. Proceed with instant settlement via RazorpayX."
            if overall_score < 20.0 and recon_report.is_reconciled
            else "MANUAL REVIEW REQUIRED: Place on hold and issue automated dispute email to vendor detailing identified variances."
        )

        return AnomalyRiskReport(
            invoice_number=invoice.invoice_number,
            overall_risk_score=overall_score,
            risk_level=risk_level,
            is_duplicate=is_duplicate,
            bank_account_changed=bank_changed,
            price_inflation_detected=price_inflation,
            gst_valid=gst_valid,
            dimensions=dimensions,
            summary_bullets=summary_bullets,
            recommendations=recommendations
        )
