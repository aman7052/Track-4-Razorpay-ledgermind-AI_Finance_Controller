import streamlit as st
import pandas as pd
from typing import List, Dict, Any
from schemas.models import (
    ReconciliationReport, 
    AnomalyRiskReport, 
    SettlementPlan, 
    InvoiceData
)
from agents.workflow import AgentExecutionStep

def render_kpi_bar(total_processed: int, auto_reconciled_pct: float, leakage_prevented_inr: float, pending_reviews: int):
    """
    Renders the 4 white KPI metric cards with dark text on dark background.
    """
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-box">
            <div class="metric-title">INVOICES AUDITED</div>
            <div class="metric-number">{total_processed}</div>
            <div class="metric-hint">Total Processed by Agents</div>
        </div>
        <div class="metric-box">
            <div class="metric-title">AUTO-RECONCILED</div>
            <div class="metric-number">{auto_reconciled_pct:.1f}%</div>
            <div class="metric-hint">Instant Clean Settlements</div>
        </div>
        <div class="metric-box">
            <div class="metric-title">MONEY SAVED (LEAKAGE)</div>
            <div class="metric-number" style="color: #059669;">₹{leakage_prevented_inr:,.2f}</div>
            <div class="metric-hint">Overbilling & Duplicate Fraud Blocked</div>
        </div>
        <div class="metric-box">
            <div class="metric-title">NEEDS REVIEW</div>
            <div class="metric-number" style="color: {'#DC2626' if pending_reviews > 0 else '#059669'};">{pending_reviews}</div>
            <div class="metric-hint">Disputes & Flagged Invoices</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_review_queue_drawer(pending_invoices: List[dict]):
    """
    Renders an inspection view of flagged invoices.
    """
    if not pending_invoices:
        st.info("No flagged invoices pending review.")
        return

    for inv in pending_invoices:
        inv_no = inv.get("invoice_no", "INV-UNKNOWN")
        vendor = inv.get("vendor_name", "Unknown Vendor")
        status = inv.get("audit_status", "FLAGGED")
        variance = float(inv.get("variance_amount", 0.0))
        risk_score = float(inv.get("risk_score", 0.0))
        notes = inv.get("notes", "Discrepancy identified during 3-way match.")
        timestamp = inv.get("timestamp", "")
        
        tag_class = "tag-danger" if risk_score >= 70 or "DUPLICATE" in status else "tag-warning"

        st.markdown(f"""
        <div style="background: #1E222D; border: 1px solid #2E3440; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <span style="font-size: 14px; font-weight: 700; color: #F8FAFC;">{inv_no}</span>
                    <span style="font-size: 13px; color: #94A3B8; margin-left: 8px;">— {vendor}</span>
                    <div style="font-size: 12px; color: #64748B; margin-top: 3px;">
                        PO: {inv.get('matched_po_id') or 'Unmatched'} &nbsp;|&nbsp; Time: {timestamp}
                    </div>
                </div>
                <div style="text-align: right;">
                    <span class="{tag_class}">{status}</span>
                    <div style="font-size: 13px; font-weight: 700; color: {'#F87171' if variance > 0 else '#F8FAFC'}; margin-top: 3px;">
                        Variance: ₹{variance:+,.2f}
                    </div>
                </div>
            </div>
            <div style="background: #131722; border-radius: 4px; padding: 6px 10px; margin-top: 8px; font-size: 12px; color: #CBD5E1; border: 1px solid #2E3440;">
                <strong style="color: #F8FAFC;">Finding:</strong> {notes} &nbsp;|&nbsp; <strong>Risk Score:</strong> {risk_score:.0f}/100
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_agent_timeline(steps: List[AgentExecutionStep]):
    """
    Renders step-by-step verification trail.
    """
    st.markdown("##### Verification Trail")
    for step in steps:
        if step.status == "SUCCESS":
            css_class = "step-row-success"
            tag_class = "tag-success"
            status_text = "PASSED"
        elif step.status == "WARNING":
            css_class = "step-row-warning"
            tag_class = "tag-warning"
            status_text = "FLAGGED"
        elif step.status == "FAILED":
            css_class = "step-row-danger"
            tag_class = "tag-danger"
            status_text = "BLOCKED"
        else:
            css_class = "step-row-info"
            tag_class = "tag-info"
            status_text = "RUNNING"

        st.markdown(f"""
        <div class="step-row {css_class}">
            <div>
                <strong style="font-size: 13px; color: #F8FAFC;">{step.step_name}</strong>
                <div style="font-size: 12px; color: #94A3B8; margin-top: 2px;">{step.output_summary}</div>
            </div>
            <div style="text-align: right; min-width: 90px;">
                <span class="{tag_class}">{status_text}</span>
                <div style="font-size: 11px; color: #64748B; margin-top: 2px;">{step.duration_ms:.0f} ms</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_line_diff_table(recon_report: ReconciliationReport):
    """
    Renders 3-way match line item variance table.
    """
    st.markdown("##### 3-Way Reconciliation Comparison (Invoice vs PO vs GRN)")
    
    if not recon_report.line_matches:
        st.info("No matching Purchase Order lines found for this vendor.")
        return

    data = []
    for item in recon_report.line_matches:
        data.append({
            "Item Description": item.item_name,
            "Invoice Qty": f"{item.invoice_qty:.1f}",
            "PO Qty": f"{item.po_qty:.1f}",
            "GRN Qty": f"{item.grn_qty:.1f}",
            "Invoice Rate": f"₹{item.invoice_unit_price:,.2f}",
            "PO Rate": f"₹{item.po_unit_price:,.2f}",
            "Rate Diff": f"₹{item.price_diff:+,.2f}",
            "Variance (INR)": f"₹{item.total_variance:+,.2f}",
            "Status": item.match_status,
            "Findings": item.notes
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Billed Total", f"₹{recon_report.total_invoice_amount:,.2f}")
    c2.metric("PO Baseline Total", f"₹{recon_report.total_po_amount:,.2f}")
    delta_color = "normal" if recon_report.net_variance_amount == 0 else "inverse"
    c3.metric(
        "Net Variance", 
        f"₹{recon_report.net_variance_amount:+,.2f}", 
        delta=f"{recon_report.variance_percentage:+.1f}%", 
        delta_color=delta_color
    )

def render_risk_audit_card(risk_report: AnomalyRiskReport):
    """
    Renders fraud checks and risk score.
    """
    st.markdown("##### Risk & Forensic Analysis")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if risk_report.overall_risk_score < 20:
            tag_class = "tag-success"
            score_color = "#4ADE80"
        elif risk_report.overall_risk_score < 50:
            tag_class = "tag-warning"
            score_color = "#FACC15"
        else:
            tag_class = "tag-danger"
            score_color = "#F87171"

        st.markdown(f"""
        <div style="background: #1E222D; border: 1px solid #2E3440; border-radius: 6px; padding: 14px; text-align: center;">
            <div style="font-size: 11px; font-weight: 600; color: #94A3B8; text-transform: uppercase;">Risk Score</div>
            <div style="font-size: 28px; font-weight: 700; color: {score_color}; margin: 4px 0;">
                {risk_report.overall_risk_score:.0f}<span style="font-size: 14px; color: #64748B;">/100</span>
            </div>
            <span class="{tag_class}">
                {risk_report.risk_level} RISK
            </span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        for bullet in risk_report.summary_bullets:
            st.markdown(f"• {bullet}")
        st.caption(f"**Recommendation:** {risk_report.recommendations}")

    with st.expander("View Rule Checks", expanded=False):
        for dim in risk_report.dimensions:
            d_color = "#F87171" if dim.severity in ["HIGH", "CRITICAL"] else "#FACC15" if dim.severity == "MEDIUM" else "#4ADE80"
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #2E3440; padding: 6px 0; font-size: 12px;">
                <div>
                    <strong style="color: #F8FAFC;">{dim.dimension}</strong>
                    <div style="color: #94A3B8;">{dim.explanation}</div>
                </div>
                <div style="text-align: right; min-width: 80px;">
                    <span style="font-weight: 700; color: {d_color};">{dim.score:.0f} pts</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

def render_payout_receipt(settlement_plan: SettlementPlan):
    """
    Renders simulated RazorpayX payout receipt card.
    """
    payout = settlement_plan.payout_response
    if not payout:
        return

    st.markdown(f"""
    <div class="payout-box">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 12px;">
            <div>
                <strong style="font-size: 15px; color: #FFFFFF;">RazorpayX Instant Settlement</strong>
                <div style="font-size: 11px; color: #94A3B8;">Automated Bank Transfer</div>
            </div>
            <span class="tag-success">PROCESSED</span>
        </div>
        <div class="payout-row">
            <span>Payout Reference:</span>
            <span class="mono" style="color: #60A5FA;">{payout.payout_id}</span>
        </div>
        <div class="payout-row">
            <span>Beneficiary Vendor:</span>
            <span style="color: #FFFFFF; font-weight: 600;">{payout.recipient_name}</span>
        </div>
        <div class="payout-row">
            <span>Bank UTR:</span>
            <span class="mono" style="color: #34D399; font-weight: 600;">{payout.utr}</span>
        </div>
        <div class="payout-row">
            <span>Transfer Mode:</span>
            <span>{payout.mode} (IMPS Instant Clearing)</span>
        </div>
        <div class="payout-row">
            <span>TDS Deduction ({settlement_plan.tds_section} @ {settlement_plan.tds_rate_pct}%):</span>
            <span style="color: #F87171;">- ₹{settlement_plan.tds_deduction_amount:,.2f}</span>
        </div>
        <div class="payout-row-total">
            <span>Net Transferred to Vendor:</span>
            <span style="color: #34D399; font-size: 16px;">₹{settlement_plan.net_payable_amount:,.2f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
