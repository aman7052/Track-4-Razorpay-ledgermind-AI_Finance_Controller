import os
import sys

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from seed_db import seed_database
from agents.workflow import MultiAgentController

def run_all_tests():
    print("=== Re-seeding database for deterministic test run ===")
    seed_database()
    
    controller = MultiAgentController(llm_provider="heuristic", auto_payout_threshold=20.0)
    samples_dir = os.path.join(PROJECT_ROOT, "samples")

    # -------------------------------------------------------------
    # Test 1: Perfect Match Invoice
    # -------------------------------------------------------------
    print("\n--- Test 1: Testing Perfect Match Invoice (PO-2026-001) ---")
    p1 = os.path.join(samples_dir, "invoice_perfect_match.pdf")
    res1 = controller.process_invoice(p1)
    
    print(f"Vendor: {res1.invoice.vendor_name}, Inv No: {res1.invoice.invoice_number}")
    print(f"Reconciliation Status: {res1.reconciliation.status}, Net Variance: INR {res1.reconciliation.net_variance_amount:+,.2f}")
    print(f"Risk Score: {res1.risk_report.overall_risk_score}/100 ({res1.risk_report.risk_level})")
    print(f"Settlement Decision: {res1.settlement.decision}")
    
    assert res1.reconciliation.status == "PERFECT_MATCH", f"Expected PERFECT_MATCH, got {res1.reconciliation.status}"
    assert res1.risk_report.overall_risk_score < 20.0, f"Expected risk < 20, got {res1.risk_report.overall_risk_score}"
    assert res1.settlement.decision == "AUTO_PAYOUT_TRIGGERED", f"Expected AUTO_PAYOUT_TRIGGERED, got {res1.settlement.decision}"
    assert res1.settlement.payout_response is not None, "Payout response should not be None"
    assert res1.settlement.payout_response.utr.startswith("RZP"), "UTR should start with RZP"
    print(">>> Test 1 PASSED! <<<")

    # -------------------------------------------------------------
    # Test 2: Unit Rate Inflation (+25%)
    # -------------------------------------------------------------
    print("\n--- Test 2: Testing Rate Mismatch Invoice (PO-2026-002) ---")
    p2 = os.path.join(samples_dir, "invoice_rate_mismatch.pdf")
    res2 = controller.process_invoice(p2)
    
    print(f"Vendor: {res2.invoice.vendor_name}, Inv No: {res2.invoice.invoice_number}")
    print(f"Reconciliation Status: {res2.reconciliation.status}, Net Variance: INR {res2.reconciliation.net_variance_amount:+,.2f}")
    print(f"Risk Score: {res2.risk_report.overall_risk_score}/100, Inflation Flag: {res2.risk_report.price_inflation_detected}")
    print(f"Settlement Decision: {res2.settlement.decision}")

    assert res2.reconciliation.status == "PRICE_MISMATCH", f"Expected PRICE_MISMATCH, got {res2.reconciliation.status}"
    assert res2.risk_report.price_inflation_detected is True, "Expected price inflation flag to be True"
    assert res2.settlement.decision == "DISPUTE_RAISED", f"Expected DISPUTE_RAISED, got {res2.settlement.decision}"
    assert res2.settlement.dispute_email_draft is not None, "Expected dispute email draft to be present"
    print(">>> Test 2 PASSED! <<<")

    # -------------------------------------------------------------
    # Test 3: Duplicate Fraud Invoice
    # -------------------------------------------------------------
    print("\n--- Test 3: Testing Duplicate Fraud Invoice (INV-2026-8801) ---")
    p3 = os.path.join(samples_dir, "invoice_duplicate_fraud.pdf")
    res3 = controller.process_invoice(p3)
    
    print(f"Vendor: {res3.invoice.vendor_name}, Inv No: {res3.invoice.invoice_number}")
    print(f"Duplicate Flag: {res3.risk_report.is_duplicate}, Risk Score: {res3.risk_report.overall_risk_score}/100")
    print(f"Settlement Decision: {res3.settlement.decision}")

    assert res3.risk_report.is_duplicate is True, "Expected is_duplicate to be True"
    assert res3.risk_report.overall_risk_score >= 90.0, f"Expected risk >= 90, got {res3.risk_report.overall_risk_score}"
    assert res3.settlement.payout_response is None, "Payout should NOT be created for duplicate invoice"
    print(">>> Test 3 PASSED! <<<")

    # -------------------------------------------------------------
    # Test 4: Quantity Mismatch & Bank Account Tampering
    # -------------------------------------------------------------
    print("\n--- Test 4: Testing Quantity Mismatch & Bank Tampering (PO-2026-004) ---")
    p4 = os.path.join(samples_dir, "invoice_qty_and_bank_tamper.pdf")
    res4 = controller.process_invoice(p4)
    
    print(f"Vendor: {res4.invoice.vendor_name}, Inv No: {res4.invoice.invoice_number}")
    print(f"Reconciliation Status: {res4.reconciliation.status}, Bank Changed: {res4.risk_report.bank_account_changed}")
    print(f"Risk Score: {res4.risk_report.overall_risk_score}/100")
    print(f"Settlement Decision: {res4.settlement.decision}")

    assert res4.reconciliation.status == "QTY_MISMATCH", f"Expected QTY_MISMATCH, got {res4.reconciliation.status}"
    assert res4.risk_report.bank_account_changed is True, "Expected bank_account_changed to be True"
    assert res4.settlement.decision == "DISPUTE_RAISED", f"Expected DISPUTE_RAISED, got {res4.settlement.decision}"
    print(">>> Test 4 PASSED! <<<")

    # -------------------------------------------------------------
    # Test 5: Unauthorized Vendor & Invalid GST
    # -------------------------------------------------------------
    print("\n--- Test 5: Testing Unauthorized Vendor (PO-2026-999) ---")
    p5 = os.path.join(samples_dir, "invoice_unauthorized_vendor.pdf")
    res5 = controller.process_invoice(p5)
    
    print(f"Vendor: {res5.invoice.vendor_name}, Inv No: {res5.invoice.invoice_number}")
    print(f"Reconciliation Status: {res5.reconciliation.status}, GST Valid: {res5.risk_report.gst_valid}")
    print(f"Risk Score: {res5.risk_report.overall_risk_score}/100")
    print(f"Settlement Decision: {res5.settlement.decision}")

    assert res5.reconciliation.status in ["UNAUTHORIZED_VENDOR", "UNMATCHED_PO"], f"Expected unauthorized/unmatched, got {res5.reconciliation.status}"
    assert res5.risk_report.gst_valid is False, "Expected GST to be invalid"
    assert res5.settlement.decision == "DISPUTE_RAISED", f"Expected DISPUTE_RAISED, got {res5.settlement.decision}"
    print(">>> Test 5 PASSED! <<<")

    print("\n=======================================================")
    print("*** ALL 5 MULTI-AGENT PIPELINE INTEGRATION TESTS PASSED! ***")
    print("=======================================================")

if __name__ == "__main__":
    run_all_tests()
