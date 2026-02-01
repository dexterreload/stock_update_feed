import requests
import os
import pytz
from datetime import datetime, timedelta

# --- CONFIGURATION ---
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# YOUR WATCHLIST (Extracted from your image)
# We use partial names to ensure matches across BSE/NSE variations
WATCHLIST = [
    "CENTUM", "SUPRIYA LIFESCI", "STYLAM", "MRS BECTORS", "TIPS MUSIC",
    "CONTROL PRINT", "YATHARTH", "PRECISION WIRES", "PREC. WIRES", "WONDERLA", 
    "UGRO CAPITAL", "ENVIRO INFRA", "RATEGAIN", "VENUS PIPES", "SJS ENTERPRISES", 
    "SANGHVI MOVERS", "JASH ENGINEERING", "FINEOTEX", "ANTONY WASTE"
]

# Indian Standard Time (Essential for correct filtering)
IST = pytz.timezone('Asia/Kolkata')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.bseindia.com/"
}

def send_alert(company, subject, link, source):
    """Sends the notification to your phone"""
    msg = (
        f"🚨 **{company}** ({source})\n"
        f"📝 {subject}\n"
        f"🔗 [View Document]({link})"
    )
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": msg, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Alert Failed: {e}")

def check_watchlist(company_name):
    """Returns True if the company is in your list"""
    if not company_name: return False
    company_upper = company_name.upper()
    for watch in WATCHLIST:
        if watch in company_upper:
            return True
    return False

def check_bse():
    print("Scanning BSE...")
    url = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?categ=0"
    try:
        # 1. Fetch Data
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()
        
        # 2. Define "New" (Last 15 mins)
        now = datetime.now(IST)
        cutoff = now - timedelta(minutes=15)

        for item in data.get('Table', []):
            # Parse Time
            news_dt = item.get('NEWS_DT') # Format: 2024-02-01T14:30:00
            try:
                filing_time = IST.localize(datetime.strptime(news_dt, "%Y-%m-%dT%H:%M:%S"))
            except:
                continue

            # 3. Filter by Time & Watchlist
            if filing_time > cutoff:
                name = item.get('SLONGNAME')
                if check_watchlist(name):
                    subject = item.get('NEWSSUB')
                    link = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{item.get('ATTACHMENTNAME')}"
                    
                    print(f"FOUND: {name}")
                    send_alert(name, subject, link, "BSE")

    except Exception as e:
        print(f"BSE Error: {e}")

# Note: NSE often blocks cloud servers. This function tries, but BSE is the primary reliable source.
def check_nse():
    print("Scanning NSE...")
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        # Cookie handshake
        session.get("https://www.nseindia.com", timeout=10)
        
        url = "https://www.nseindia.com/api/corporate-announcements?index=equities"
        response = session.get(url, timeout=10)
        data = response.json()

        now = datetime.now(IST)
        cutoff = now - timedelta(minutes=15)

        for item in data[:20]:
            date_str = item.get('sort_date')
            try:
                filing_time = IST.localize(datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S"))
            except:
                continue

            if filing_time > cutoff:
                symbol = item.get('symbol')
                if check_watchlist(symbol):
                    desc = item.get('desc')
                    link = item.get('attchmntText')
                    print(f"FOUND: {symbol}")
                    send_alert(symbol, desc, link, "NSE")

    except Exception:
        print("NSE Access Blocked (Standard for Cloud IPs). relying on BSE.")

if __name__ == "__main__":
    check_bse()
    check_nse()
