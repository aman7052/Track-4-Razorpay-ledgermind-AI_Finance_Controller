from datetime import datetime
from schemas.models import ReconciliationReport, AnomalyRiskReport

class DisputeEmailService:
    @staticmethod
    def generate_dispute_email(
        recon_report: ReconciliationReport,
        risk_report: AnomalyRiskReport,
        vendor_email: str = "accounts@vendor.com",
        cfo_name: str = "Finance Operations & Controller Team",
        company_name: str = "Razorpay Technologies Pvt Ltd"
    ) -> str:
        """
        Drafts a clear, polite, and legally sound dispute resolution email to the billing vendor.
        """
        dispute_id = f"DSP-{recon_report.invoice_number.replace('INV-', '')}-{datetime.now().strftime('%Y%m%d')}"
        
        # Build Itemized Discrepancy Breakdown
        items_table_lines = []
        items_table_lines.append("| Item Description | Invoiced Qty | PO / GRN Qty | Invoiced Rate (₹) | Approved PO Rate (₹) | Variance (₹) | Discrepancy Flag |")
        items_table_lines.append("|:---|:---:|:---:|:---:|:---:|:---:|:---|")

        for item in recon_report.line_matches:
            qty_flag = f"Δ {item.qty_diff:+.1f}" if item.qty_diff != 0 else "✓ Exact"
            rate_flag = f"Δ ₹{item.price_diff:+,.2f}" if item.price_diff != 0 else "✓ Contracted"
            var_flag = f"₹{item.total_variance:+,.2f}"
            status_badge = f"⚠️ {item.match_status}" if item.match_status != "MATCH" else "✅ Match"
            
            items_table_lines.append(
                f"| **{item.item_name}** | {item.invoice_qty} | {item.po_qty} | ₹{item.invoice_unit_price:,.2f} | ₹{item.po_unit_price:,.2f} | {var_flag} | {status_badge} |"
            )

        items_table_md = "\n".join(items_table_lines)

        # Build Risk & Compliance Notes
        audit_bullets = "\n".join([f"- ❗ {bullet}" for bullet in risk_report.summary_bullets])

        email_content = f"""**Subject:** [DISPUTE NOTICE - {dispute_id}] Discrepancy Identified on Invoice {recon_report.invoice_number} (PO: {recon_report.matched_po_id or 'UNMATCHED'})

**To:** {vendor_email}  
**From:** {cfo_name} <finance-controller@razorpay.corp>  
**Date:** {datetime.now().strftime('%d %B %Y')}  
**Dispute Reference:** `{dispute_id}`  

---

Dear Accounts Team at **{recon_report.vendor_name}**,

We are writing regarding **Invoice #{recon_report.invoice_number}** submitted against Purchase Order **{recon_report.matched_po_id or 'N/A'}** for a total billed amount of **₹{recon_report.total_invoice_amount:,.2f}**.

Our automated Finance Audit & 3-Way Reconciliation Controller has identified discrepancies during line-item matching against our contracted Purchase Order terms and Goods Received Notes (GRN). Consequently, the invoice has been placed on temporary hold.

### 📋 Line-Item Variance Summary:
{items_table_md}

### 🚨 Audit & Risk Flags Identified:
{audit_bullets}

- **Total Invoiced Amount:** ₹{recon_report.total_invoice_amount:,.2f}
- **Approved PO Baseline:** ₹{recon_report.total_po_amount:,.2f}
- **Net Identified Discrepancy / Variance:** **₹{recon_report.net_variance_amount:+,.2f}** ({recon_report.variance_percentage:.1f}%)

---

### 🛠️ Required Action Steps:
1. **Option A (Revised Tax Invoice):** Issue a corrected tax invoice adjusting the quantities/rates to match Purchase Order **{recon_report.matched_po_id}**.
2. **Option B (Credit Note):** If invoice has already been registered in your GSTR-1, issue a formal Credit Note of **₹{abs(recon_report.net_variance_amount):,.2f}** citing reference `{dispute_id}`.
3. If bank account information was updated, provide a signed bank confirmation letter on official company letterhead for validation.

Please reply to this email or re-upload the revised document within **5 business days** so our settlement engine can release instant payout via RazorpayX.

Warm regards,  
**{cfo_name}**  
{company_name}  
*Autonomous AI Finance Controller & Reconciliation Engine*
"""
        return email_content
