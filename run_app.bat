@echo off
echo ========================================================
echo Starting LedgerMind: AI Finance Controller (Razorpay Buildathon)
echo ========================================================

echo [1/3] Freeing port 8501 from any previous Streamlit session...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [2/3] Initializing SQLite database and compiling sample invoices...
python seed_db.py

echo [3/3] Launching LedgerMind Streamlit Dashboard...
python -m streamlit run app.py --server.port 8501

pause
