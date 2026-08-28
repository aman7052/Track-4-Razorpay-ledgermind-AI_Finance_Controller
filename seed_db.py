import os
import sqlite3
from database.db import get_db_cursor, init_db
from generate_sample_pdfs import generate_all_samples

def seed_database():
    print("Initializing SQLite Database Schema...")
    init_db()

    with get_db_cursor() as cursor:
        # Clear existing data to ensure clean state
        cursor.execute("DELETE FROM payout_logs;")
        cursor.execute("DELETE FROM audit_ledger;")
        cursor.execute("DELETE FROM goods_received_notes;")
        cursor.execute("DELETE FROM po_items;")
        cursor.execute("DELETE FROM purchase_orders;")
        cursor.execute("DELETE FROM vendors;")

        print("Seeding Vendors...")
        vendors = [
            (1, "CloudInfra Solutions Pvt Ltd", "29AABCC1122D1Z4", "918273645012", "HDFC0001234", "billing@cloudinfra.io", "CLOUD_INFRA", "VERIFIED"),
            (2, "Apex Hardware & Networking Hub", "29AABBA5566G1Z2", "001122334455", "ICIC0000011", "accounts@apexhardware.in", "IT_HARDWARE", "VERIFIED"),
            (3, "Nexus Cybertech Systems", "29AAACN9988H1Z5", "987654321098", "UTIB0000888", "finance@nexuscyber.com", "SECURITY_SERVICES", "VERIFIED"),
            (4, "SwiftLogistics & Freight Express", "29AABCS7744K1Z9", "112233445566", "SBIN0004567", "dispatch@swiftlogistics.co", "LOGISTICS", "VERIFIED"),
            (5, "PrintCraft Corporate Stationery", "29AACCP3322M1Z1", "778899001122", "KKBK0000444", "orders@printcraft.in", "OFFICE_SUPPLIES", "VERIFIED")
        ]
        cursor.executemany("""
            INSERT INTO vendors (id, name, gstin, bank_account, ifsc, email, category, verified_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, vendors)

        print("Seeding Purchase Orders...")
        pos = [
            ("PO-2026-001", 1, "APPROVED", 150000.0, "2026-08-01"),
            ("PO-2026-002", 2, "APPROVED", 84000.0, "2026-08-05"),
            ("PO-2026-003", 3, "APPROVED", 200000.0, "2026-08-08"),
            ("PO-2026-004", 4, "APPROVED", 45000.0, "2026-08-10"),
            ("PO-2026-005", 5, "APPROVED", 30000.0, "2026-08-12"),
        ]
        cursor.executemany("""
            INSERT INTO purchase_orders (po_id, vendor_id, status, total_budget, issued_date)
            VALUES (?, ?, ?, ?, ?)
        """, pos)

        print("Seeding PO Line Items...")
        po_items = [
            # PO-2026-001
            (1, "PO-2026-001", "AWS Dedicated Cloud Instances (c6g.4xlarge)", 4.0, 25000.0, 100000.0, "998315"),
            (2, "PO-2026-001", "Managed Kubernetes Cluster 24x7 Support", 1.0, 50000.0, 50000.0, "998313"),
            # PO-2026-002
            (3, "PO-2026-002", "Cisco Gigabit 48-Port Switch L3", 2.0, 36000.0, 72000.0, "851762"),
            (4, "PO-2026-002", "Cat6 UTP Patch Cable Bundle (100m)", 5.0, 2400.0, 12000.0, "854449"),
            # PO-2026-003
            (5, "PO-2026-003", "Enterprise SOC Threat Monitoring License (Q3)", 1.0, 200000.0, 200000.0, "998319"),
            # PO-2026-004
            (6, "PO-2026-004", "Express Pallet Cargo Shipments (BLR-DEL)", 30.0, 1500.0, 45000.0, "996511"),
            # PO-2026-005
            (7, "PO-2026-005", "Custom Corporate ID Badges & Lanyards (Pack of 500)", 2.0, 15000.0, 30000.0, "491110"),
        ]
        cursor.executemany("""
            INSERT INTO po_items (id, po_id, item_name, ordered_qty, unit_price, total_price, hsn_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, po_items)

        print("Seeding Goods Received Notes (GRN)...")
        grns = [
            ("GRN-2026-001", "PO-2026-001", "AWS Dedicated Cloud Instances (c6g.4xlarge)", 4.0, 4.0, "PASSED", "2026-08-15"),
            ("GRN-2026-001", "PO-2026-001", "Managed Kubernetes Cluster 24x7 Support", 1.0, 1.0, "PASSED", "2026-08-15"),
            ("GRN-2026-002", "PO-2026-002", "Cisco Gigabit 48-Port Switch L3", 2.0, 2.0, "PASSED", "2026-08-18"),
            ("GRN-2026-002", "PO-2026-002", "Cat6 UTP Patch Cable Bundle (100m)", 5.0, 5.0, "PASSED", "2026-08-18"),
            ("GRN-2026-003", "PO-2026-003", "Enterprise SOC Threat Monitoring License (Q3)", 1.0, 1.0, "PASSED", "2026-08-19"),
            ("GRN-2026-004", "PO-2026-004", "Express Pallet Cargo Shipments (BLR-DEL)", 30.0, 30.0, "PASSED", "2026-08-20"),
        ]
        cursor.executemany("""
            INSERT INTO goods_received_notes (grn_number, po_id, item_name, received_qty, accepted_qty, inspection_status, received_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, grns)

        print("Seeding Baseline Historical Settled Invoices for Fraud Detection...")
        # Seed INV-2026-8801 as a historical settled invoice so Agent 3 can detect duplicate invoice fraud
        historical_ledger = [
            ("INV-2026-8801", 3, "PO-2026-003", "PERFECT_MATCH", 0.0, 5.0, "pout_hist_998822", "PROCESSED", "AUTO_PAYOUT_TRIGGERED", "Historical baseline: settled on 2026-08-10", 1, "2026-08-10 11:30:00")
        ]
        cursor.executemany("""
            INSERT INTO audit_ledger (invoice_no, vendor_id, matched_po_id, audit_status, variance_amount, risk_score, payout_id, settlement_status, action_taken, notes, is_historical, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, historical_ledger)

    print("Generating Sample PDF Invoices...")
    generate_all_samples()

    print("LedgerMind Database and Sample Invoices seeded successfully!")

if __name__ == "__main__":
    seed_database()
