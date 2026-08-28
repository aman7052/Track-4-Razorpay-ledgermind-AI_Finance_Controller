from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class InvoiceLineItem(BaseModel):
    item_name: str = Field(..., description="Name or description of product/service")
    quantity: float = Field(..., description="Billed quantity")
    unit_price: float = Field(..., description="Unit price per item")
    line_total: float = Field(..., description="Total line amount before tax")
    hsn_code: Optional[str] = Field(None, description="HSN/SAC Code")

class InvoiceData(BaseModel):
    vendor_name: str = Field(..., description="Name of the billing vendor")
    vendor_gstin: Optional[str] = Field(None, description="15-character GSTIN number of vendor")
    invoice_number: str = Field(..., description="Unique invoice identification number")
    invoice_date: str = Field(..., description="Invoice issue date in YYYY-MM-DD format")
    due_date: Optional[str] = Field(None, description="Payment due date")
    po_reference: Optional[str] = Field(None, description="Purchase Order reference number if present")
    line_items: List[InvoiceLineItem] = Field(default_factory=list, description="Extracted line items")
    subtotal: float = Field(0.0, description="Sum of line totals before taxes")
    tax_amount: float = Field(0.0, description="Total GST / Tax amount")
    total_amount: float = Field(0.0, description="Grand total payable")
    bank_account_no: Optional[str] = Field(None, description="Beneficiary bank account number")
    ifsc_code: Optional[str] = Field(None, description="Bank IFSC code")
    raw_text: Optional[str] = Field(None, description="Raw extracted OCR / text")

class LineMatchResult(BaseModel):
    item_name: str
    invoice_qty: float
    po_qty: float
    grn_qty: float
    invoice_unit_price: float
    po_unit_price: float
    invoice_total: float
    po_total: float
    qty_diff: float
    price_diff: float
    total_variance: float
    match_status: str  # MATCH, PRICE_MISMATCH, QTY_MISMATCH, UNMATCHED_ITEM
    notes: str = ""

class ReconciliationReport(BaseModel):
    invoice_number: str
    matched_po_id: Optional[str] = None
    vendor_id: Optional[int] = None
    vendor_name: str
    status: str  # PERFECT_MATCH, PRICE_MISMATCH, QTY_MISMATCH, DUPLICATE_INVOICE, UNAUTHORIZED_VENDOR, LINE_ITEM_MISMATCH
    line_matches: List[LineMatchResult] = Field(default_factory=list)
    total_invoice_amount: float = 0.0
    total_po_amount: float = 0.0
    net_variance_amount: float = 0.0
    variance_percentage: float = 0.0
    is_reconciled: bool = False
    details: str = ""

class RiskDimensionScore(BaseModel):
    dimension: str
    score: float
    weight: float
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    flag: bool
    explanation: str

class AnomalyRiskReport(BaseModel):
    invoice_number: str
    overall_risk_score: float  # 0 to 100
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    is_duplicate: bool = False
    bank_account_changed: bool = False
    price_inflation_detected: bool = False
    gst_valid: bool = True
    dimensions: List[RiskDimensionScore] = Field(default_factory=list)
    summary_bullets: List[str] = Field(default_factory=list)
    recommendations: str = ""

class RazorpayPayoutResponse(BaseModel):
    payout_id: str
    fund_account_id: str
    recipient_name: str
    amount_inr: float
    amount_paise: int
    tds_deducted_inr: float
    net_paid_inr: float
    currency: str = "INR"
    status: str = "processed"  # processed, queued, rejected
    mode: str = "IMPS"  # IMPS, NEFT, RTGS
    utr: str
    purpose: str = "vendor_payment"
    created_at: str
    webhook_event: Dict[str, Any] = Field(default_factory=dict)
    receipt_id: str

class SettlementPlan(BaseModel):
    invoice_number: str
    decision: str  # AUTO_PAYOUT_TRIGGERED, HOLD_FOR_CFO_REVIEW, DISPUTE_RAISED
    gross_amount: float
    tds_section: str = "194C"  # 194C (2%), 194J (10%), or 0%
    tds_rate_pct: float = 2.0
    tds_deduction_amount: float = 0.0
    net_payable_amount: float = 0.0
    payout_response: Optional[RazorpayPayoutResponse] = None
    dispute_email_draft: Optional[str] = None
    dispute_reason: Optional[str] = None
    execution_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
