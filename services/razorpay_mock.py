import os
import time
import random
import string
import json
from datetime import datetime
from typing import Dict, Any, Optional
from schemas.models import RazorpayPayoutResponse
from database.db import get_db_cursor

class RazorpayMockService:
    """
    Enterprise Mock Service simulating RazorpayX Payouts API
    Docs reference: https://razorpay.com/docs/api/x/payouts/
    """
    def __init__(self, key_id: str = "rzp_test_ledgermind_mock", key_secret: str = "rzp_secret_ledgermind_mock"):
        self.key_id = key_id
        self.key_secret = key_secret
        self.account_number = os.getenv("RAZORPAY_ACCOUNT_NUMBER", "7878780080316316")

    def _generate_id(self, prefix: str, length: int = 14) -> str:
        random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        return f"{prefix}_{random_chars}"

    def _generate_utr(self) -> str:
        # Standard 12-digit Indian Bank UTR format: RZP + 9 digits
        return f"RZP{random.randint(100000000, 999999999)}"

    def calculate_tds(self, gross_amount: float, vendor_category: str = "IT_SERVICES") -> tuple[str, float, float]:
        """
        Calculate Indian TDS according to Income Tax Act:
        - Section 194C (Logistics, Hardware supply, Contractors): 2%
        - Section 194J (IT Services, Software, Technical Consultation): 10% or 2% for tech call center
        - Office Supplies: 0%
        """
        if vendor_category in ["IT_SERVICES", "SECURITY_SERVICES", "CLOUD_INFRA"]:
            section = "194J (Technical Services)"
            rate = 2.0  # Common discounted TDS for software services or 10%
        elif vendor_category in ["LOGISTICS", "IT_HARDWARE"]:
            section = "194C (Work Contracts)"
            rate = 2.0
        else:
            section = "194C"
            rate = 1.0

        tds_amount = round((gross_amount * rate) / 100.0, 2)
        net_payable = round(gross_amount - tds_amount, 2)
        return section, rate, tds_amount, net_payable

    def create_payout(
        self,
        invoice_no: str,
        vendor_id: int,
        vendor_name: str,
        bank_account: str,
        ifsc: str,
        gross_amount: float,
        vendor_category: str = "IT_SERVICES",
        mode: str = "IMPS"
    ) -> RazorpayPayoutResponse:
        """
        Simulates RazorpayX Payout creation with instant settlement and webhook dispatch.
        """
        section, rate, tds_amount, net_payable = self.calculate_tds(gross_amount, vendor_category)
        
        payout_id = self._generate_id("pout")
        contact_id = self._generate_id("cont")
        fund_account_id = self._generate_id("fa")
        utr = self._generate_utr()
        receipt_id = f"REC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        created_timestamp = datetime.now().isoformat()
        
        amount_paise = int(round(net_payable * 100))

        # Simulated Webhook Payload for finance systems integration
        webhook_payload = {
            "entity": "event",
            "account_id": "acc_ledgermind_hq",
            "event": "payout.processed",
            "contains": ["payout"],
            "payload": {
                "payout": {
                    "entity": {
                        "id": payout_id,
                        "fund_account_id": fund_account_id,
                        "amount": amount_paise,
                        "currency": "INR",
                        "notes": {
                            "invoice_number": invoice_no,
                            "vendor_name": vendor_name,
                            "tds_section": section,
                            "tds_deducted": tds_amount,
                            "gross_amount": gross_amount
                        },
                        "fees": 10.0,
                        "tax": 1.8,
                        "status": "processed",
                        "utr": utr,
                        "mode": mode,
                        "purpose": "vendor_bill",
                        "reference_id": f"REF_{invoice_no.replace('-', '_')}",
                        "narration": f"LedgerMind AutoPay {invoice_no}",
                        "created_at": int(time.time())
                    }
                }
            },
            "created_at": int(time.time())
        }

        # Persist to database
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO payout_logs (
                    payout_id, invoice_no, vendor_id, gross_amount, tds_amount, net_amount, utr, mode, status, webhook_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payout_id, invoice_no, vendor_id, gross_amount, tds_amount, net_payable, utr, mode, "PROCESSED", json.dumps(webhook_payload)
            ))

            cursor.execute("""
                UPDATE audit_ledger
                SET settlement_status = 'PROCESSED',
                    payout_id = ?,
                    action_taken = 'AUTO_PAYOUT_TRIGGERED',
                    notes = ?
                WHERE invoice_no = ?
            """, (
                payout_id, f"Auto-settled via RazorpayX (UTR: {utr}, TDS: ₹{tds_amount:,.2f})", invoice_no
            ))

        return RazorpayPayoutResponse(
            payout_id=payout_id,
            fund_account_id=fund_account_id,
            recipient_name=vendor_name,
            amount_inr=gross_amount,
            amount_paise=amount_paise,
            tds_deducted_inr=tds_amount,
            net_paid_inr=net_payable,
            currency="INR",
            status="processed",
            mode=mode,
            utr=utr,
            purpose="vendor_payment",
            created_at=created_timestamp,
            webhook_event=webhook_payload,
            receipt_id=receipt_id
        )

    def get_all_payouts(self):
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT p.*, v.name as vendor_name, v.bank_account, v.ifsc
                FROM payout_logs p
                LEFT JOIN vendors v ON p.vendor_id = v.id
                ORDER BY p.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
