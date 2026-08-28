import os
import json
import re
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class LLMFactory:
    """
    Unified LLM Invocation Factory supporting OpenAI, Gemini, Groq, Ollama, 
    and a local deterministic regex-heuristic fallback engine.
    """
    @staticmethod
    def is_provider_available(provider: str) -> bool:
        provider = provider.lower()
        if provider == "openai":
            return bool(os.getenv("OPENAI_API_KEY"))
        elif provider == "gemini":
            return bool(os.getenv("GEMINI_API_KEY"))
        elif provider == "groq":
            return bool(os.getenv("GROQ_API_KEY"))
        elif provider == "ollama":
            return True
        return True  # heuristic fallback always available

    @staticmethod
    def call_llm(prompt: str, system_prompt: str = "", provider: str = "auto", temperature: float = 0.1) -> str:
        """
        Routes the prompt to the selected LLM provider or fallback.
        """
        # Determine actual provider
        if provider == "auto":
            if os.getenv("OPENAI_API_KEY"):
                provider = "openai"
            elif os.getenv("GEMINI_API_KEY"):
                provider = "gemini"
            elif os.getenv("GROQ_API_KEY"):
                provider = "groq"
            else:
                provider = "heuristic"

        try:
            if provider == "openai" and os.getenv("OPENAI_API_KEY"):
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt or "You are a precise corporate finance extraction AI."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"} if "json" in prompt.lower() else None,
                    temperature=temperature
                )
                return response.choices[0].message.content or ""

            elif provider == "gemini" and os.getenv("GEMINI_API_KEY"):
                import google.generativeai as genai
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                model = genai.GenerativeModel("gemini-1.5-flash")
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                response = model.generate_content(full_prompt)
                return response.text

            elif provider == "groq" and os.getenv("GROQ_API_KEY"):
                from groq import Groq
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"} if "json" in prompt.lower() else None,
                    temperature=temperature
                )
                return response.choices[0].message.content or ""

        except Exception as e:
            print(f"[LLMFactory] Provider {provider} failed with error: {e}. Switching to deterministic heuristic fallback.")

        # Fallback to local heuristic extractor
        return LLMFactory._heuristic_extraction(prompt)

    @staticmethod
    def _heuristic_extraction(raw_text: str) -> str:
        """
        High precision local regex & structure parser for Indian Tax Invoices.
        """
        data: Dict[str, Any] = {
            "vendor_name": "Unknown Vendor",
            "vendor_gstin": None,
            "invoice_number": "INV-UNKNOWN",
            "invoice_date": "2026-08-24",
            "due_date": None,
            "po_reference": None,
            "line_items": [],
            "subtotal": 0.0,
            "tax_amount": 0.0,
            "total_amount": 0.0,
            "bank_account_no": None,
            "ifsc_code": None
        }

        # 1. Extract Vendor GSTIN (Look before BILL TO / BUYER block first)
        buyer_split = re.split(r'BILL\s*TO|BUYER', raw_text, flags=re.IGNORECASE)
        header_text = buyer_split[0] if len(buyer_split) > 1 else raw_text
        
        gstin_match = re.search(r'GSTIN[\s:]*([A-Z0-9]{10,18})', header_text, re.IGNORECASE)
        if gstin_match:
            data["vendor_gstin"] = gstin_match.group(1).strip()
        else:
            gstin_gen = re.search(r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})\b', raw_text)
            if gstin_gen:
                data["vendor_gstin"] = gstin_gen.group(1).strip()

        # 2. Extract Invoice Number
        inv_match = re.search(r'(?:Invoice\s*(?:No|Number|#)[\s:]*)\s*([A-Z0-9_-]+)', raw_text, re.IGNORECASE)
        if inv_match:
            data["invoice_number"] = inv_match.group(1).strip()
        else:
            inv_alt = re.search(r'\b(INV-[\w-]+)\b', raw_text, re.IGNORECASE)
            if inv_alt:
                data["invoice_number"] = inv_alt.group(1).strip()

        # 3. Extract PO Reference
        po_match = re.search(r'(?:PO\s*(?:Reference|Ref|No|Number)?[\s:]*)\s*(PO-[\w-]+)', raw_text, re.IGNORECASE)
        if po_match:
            data["po_reference"] = po_match.group(1).strip()
        else:
            po_alt = re.search(r'\b(PO-\d{4}-\d{3,4})\b', raw_text)
            if po_alt:
                data["po_reference"] = po_alt.group(1).strip()

        # 4. Extract Dates
        date_match = re.search(r'(?:Invoice\s*Date[\s:]*)\s*(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})', raw_text, re.IGNORECASE)
        if date_match:
            data["invoice_date"] = date_match.group(1).strip()

        due_match = re.search(r'(?:Due\s*Date[\s:]*)\s*(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})', raw_text, re.IGNORECASE)
        if due_match:
            data["due_date"] = due_match.group(1).strip()

        # 5. Extract Bank Details
        ben_match = re.search(r'(?:Beneficiary\s*Name[\s:]*)\s*([A-Za-z0-9\s&.,\'-]+?)(?:\s*(?:Bank|Account|IFSC|Branch|Subtotal|CGST|SGST|Grand|\n|\r|$))', raw_text, re.IGNORECASE)
        if ben_match:
            clean_ben = ben_match.group(1).strip()
            if len(clean_ben) > 3:
                data["vendor_name"] = clean_ben

        acct_match = re.search(r'(?:Account\s*(?:Number|No)?[\s:]*)\s*(\d{9,18})', raw_text, re.IGNORECASE)
        if acct_match:
            data["bank_account_no"] = acct_match.group(1).strip()

        ifsc_match = re.search(r'(?:IFSC[\s:]*)\s*([A-Z]{4}0[A-Z0-9]{6})', raw_text, re.IGNORECASE)
        if ifsc_match:
            data["ifsc_code"] = ifsc_match.group(1).strip()

        # 6. Extract Vendor Name from Header if not from Beneficiary
        if data["vendor_name"] == "Unknown Vendor":
            lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
            for line in lines[:8]:
                # Ignore Razorpay line, buyer line, or title words
                if "razorpay" in line.lower() or "bill to" in line.lower():
                    continue
                clean = re.sub(r'\s*TAX INVOICE.*', '', line, flags=re.IGNORECASE).strip()
                clean = re.sub(r'^(Vendor|From|Name)[\s:]*', '', clean, flags=re.IGNORECASE).strip()
                if any(term in clean.lower() for term in ["pvt", "ltd", "enterprises", "solutions", "hub", "logistics", "systems", "corp", "tech", "stationery", "hardware"]):
                    data["vendor_name"] = clean
                    break
                elif len(clean) > 4 and not any(k in clean.lower() for k in ["gstin", "invoice", "date", "original"]):
                    data["vendor_name"] = clean
                    break

        # 7. Extract Grand Total / Subtotal
        grand_total_match = re.search(r'(?:Grand\s*Total|Total\s*Amount|Net\s*Payable)[\s:]*[₹Rs\.\s]*([\d,]+\.?\d*)', raw_text, re.IGNORECASE)
        if grand_total_match:
            try:
                data["total_amount"] = float(grand_total_match.group(1).replace(',', ''))
            except ValueError:
                pass

        subtotal_match = re.search(r'(?:Subtotal|Taxable\s*Amount)[\s:]*[₹Rs\.\s]*([\d,]+\.?\d*)', raw_text, re.IGNORECASE)
        if subtotal_match:
            try:
                data["subtotal"] = float(subtotal_match.group(1).replace(',', ''))
            except ValueError:
                pass

        tax_match = re.search(r'(?:CGST|SGST|IGST|GST|Tax\s*Amount)[\s:]*[₹Rs\.\s]*([\d,]+\.?\d*)', raw_text, re.IGNORECASE)
        if tax_match and data["total_amount"] > 0 and data["subtotal"] > 0:
            data["tax_amount"] = round(data["total_amount"] - data["subtotal"], 2)

        return json.dumps(data)
