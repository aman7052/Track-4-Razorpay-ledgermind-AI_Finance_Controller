def get_custom_css() -> str:
    return """
    <style>
        /* Hide Streamlit default header, footer, and deploy button */
        header[data-testid="stHeader"] { visibility: hidden; height: 0% !important; margin: 0 !important; padding: 0 !important; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .stDeployButton { display: none !important; }
        
        /* Main container padding */
        .block-container {
            padding-top: 1.25rem !important;
            padding-bottom: 2rem !important;
            max-width: 1260px !important;
        }

        /* Typography */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], .stMarkdown, .stText, p, span, label, div {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        /* Project Header & Badge Row (Clean Flexbox - No Overlaps) */
        .project-header {
            margin-bottom: 1.5rem;
        }

        .project-badge-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }

        .project-badge {
            background: #2563EB;
            color: #FFFFFF;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 4px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            font-family: 'JetBrains Mono', monospace;
            display: inline-block;
        }

        .project-pill {
            background: #1E293B;
            color: #94A3B8;
            font-size: 11.5px;
            font-weight: 500;
            padding: 3px 10px;
            border-radius: 4px;
            border: 1px solid #334155;
            font-family: 'JetBrains Mono', monospace;
            display: inline-block;
        }

        .project-title {
            font-size: 32px;
            font-weight: 800;
            color: #F8FAFC;
            margin: 6px 0 8px 0;
            letter-spacing: -0.5px;
            line-height: 1.25;
        }

        .project-title b {
            color: #38BDF8;
        }

        .project-desc {
            font-size: 14px;
            color: #94A3B8;
            margin: 0;
            line-height: 1.5;
        }

        /* 4 White Metric Cards on Dark Background */
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-bottom: 18px;
        }

        .metric-box {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }

        .metric-title {
            font-size: 11px;
            font-weight: 700;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .metric-number {
            font-size: 26px;
            font-weight: 800;
            color: #0F172A;
            margin: 4px 0 2px 0;
            font-family: 'Inter', sans-serif;
        }

        .metric-hint {
            font-size: 12px;
            color: #64748B;
            font-weight: 500;
        }

        /* Status tags */
        .tag-success {
            background-color: #ECFDF5;
            color: #047857;
            border: 1px solid #A7F3D0;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11.5px;
            display: inline-block;
        }

        .tag-warning {
            background-color: #FFFBEB;
            color: #B45309;
            border: 1px solid #FDE68A;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11.5px;
            display: inline-block;
        }

        .tag-danger {
            background-color: #FEF2F2;
            color: #B91C1C;
            border: 1px solid #FECACA;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11.5px;
            display: inline-block;
        }

        .tag-info {
            background-color: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #BFDBFE;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11.5px;
            display: inline-block;
        }

        /* Step cards */
        .step-row {
            background: #1E222D;
            border: 1px solid #2E3440;
            border-radius: 6px;
            padding: 10px 14px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .step-row-success { border-left: 3px solid #10B981; }
        .step-row-warning { border-left: 3px solid #F59E0B; }
        .step-row-danger { border-left: 3px solid #EF4444; }
        .step-row-info { border-left: 3px solid #3B82F6; }

        /* Payout Receipt */
        .payout-box {
            background: #0F172A;
            border-radius: 8px;
            padding: 18px 20px;
            color: #FFFFFF;
            margin-top: 12px;
            border: 1px solid #334155;
        }

        .payout-row {
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            margin-bottom: 6px;
            color: #94A3B8;
        }

        .payout-row-total {
            display: flex;
            justify-content: space-between;
            font-size: 15px;
            font-weight: 700;
            color: #FFFFFF;
            border-top: 1px solid #334155;
            padding-top: 8px;
            margin-top: 8px;
        }

        .mono {
            font-family: 'JetBrains Mono', monospace;
        }

        /* Green Sandbox Account Badge */
        .sandbox-acct-badge {
            background: #0F392B;
            color: #4ADE80;
            font-family: 'JetBrains Mono', monospace;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            border: 1px solid #166534;
            display: inline-block;
            font-weight: 600;
        }

        /* Streamlit Tabs */
        button[data-baseweb="tab"] {
            font-size: 13.5px !important;
            font-weight: 600 !important;
            padding: 8px 16px !important;
        }
    </style>
    """
