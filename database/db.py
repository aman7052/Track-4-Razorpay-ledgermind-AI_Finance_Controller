import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ledgermind.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db_cursor() -> Generator[sqlite3.Cursor, None, None]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    with get_db_cursor() as cursor:
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            gstin TEXT NOT NULL,
            bank_account TEXT NOT NULL,
            ifsc TEXT NOT NULL,
            email TEXT NOT NULL,
            category TEXT DEFAULT 'IT_SERVICES',
            verified_status TEXT DEFAULT 'VERIFIED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_id TEXT PRIMARY KEY,
            vendor_id INTEGER NOT NULL,
            status TEXT DEFAULT 'APPROVED',
            total_budget REAL NOT NULL,
            issued_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vendor_id) REFERENCES vendors (id)
        );

        CREATE TABLE IF NOT EXISTS po_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            ordered_qty REAL NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            hsn_code TEXT,
            FOREIGN KEY (po_id) REFERENCES purchase_orders (po_id)
        );

        CREATE TABLE IF NOT EXISTS goods_received_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grn_number TEXT NOT NULL,
            po_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            received_qty REAL NOT NULL,
            accepted_qty REAL NOT NULL,
            inspection_status TEXT DEFAULT 'PASSED',
            received_date TEXT NOT NULL,
            FOREIGN KEY (po_id) REFERENCES purchase_orders (po_id)
        );

        CREATE TABLE IF NOT EXISTS audit_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            vendor_id INTEGER,
            matched_po_id TEXT,
            audit_status TEXT NOT NULL,
            variance_amount REAL DEFAULT 0.0,
            risk_score REAL DEFAULT 0.0,
            payout_id TEXT,
            settlement_status TEXT DEFAULT 'PENDING',
            action_taken TEXT,
            notes TEXT,
            is_historical INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS payout_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payout_id TEXT NOT NULL UNIQUE,
            invoice_no TEXT NOT NULL,
            vendor_id INTEGER,
            gross_amount REAL NOT NULL,
            tds_amount REAL NOT NULL,
            net_amount REAL NOT NULL,
            utr TEXT NOT NULL,
            mode TEXT DEFAULT 'IMPS',
            status TEXT DEFAULT 'PROCESSED',
            webhook_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Migration check for is_historical column
        try:
            cursor.execute("SELECT is_historical FROM audit_ledger LIMIT 1;")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE audit_ledger ADD COLUMN is_historical INTEGER DEFAULT 0;")

