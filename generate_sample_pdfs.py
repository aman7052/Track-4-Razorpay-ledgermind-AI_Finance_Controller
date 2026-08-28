import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)

def build_pdf(filename: str, vendor_data: dict, invoice_data: dict, items: list, totals: dict, bank_data: dict, notice: str = ""):
    filepath = os.path.join(SAMPLES_DIR, filename)
    doc = SimpleDocTemplate(filepath, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#072654'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#4A5568')
    )
    bold_label = ParagraphStyle(
        'BoldLabel',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1A202C')
    )
    right_bold = ParagraphStyle(
        'RightBold',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        fontName='Helvetica-Bold',
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#072654')
    )
    cell_style = ParagraphStyle(
        'Cell',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#2D3748')
    )
    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1A202C')
    )

    story = []

    # Header Row: Vendor Info & Tax Invoice Title
    header_table_data = [
        [
            Paragraph(f"<b>{vendor_data['name']}</b><br/>{vendor_data['address']}<br/>GSTIN: <b>{vendor_data['gstin']}</b><br/>Email: {vendor_data['email']}", subtitle_style),
            Paragraph("<b>TAX INVOICE</b><br/><font size=8 color='#718096'>ORIGINAL FOR RECIPIENT</font>", right_bold)
        ]
    ]
    header_table = Table(header_table_data, colWidths=[340, 200])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#072654'), spaceAfter=10, spaceBefore=4))

    # Invoice & Buyer Info
    buyer_info = f"""
    <b>BILL TO / BUYER:</b><br/>
    <b>Razorpay Technologies Private Limited</b><br/>
    SJR Cyber, 1st Floor, 22 Laskar Hosur Road, Adugodi<br/>
    Bengaluru, Karnataka 560030<br/>
    GSTIN: <b>29AABCR1234F1Z8</b>
    """

    invoice_meta = f"""
    <b>Invoice No:</b> {invoice_data['invoice_no']}<br/>
    <b>Invoice Date:</b> {invoice_data['date']}<br/>
    <b>Due Date:</b> {invoice_data['due_date']}<br/>
    <b>PO Reference:</b> <b>{invoice_data['po_ref']}</b><br/>
    <b>Payment Terms:</b> Net 30 Days
    """

    info_table_data = [
        [Paragraph(buyer_info, subtitle_style), Paragraph(invoice_meta, subtitle_style)]
    ]
    info_table = Table(info_table_data, colWidths=[320, 220])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F7FAFC')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 14))

    # Line Items Table
    table_headers = [
        Paragraph("<b>#</b>", bold_label),
        Paragraph("<b>Item Description</b>", bold_label),
        Paragraph("<b>HSN/SAC</b>", bold_label),
        Paragraph("<b>Qty</b>", bold_label),
        Paragraph("<b>Unit Price (INR)</b>", bold_label),
        Paragraph("<b>Total (INR)</b>", bold_label)
    ]
    
    table_rows = [table_headers]
    for idx, itm in enumerate(items, 1):
        table_rows.append([
            Paragraph(str(idx), cell_style),
            Paragraph(f"<b>{itm['name']}</b>", cell_style),
            Paragraph(itm.get('hsn', '998313'), cell_style),
            Paragraph(f"{itm['qty']}", cell_style),
            Paragraph(f"Rs. {itm['unit_price']:,.2f}", cell_style),
            Paragraph(f"Rs. {itm['total']:,.2f}", cell_bold)
        ])

    items_table = Table(table_rows, colWidths=[24, 230, 60, 45, 90, 91])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#072654')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # Totals & Bank Details Row
    bank_text = f"""
    <b>BANK & PAYMENT DETAILS:</b><br/>
    Beneficiary Name: <b>{vendor_data['name']}</b><br/>
    Bank Name: <b>{bank_data['bank_name']}</b><br/>
    Account Number: <b>{bank_data['account_no']}</b><br/>
    IFSC Code: <b>{bank_data['ifsc']}</b><br/>
    Branch: {bank_data.get('branch', 'Main Tech Park Branch, Bengaluru')}
    """

    totals_text = f"""
    <table width="100%">
        <tr><td><b>Subtotal:</b></td><td align="right">Rs. {totals['subtotal']:,.2f}</td></tr>
        <tr><td><b>CGST (9%):</b></td><td align="right">Rs. {totals['cgst']:,.2f}</td></tr>
        <tr><td><b>SGST (9%):</b></td><td align="right">Rs. {totals['sgst']:,.2f}</td></tr>
        <tr style="border-top: 1px solid #072654"><td><font size=11 color='#072654'><b>Grand Total:</b></font></td><td align="right"><font size=11 color='#072654'><b>Rs. {totals['grand_total']:,.2f}</b></font></td></tr>
    </table>
    """

    bottom_table_data = [
        [Paragraph(bank_text, subtitle_style), Paragraph(totals_text, subtitle_style)]
    ]
    bottom_table = Table(bottom_table_data, colWidths=[310, 230])
    bottom_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#EDF2F7')),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#FEFCBF') if notice else colors.HexColor('#EBF8FF')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
    ]))
    story.append(bottom_table)

    story.append(Spacer(1, 16))
    sig_text = """
    <b>For & on behalf of Billing Vendor:</b><br/><br/>
    <i>Digitally Verified & Authorized Signatory</i><br/>
    <font size=7 color='#718096'>This is a system generated tax invoice governed under Rule 48 of the CGST Rules, 2017.</font>
    """
    story.append(Paragraph(sig_text, subtitle_style))

    doc.build(story)
    print(f"Generated sample PDF: {filepath}")

