import os
import json
import re
from typing import Union, BinaryIO, Optional, Any
import pypdf
import pdfplumber
from schemas.models import InvoiceData, InvoiceLineItem
from services.llm_factory import LLMFactory

class InvoiceParserAgent:
    """
    Agent 1: Ingests raw PDF / Image Invoices and extracts structured metadata, 
    line items, GSTIN, bank details, and PO reference into a strict Pydantic model.
    """
    def __init__(self, llm_provider: str = "auto"):
        self.llm_provider = llm_provider

    def extract_text_from_pdf(self, file_source: Union[str, BinaryIO, bytes]) -> tuple[str, list]:
        """
        Extracts raw text and tabular structures using pdfplumber and pypdf.
        """
        extracted_text = []
        extracted_tables = []

        try:
            with pdfplumber.open(file_source) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        extracted_text.append(text)
                    tables = page.extract_tables()
                    if tables:
                        extracted_tables.extend(tables)
        except Exception as e:
            print(f"[InvoiceParserAgent] pdfplumber failed: {e}. Fallback to pypdf.")
            try:
                reader = pypdf.PdfReader(file_source)
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        extracted_text.append(txt)
            except Exception as e2:
                print(f"[InvoiceParserAgent] pypdf failed: {e2}")

        full_text = "\n".join(extracted_text)
        return full_text, extracted_tables

    @staticmethod
    def _clean_amount(val: Any) -> float:
        if val is None:
            return 0.0
        s = str(val).strip()
        # Remove currency words/symbols like Rs., INR, ₹, $
        s = re.sub(r'^(?:Rs|INR|₹|\$)\.?\s*', '', s, flags=re.IGNORECASE)
        # Remove commas
        s = s.replace(',', '')
        # Remove any remaining non-digit non-dot chars
        s = re.sub(r'[^\d.]', '', s)
        # Handle cases with multiple dots like ..45000.00
        parts = s.split('.')
        if len(parts) > 2:
            s = "".join(parts[:-1]) + "." + parts[-1]
        try:
            return float(s) if s else 0.0
        except ValueError:
            return 0.0

    def parse_tables_for_line_items(self, tables: list) -> list[InvoiceLineItem]:
        """
        Heuristic line item extractor from pdfplumber tables.
        """
        items = []
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Find header index
            header_idx = -1
            for idx, row in enumerate(table):
                row_str = " ".join([str(c).lower() for c in row if c])
                if any(k in row_str for k in ["item", "description", "qty", "quantity", "unit price", "rate", "price"]):
                    header_idx = idx
                    break
            
            if header_idx == -1:
                continue

            headers = [str(c).lower().strip() if c else "" for c in table[header_idx]]
            
            for row in table[header_idx + 1:]:
                if not row or len(row) < 3:
                    continue
                # Skip subtotal/total/summary rows
                row_str = " ".join([str(c).lower() for c in row if c])
                if any(k in row_str for k in ["subtotal", "tax", "cgst", "sgst", "igst", "grand total", "bank &", "beneficiary"]):
                    continue

                item_name = ""
                qty = 1.0
                unit_price = 0.0
                line_total = 0.0
                hsn = ""

                # Positional mapping if standard 6-column format: [# , Name, HSN, Qty, Price, Total]
                if len(row) >= 5 and str(row[0]).strip().isdigit():
                    item_name = str(row[1]).strip()
                    hsn = str(row[2]).strip() if len(row) >= 6 else None
                    qty_idx = 3 if len(row) >= 6 else 2
                    price_idx = 4 if len(row) >= 6 else 3
                    total_idx = 5 if len(row) >= 6 else 4

                    qty = self._clean_amount(row[qty_idx])
                    if qty <= 0:
                        qty = 1.0
                    unit_price = self._clean_amount(row[price_idx])
                    line_total = self._clean_amount(row[total_idx])
                else:
                    # Dynamic column lookup based on header names
                    for c_idx, cell in enumerate(row):
                        if not cell:
                            continue
                        cell_text = str(cell).strip()
                        h_name = headers[c_idx] if c_idx < len(headers) else ""
                        
                        if "desc" in h_name or "item" in h_name:
                            item_name = cell_text
                        elif "hsn" in h_name or "sac" in h_name:
                            hsn = cell_text
                        elif "qty" in h_name or "quantity" in h_name:
                            qty = self._clean_amount(cell_text)
                        elif "price" in h_name or "rate" in h_name or "unit" in h_name:
                            unit_price = self._clean_amount(cell_text)
                        elif "total" in h_name or "amount" in h_name:
                            line_total = self._clean_amount(cell_text)

                # Fallback calculation if one is 0.0
                if item_name:
                    if unit_price == 0.0 and line_total > 0 and qty > 0:
                        unit_price = round(line_total / qty, 2)
                    if line_total == 0.0 and unit_price > 0 and qty > 0:
                        line_total = round(unit_price * qty, 2)

                    if unit_price > 0 or line_total > 0:
                        items.append(InvoiceLineItem(
                            item_name=item_name,
                            quantity=qty if qty > 0 else 1.0,
                            unit_price=unit_price,
                            line_total=line_total,
                            hsn_code=hsn or None
                        ))

        return items

    def parse_invoice(self, file_source: Union[str, BinaryIO, bytes]) -> InvoiceData:
        """
        Main execution pipeline: PDF -> Text & Tables -> LLM / Heuristics -> Pydantic InvoiceData.
        """
        raw_text, tables = self.extract_text_from_pdf(file_source)

        # Build prompt for LLM
        prompt = f"""
        Extract the following Indian Tax Invoice fields into strict JSON:
        - vendor_name (string)
        - vendor_gstin (15-character GSTIN string)
        - invoice_number (string)
        - invoice_date (YYYY-MM-DD string)
        - due_date (YYYY-MM-DD string or null)
        - po_reference (e.g. PO-2026-001 or null)
        - line_items: list of objects with [item_name, quantity, unit_price, line_total, hsn_code]
        - subtotal (number)
        - tax_amount (number)
        - total_amount (number)
        - bank_account_no (string or null)
        - ifsc_code (string or null)

        Invoice Text Content:
        \"\"\"
        {raw_text}
        \"\"\"
        """
        system_prompt = "You are an expert AI Finance Controller. Extract accurate invoice fields into strict JSON only."
        
        llm_response = LLMFactory.call_llm(prompt, system_prompt, provider=self.llm_provider)

        # Try to parse JSON from LLM
        invoice_dict = {}
        try:
            # Clean JSON markdown if wrapped
            cleaned = re.sub(r'```(?:json)?\s*', '', llm_response)
            cleaned = re.sub(r'\s*```', '', cleaned).strip()
            # Extract JSON substring
            json_match = re.search(r'(\{[\s\S]*\})', cleaned)
            if json_match:
                invoice_dict = json.loads(json_match.group(1))
        except Exception as e:
            print(f"[InvoiceParserAgent] Failed to parse LLM JSON: {e}. Utilizing regex/heuristic extraction.")
            # Fallback to local heuristic extractor
            fallback_json = LLMFactory._heuristic_extraction(raw_text)
            invoice_dict = json.loads(fallback_json)

        # If line items are missing from LLM response, populate from table extraction
        table_line_items = self.parse_tables_for_line_items(tables)
        if (not invoice_dict.get("line_items") or len(invoice_dict["line_items"]) == 0) and table_line_items:
            invoice_dict["line_items"] = [item.model_dump() for item in table_line_items]

        # Ensure line items is a list of InvoiceLineItem
        parsed_items = []
        raw_items = invoice_dict.get("line_items", [])
        for itm in raw_items:
            if isinstance(itm, dict):
                try:
                    parsed_items.append(InvoiceLineItem(
                        item_name=str(itm.get("item_name", "Unknown Item")),
                        quantity=float(itm.get("quantity", 1.0)),
                        unit_price=float(itm.get("unit_price", 0.0)),
                        line_total=float(itm.get("line_total", 0.0)),
                        hsn_code=str(itm.get("hsn_code", "")) if itm.get("hsn_code") else None
                    ))
                except Exception:
                    pass

        # If still no items, parse from text lines heuristically
        if not parsed_items and table_line_items:
            parsed_items = table_line_items

        subtotal = float(invoice_dict.get("subtotal") or sum(itm.line_total for itm in parsed_items) or 0.0)
        total_amount = float(invoice_dict.get("total_amount") or (subtotal * 1.18 if subtotal > 0 else 0.0))
        tax_amount = float(invoice_dict.get("tax_amount") or round(total_amount - subtotal, 2))

        return InvoiceData(
            vendor_name=invoice_dict.get("vendor_name", "Unknown Vendor"),
            vendor_gstin=invoice_dict.get("vendor_gstin"),
            invoice_number=invoice_dict.get("invoice_number", "INV-UNKNOWN"),
            invoice_date=invoice_dict.get("invoice_date", "2026-08-24"),
            due_date=invoice_dict.get("due_date"),
            po_reference=invoice_dict.get("po_reference"),
            line_items=parsed_items,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            bank_account_no=invoice_dict.get("bank_account_no"),
            ifsc_code=invoice_dict.get("ifsc_code"),
            raw_text=raw_text
        )
