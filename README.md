# LedgerMind: Automated 3-Way Invoice Reconciliation & Payout Controller

LedgerMind is an accounts payable automation system designed to eliminate manual invoice verification. It compares vendor invoices against contracted Purchase Orders (POs) and Goods Received Notes (GRNs), checks for common billing errors and fraud patterns (like duplicate submissions, unit rate inflation, or modified bank details), and handles payouts with automatic TDS withholding.

---

## The Problem
In standard business operations, accounts payable teams spend days manually reviewing vendor invoices:
- Line items are manually compared against purchase contracts and warehouse delivery receipts.
- Overcharges (e.g. slight price inflation or quantity mismatches) often slip through.
- Duplicate invoices and unauthorized bank account changes can lead to financial losses.
- Slow verification cycles delay payments and damage vendor relationships.

## How It Works
LedgerMind splits invoice processing into four specialized stages:

1. **Invoice Parsing (`InvoiceParserAgent`)**  
   Extracts vendor metadata, line items, 15-character GSTINs, PO numbers, and banking details from PDF invoices using layout parsing (`pdfplumber`) with heuristic/LLM fallback.

2. **3-Way Reconciliation (`ReconciliationAgent`)**  
   Matches each billed line item against contracted Purchase Orders (`po_items`) and physical delivery receipts (`goods_received_notes`). It computes unit price differences ($\Delta \text{Rate}$), quantity differences ($\Delta \text{Qty}$), and total variances.

3. **Anomaly & Risk Auditing (`AnomalyAuditAgent`)**  
   Evaluates risk on a 0–100 scale based on:
   - Duplicate invoice checks against the payment ledger
   - Bank account & IFSC validation against verified vendor records
   - Price inflation beyond contracted rates (>10% baseline)
   - 15-character GSTIN structure and Indian state code validation

4. **Settlement & Dispute Action (`SettlementAgent`)**  
   - **Clean Invoices (100% Match & Risk < 20):** Calculates applicable TDS (Section 194C for contracts/logistics @ 2%, Section 194J for software @ 2% or 10%) and triggers an instant simulated RazorpayX IMPS payout with bank UTR and webhook generation.
   - **Flagged Invoices:** Places the payment on hold and auto-drafts a line-item dispute email addressed to the vendor.

```
Invoice PDF ───> [ 1. Parser ] ───> [ 2. 3-Way Recon ] ───> [ 3. Risk Audit ] ───> [ 4. Settlement ]
                                           │                        │                        │
                                   (PO / GRN Database)       (Audit Ledger)          ┌───────┴───────┐
                                                                                     ▼               ▼
                                                                                Auto Payout    Dispute Notice
                                                                                (RazorpayX)    (Itemized Email)
```

---

## Project Structure

```
├── app.py                      # Main Streamlit web application
├── seed_db.py                  # Database initialization and sample data seeder
├── generate_sample_pdfs.py     # PDF invoice generator using ReportLab
├── ledgermind.db               # SQLite database
├── requirements.txt            # Python dependencies
├── run_app.bat                 # Windows one-click startup script
│
├── agents/                     # Processing agents
│   ├── workflow.py             # Controller coordinating the pipeline
│   ├── invoice_parser.py       # PDF OCR and structured data extractor
│   ├── reconciliation.py       # 3-way matching logic (Invoice vs PO vs GRN)
│   ├── anomaly_auditor.py      # Rule-based fraud and risk checks
│   └── settlement.py           # Payout trigger and dispute handler
│
├── database/                   # Database layer
│   └── db.py                   # SQLite schema and connections
│
├── schemas/                    # Pydantic data schemas
│   └── models.py               # Data models for invoices, matches, risk, and payouts
│
├── services/                   # Backend services
│   ├── llm_factory.py          # LLM router with offline heuristic parser
│   ├── razorpay_mock.py        # RazorpayX payout simulation with TDS calculation
│   └── email_service.py        # Dispute email composer
│
├── samples/                    # Pre-generated sample PDF invoices
├── tests/                      # Automated test suite
│   └── test_pipeline.py        # End-to-end integration tests
│
└── ui/                         # Streamlit UI styles and components
    ├── styles.py               # Custom CSS styling
    └── components.py           # UI metric cards, timeline, diff table, and receipt
```

---

## Quickstart Guide

### Prerequisites
- Python 3.10 or higher
- pip package manager

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/aman7052/Track-4-Razorpay-ledgermind-AI_Finance_Controller.git
cd Track-4-Razorpay-ledgermind-AI_Finance_Controller
pip install -r requirements.txt
```

### 2. Set Up Database & Sample Invoices
Initialize the SQLite database (`ledgermind.db`) and generate the 5 test invoice PDFs:
```bash
python seed_db.py
```

### 3. Run the Automated Tests
Run integration tests across all 5 test scenarios:
```bash
python tests/test_pipeline.py
```

### 4. Launch the Web Application
```bash
streamlit run app.py
```
*(On Windows, you can also double-click `run_app.bat`)*

Open your browser at `http://localhost:8501`.

---

## Built-In Test Scenarios

The system includes 5 sample invoices to test different real-world conditions:

| # | Scenario | File | Expected Result | Action Taken |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **Clean Invoice** | `invoice_perfect_match.pdf` | 100% Match, Risk: `0/100` | Auto Payout via RazorpayX (TDS calculated, UTR generated) |
| **2** | **Rate Inflation (+25%)** | `invoice_rate_mismatch.pdf` | +₹24,780 overbilling | Payment Held; Dispute email generated |
| **3** | **Duplicate Fraud** | `invoice_duplicate_fraud.pdf` | Previously settled invoice | Payment Blocked (Duplicate invoice fraud) |
| **4** | **Qty Mismatch & Bank Change** | `invoice_qty_and_bank_tamper.pdf` | Qty diff + Bank mismatch | Payment Held; Bank tampering alert flagged |
| **5** | **Unregistered Vendor** | `invoice_unauthorized_vendor.pdf` | Invalid PO + Invalid GSTIN | Payment Blocked |

---

## Configuration & Environment Variables

The application is designed to run **completely offline** with zero API keys using its built-in heuristic parser.

If you want to use cloud LLMs for extraction, copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Available environment variables:
```env
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Tech Stack
- **Backend:** Python 3.10+, Pydantic v2, SQLite3
- **Document Processing:** pdfplumber, pypdf, ReportLab
- **UI & Visualization:** Streamlit, Plotly, Pandas
- **Integrations:** RazorpayX Payouts Simulator, Indian Income Tax TDS (194C / 194J)

---

## License
MIT License. Feel free to use and adapt this project for your own experiments.