def generate_all_samples():
    # 1. Sample 1: Perfect Match
    build_pdf(
        filename="invoice_perfect_match.pdf",
        vendor_data={
            "name": "CloudInfra Solutions Pvt Ltd",
            "address": "402 Tech Horizon Park, Whitefield, Bengaluru, KA 560066",
            "gstin": "29AABCC1122D1Z4",
            "email": "billing@cloudinfra.io"
        },
        invoice_data={
            "invoice_no": "INV-2026-1001",
            "date": "2026-08-20",
            "due_date": "2026-09-19",
            "po_ref": "PO-2026-001"
        },
        items=[
            {"name": "AWS Dedicated Cloud Instances (c6g.4xlarge)", "hsn": "998315", "qty": 4, "unit_price": 25000.0, "total": 100000.0},
            {"name": "Managed Kubernetes Cluster 24x7 Support", "hsn": "998313", "qty": 1, "unit_price": 50000.0, "total": 50000.0}
        ],
        totals={"subtotal": 150000.0, "cgst": 13500.0, "sgst": 13500.0, "grand_total": 177000.0},
        bank_data={"bank_name": "HDFC Bank", "account_no": "918273645012", "ifsc": "HDFC0001234", "branch": "Whitefield IT Park"}
    )

    # 2. Sample 2: Rate Mismatch (Overbilling by 25%)
    build_pdf(
        filename="invoice_rate_mismatch.pdf",
        vendor_data={
            "name": "Apex Hardware & Networking Hub",
            "address": "12 Silicon Lane, Electronic City, Bengaluru, KA 560100",
            "gstin": "29AABBA5566G1Z2",
            "email": "accounts@apexhardware.in"
        },
        invoice_data={
            "invoice_no": "INV-2026-2002",
            "date": "2026-08-21",
            "due_date": "2026-09-20",
            "po_ref": "PO-2026-002"
        },
        items=[
            {"name": "Cisco Gigabit 48-Port Switch L3", "hsn": "851762", "qty": 2, "unit_price": 45000.0, "total": 90000.0},  # PO was 36,000
            {"name": "Cat6 UTP Patch Cable Bundle (100m)", "hsn": "854449", "qty": 5, "unit_price": 3000.0, "total": 15000.0}   # PO was 2,400
        ],
        totals={"subtotal": 105000.0, "cgst": 9450.0, "sgst": 9450.0, "grand_total": 123900.0},
        bank_data={"bank_name": "ICICI Bank", "account_no": "001122334455", "ifsc": "ICIC0000011", "branch": "Electronic City"}
    )

    # 3. Sample 3: Duplicate Fraud Invoice
    build_pdf(
        filename="invoice_duplicate_fraud.pdf",
        vendor_data={
            "name": "Nexus Cybertech Systems",
            "address": "88 Koramangala 4th Block, Bengaluru, KA 560034",
            "gstin": "29AAACN9988H1Z5",
            "email": "finance@nexuscyber.com"
        },
        invoice_data={
            "invoice_no": "INV-2026-8801",  # Already paid in ledger!
            "date": "2026-08-22",
            "due_date": "2026-09-21",
            "po_ref": "PO-2026-003"
        },
        items=[
            {"name": "Enterprise SOC Threat Monitoring License (Q3)", "hsn": "998319", "qty": 1, "unit_price": 200000.0, "total": 200000.0}
        ],
        totals={"subtotal": 200000.0, "cgst": 18000.0, "sgst": 18000.0, "grand_total": 236000.0},
        bank_data={"bank_name": "Axis Bank", "account_no": "987654321098", "ifsc": "UTIB0000888", "branch": "Koramangala"}
    )

    # 4. Sample 4: Quantity Mismatch & Bank Account Tampering
    build_pdf(
        filename="invoice_qty_and_bank_tamper.pdf",
        vendor_data={
            "name": "SwiftLogistics & Freight Express",
            "address": "Zone 5 Cargo Complex, Devanahalli, Bengaluru, KA 562300",
            "gstin": "29AABCS7744K1Z9",
            "email": "dispatch@swiftlogistics.co"
        },
        invoice_data={
            "invoice_no": "INV-2026-4004",
            "date": "2026-08-23",
            "due_date": "2026-09-22",
            "po_ref": "PO-2026-004"
        },
        items=[
            {"name": "Express Pallet Cargo Shipments (BLR-DEL)", "hsn": "996511", "qty": 50, "unit_price": 1500.0, "total": 75000.0} # PO was 30 units
        ],
        totals={"subtotal": 75000.0, "cgst": 6750.0, "sgst": 6750.0, "grand_total": 88500.0},
        # Tampered bank account (DB has 112233445566, IFSC SBIN0004567)
        bank_data={"bank_name": "Suspicious Off-shore Bank", "account_no": "999988887777", "ifsc": "PUNB0999999", "branch": "Unknown Branch"}
    )

    # 5. Sample 5: Unauthorized Vendor & Invalid GST
    build_pdf(
        filename="invoice_unauthorized_vendor.pdf",
        vendor_data={
            "name": "Shadow Phantom Enterprise Ltd",
            "address": "Plot 00, Ghost Industrial Area, Unknown, DL 110001",
            "gstin": "99XXXXX0000X1Z",  # Invalid GSTIN format
            "email": "unregistered@phantomfake.biz"
        },
        invoice_data={
            "invoice_no": "INV-2026-9999",
            "date": "2026-08-24",
            "due_date": "2026-09-23",
            "po_ref": "PO-2026-999"  # Non-existent PO
        },
        items=[
            {"name": "Unspecified Strategic Consultation Services", "hsn": "999999", "qty": 3, "unit_price": 100000.0, "total": 300000.0}
        ],
        totals={"subtotal": 300000.0, "cgst": 27000.0, "sgst": 27000.0, "grand_total": 354000.0},
        bank_data={"bank_name": "Unverified Credit Society", "account_no": "555544443333", "ifsc": "KKBK0000999", "branch": "Central"}
    )

if __name__ == "__main__":
    generate_all_samples()
