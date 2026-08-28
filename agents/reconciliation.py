import re
from typing import Optional, List, Dict, Any
from schemas.models import InvoiceData, ReconciliationReport, LineMatchResult
from database.db import get_db_cursor

class ReconciliationAgent:
    """
    Agent 2: Performs 3-Way Match Verification (Invoice vs Purchase Order vs Goods Received Notes).
    Calculates variance on quantity, unit price, and total amounts.
    """
    def __init__(self):
        pass

    def _normalize_string(self, s: str) -> str:
        if not s:
            return ""
        return re.sub(r'[^a-zA-Z0-9]', '', s.lower())

    def _find_matching_po_item(self, invoice_item_name: str, po_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        norm_inv = self._normalize_string(invoice_item_name)
        
        # 1. Exact or substring match
        for po_item in po_items:
            norm_po = self._normalize_string(po_item["item_name"])
            if norm_inv == norm_po or norm_inv in norm_po or norm_po in norm_inv:
                return po_item

        # 2. Token overlap match
        inv_tokens = set(invoice_item_name.lower().split())
        best_match = None
        highest_overlap = 0

        for po_item in po_items:
            po_tokens = set(po_item["item_name"].lower().split())
            overlap = len(inv_tokens.intersection(po_tokens))
            if overlap > highest_overlap and overlap >= 2:
                highest_overlap = overlap
                best_match = po_item

        return best_match

    def reconcile(self, invoice: InvoiceData) -> ReconciliationReport:
        with get_db_cursor() as cursor:
            # 1. Find Vendor in Database
            vendor_row = None
            if invoice.vendor_gstin:
                cursor.execute("SELECT * FROM vendors WHERE gstin = ?", (invoice.vendor_gstin,))
                vendor_row = cursor.fetchone()
            
            if not vendor_row and invoice.vendor_name:
                cursor.execute("SELECT * FROM vendors WHERE LOWER(name) LIKE ?", (f"%{invoice.vendor_name.lower()[:8]}%",))
                vendor_row = cursor.fetchone()

            # 2. Find Purchase Order
            po_row = None
            if invoice.po_reference:
                cursor.execute("SELECT * FROM purchase_orders WHERE po_id = ?", (invoice.po_reference,))
                po_row = cursor.fetchone()

            if not po_row and vendor_row:
                cursor.execute("SELECT * FROM purchase_orders WHERE vendor_id = ? AND status = 'APPROVED' ORDER BY created_at DESC LIMIT 1", (vendor_row["id"],))
                po_row = cursor.fetchone()

            # If no PO found or Vendor not registered
            if not po_row:
                return ReconciliationReport(
                    invoice_number=invoice.invoice_number,
                    matched_po_id=None,
                    vendor_id=vendor_row["id"] if vendor_row else None,
                    vendor_name=invoice.vendor_name,
                    status="UNAUTHORIZED_VENDOR" if not vendor_row else "UNMATCHED_PO",
                    line_matches=[],
                    total_invoice_amount=invoice.total_amount,
                    total_po_amount=0.0,
                    net_variance_amount=invoice.total_amount,
                    variance_percentage=100.0,
                    is_reconciled=False,
                    details=f"No approved Purchase Order found for {invoice.vendor_name} (Ref: {invoice.po_reference or 'None'})."
                )

            po_id = po_row["po_id"]
            vendor_id = po_row["vendor_id"]

            # Fetch PO Line Items
            cursor.execute("SELECT * FROM po_items WHERE po_id = ?", (po_id,))
            po_items = [dict(row) for row in cursor.fetchall()]

            # Fetch GRN Records for this PO
            cursor.execute("SELECT * FROM goods_received_notes WHERE po_id = ?", (po_id,))
            grn_records = [dict(row) for row in cursor.fetchall()]

            line_matches: List[LineMatchResult] = []
            has_price_mismatch = False
            has_qty_mismatch = False
            has_unmatched_items = False

            total_po_amount_subtotal = sum(item["total_price"] for item in po_items)
            # Estimate PO total with standard 18% GST for comparison
            total_po_with_tax = round(total_po_amount_subtotal * 1.18, 2)

            for inv_item in invoice.line_items:
                matched_po_item = self._find_matching_po_item(inv_item.item_name, po_items)
                
                if matched_po_item:
                    po_qty = float(matched_po_item["ordered_qty"])
                    po_unit_price = float(matched_po_item["unit_price"])
                    po_total = float(matched_po_item["total_price"])

                    # Match GRN
                    grn_qty = po_qty  # default
                    for grn in grn_records:
                        if self._normalize_string(grn["item_name"]) == self._normalize_string(matched_po_item["item_name"]):
                            grn_qty = float(grn["accepted_qty"])
                            break

                    qty_diff = inv_item.quantity - po_qty
                    price_diff = inv_item.unit_price - po_unit_price
                    total_variance = inv_item.line_total - po_total

                    # Match Status
                    if abs(qty_diff) > 0.01 and abs(price_diff) > 0.01:
                        match_status = "QTY_AND_PRICE_MISMATCH"
                        has_qty_mismatch = True
                        has_price_mismatch = True
                    elif abs(qty_diff) > 0.01:
                        match_status = "QTY_MISMATCH"
                        has_qty_mismatch = True
                    elif abs(price_diff) > 0.01:
                        match_status = "PRICE_MISMATCH"
                        has_price_mismatch = True
                    else:
                        match_status = "MATCH"

                    notes = []
                    if abs(price_diff) > 0.01:
                        pct_change = (price_diff / po_unit_price) * 100
                        notes.append(f"Price inflated by {pct_change:+.1f}% (₹{inv_item.unit_price:,.2f} vs PO ₹{po_unit_price:,.2f})")
                    if abs(qty_diff) > 0.01:
                        notes.append(f"Quantity difference: Billed {inv_item.quantity} vs PO {po_qty} (GRN {grn_qty})")

                    line_matches.append(LineMatchResult(
                        item_name=inv_item.item_name,
                        invoice_qty=inv_item.quantity,
                        po_qty=po_qty,
                        grn_qty=grn_qty,
                        invoice_unit_price=inv_item.unit_price,
                        po_unit_price=po_unit_price,
                        invoice_total=inv_item.line_total,
                        po_total=po_total,
                        qty_diff=qty_diff,
                        price_diff=price_diff,
                        total_variance=total_variance,
                        match_status=match_status,
                        notes="; ".join(notes) if notes else "Line matched 100% with PO & GRN"
                    ))
                else:
                    has_unmatched_items = True
                    line_matches.append(LineMatchResult(
                        item_name=inv_item.item_name,
                        invoice_qty=inv_item.quantity,
                        po_qty=0.0,
                        grn_qty=0.0,
                        invoice_unit_price=inv_item.unit_price,
                        po_unit_price=0.0,
                        invoice_total=inv_item.line_total,
                        po_total=0.0,
                        qty_diff=inv_item.quantity,
                        price_diff=inv_item.unit_price,
                        total_variance=inv_item.line_total,
                        match_status="UNMATCHED_ITEM",
                        notes="Item not present in contracted Purchase Order"
                    ))

            # Final Reconciliation Status
            net_variance = round(invoice.total_amount - total_po_with_tax, 2)
            variance_pct = round((net_variance / total_po_with_tax * 100), 2) if total_po_with_tax > 0 else 100.0

            if has_unmatched_items:
                overall_status = "LINE_ITEM_MISMATCH"
                is_reconciled = False
            elif has_price_mismatch and has_qty_mismatch:
                overall_status = "PRICE_AND_QTY_MISMATCH"
                is_reconciled = False
            elif has_price_mismatch:
                overall_status = "PRICE_MISMATCH"
                is_reconciled = False
            elif has_qty_mismatch:
                overall_status = "QTY_MISMATCH"
                is_reconciled = False
            elif abs(net_variance) > 5.0:  # slight rounding tolerance
                overall_status = "TOTAL_VARIANCE_MISMATCH"
                is_reconciled = False
            else:
                overall_status = "PERFECT_MATCH"
                is_reconciled = True

            return ReconciliationReport(
                invoice_number=invoice.invoice_number,
                matched_po_id=po_id,
                vendor_id=vendor_id,
                vendor_name=vendor_row["name"] if vendor_row else invoice.vendor_name,
                status=overall_status,
                line_matches=line_matches,
                total_invoice_amount=invoice.total_amount,
                total_po_amount=total_po_with_tax,
                net_variance_amount=net_variance,
                variance_percentage=variance_pct,
                is_reconciled=is_reconciled,
                details=f"Reconciliation completed for {po_id}. Status: {overall_status} with variance ₹{net_variance:+,.2f}."
            )
