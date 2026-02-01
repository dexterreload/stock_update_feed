import requests
import os
import pytz
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# OFFICIAL BSE SCRIP CODES
WATCHLIST = {
    "CENTUM ELECTRONICS": "517544",
    "SUPRIYA LIFESCIENCE": "543434",
    "STYLAM INDUSTRIES": "526951",
    "MRS BECTORS FOOD": "543253",
    "TIPS MUSIC": "532375",
    "CONTROL PRINT": "522295",
    "YATHARTH HOSPITAL": "543950",
    "PRECISION WIRES": "523539",
    "WONDERLA HOLIDAYS": "538268",
    "UGRO CAPITAL": "511742",
    "ENVIRO INFRA": "544290",
    "RATEGAIN TRAVEL": "543417",
    "VENUS PIPES": "543528",
    "SJS ENTERPRISES": "543387",
    "SANGHVI MOVERS": "530073",
    "JASH ENGINEERING": "544402",
    "FINEOTEX CHEMICAL": "533333",
    "ANTONY WASTE": "543254"
}

IST = pytz.timezone('Asia/Kolkata')

# HEADERS (Critical)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://www.bseindia.com",
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*"
}

def send_telegram(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def get_company_history(scrip_code, company_name):
    # Calculate "From Date" (90 days ago) to ensure we get history
    from_date = (datetime.now(IST) - timedelta(days=90)).strftime("%Y%m%d")
    
    # Endpoint matches the 'Corp Announcements' tab on BSE
    url = f"https://api.bseindia.com/BseIndiaAPI/api/AnnouncemnetData/w?strCat=-1&strPrevDate={from_date}&strScrip={scrip_code}&strSearch=P"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()
        return data.get("Table", [])
    except Exception as e:
        print(f"⚠️ Error fetching {company_name}: {e}")
        return []

def run_surveillance():
    # Detect Mode (Manual or Automatic)
    mode = os.environ.get("INPUT_MODE", "LIVE")
    target_input = os.environ.get("INPUT_COMPANY", "").strip().upper()
    
    print(f"🕵️‍♂️ Running Mode: {mode}")

    # 1. IDENTIFY TARGETS
    targets = {}
    if target_input:
        # Fuzzy search for manual input
        for name, code in WATCHLIST.items():
            if target_input in name:
                targets[name] = code
                break
        if not targets:
            send_telegram(f"❌ Could not find **{target_input}** in Watchlist.")
            return
    else:
        # Scan ALL (for polling)
        targets = WATCHLIST

    # 2. SCAN
    now = datetime.now(IST)
    cutoff = now - timedelta(minutes=15) # 15 min lookback for LIVE alerts

    for name, code in targets.items():
        print(f"Scanning {name} ({code})...")
        announcements = get_company_history(code, name)
        
        history_buffer = []

        for item in announcements:
            subject = item.get('NEWSSUB')
            link = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{item.get('ATTACHMENTNAME')}"
            
            try:
                dt_str = item.get('NEWS_DT') # Format: 2024-02-01T15:30:00
                filing_time = IST.localize(datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S"))
                time_pretty = filing_time.strftime("%d-%b %H:%M")
            except:
                continue

            # --- LOGIC BRANCHING ---
            
            # MODE A: HISTORY (Show last 5, ignoring time)
            if mode == "HISTORY":
                history_buffer.append(f"🗓 `{time_pretty}`\n📝 {subject}\n🔗 [PDF]({link})")
                if len(history_buffer) >= 5: break

            # MODE B: LIVE (Only alert if < 15 mins old)
            elif mode == "LIVE" or mode == "schedule": 
                if filing_time > cutoff:
                    msg = f"🚨 **{name}**\n⏱ `{time_pretty}`\n📝 {subject}\n🔗 [Read PDF]({link})"
                    send_telegram(msg)
                    print(f"✅ Alert Sent: {name}")

        # Send History Digest (One message per company)
        if mode == "HISTORY":
            if history_buffer:
                msg = f"📂 **History: {name}**\n\n" + "\n\n".join(history_buffer)
                send_telegram(msg)
            else:
                send_telegram(f"❌ No recent filings found for **{name}** (Last 90 Days)")
        
        # Polite delay to prevent blocking
        time.sleep(0.5)

if __name__ == "__main__":
    run_surveillance()
