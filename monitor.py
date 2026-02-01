import requests
import os
import pytz
import sys
from datetime import datetime, timedelta

# --- CONFIGURATION ---
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Detect how the script was started
# 'schedule' = Automatic 10-min poll
# 'workflow_dispatch' = You pressed the button
EVENT_NAME = os.environ.get("GITHUB_EVENT_NAME", "schedule")

# Manual Inputs (Only used if you triggered it manually)
MANUAL_MODE = os.environ.get("INPUT_MODE", "LIVE") 
MANUAL_TARGET = os.environ.get("INPUT_COMPANY", "").strip()

# WATCHLIST (Your 18 Companies)
WATCHLIST = [
    "CENTUM", "SUPRIYA LIFESCI", "STYLAM", "MRS BECTORS", "TIPS MUSIC",
    "CONTROL PRINT", "YATHARTH", "PRECISION WIRES", "PREC. WIRES", "WONDERLA", 
    "UGRO CAPITAL", "ENVIRO INFRA", "RATEGAIN", "VENUS PIPES", "SJS ENTERPRISES", 
    "SANGHVI MOVERS", "JASH ENGINEERING", "FINEOTEX", "ANTONY WASTE"
]

IST = pytz.timezone('Asia/Kolkata')
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Referer": "https://www.bseindia.com/"
}

def send_telegram(text, parse_mode="Markdown"):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def get_target_companies():
    """Decides which companies to scan based on the Trigger"""
    # 1. Automatic Polling -> Scan EVERYTHING
    if EVENT_NAME == "schedule":
        return WATCHLIST, "LIVE"
    
    # 2. Manual Trigger -> Check user inputs
    if MANUAL_TARGET:
        # User asked for specific company (e.g. "Supriya")
        return [MANUAL_TARGET], MANUAL_MODE
    else:
        # User left company blank -> Scan EVERYTHING
        return WATCHLIST, MANUAL_MODE

def check_bse():
    targets, mode = get_target_companies()
    
    if mode == "HISTORY":
        print(f"📚 Fetching History for: {targets}")
        send_telegram(f"⏳ **Fetching History for:** `{targets[0]}`...")
    else:
        print("🔴 Running Live Scan...")

    url = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?categ=0"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        data = response.json()
        
        now = datetime.now(IST)
        cutoff = now - timedelta(minutes=15) # For Live Polling
        
        history_buffer = []
        
        for item in data.get('Table', []):
            name = item.get('SLONGNAME')
            
            # Smart Matching: Check if this news item matches our Target List
            match_found = False
            for t in targets:
                if t.upper() in name.upper():
                    match_found = True
                    break
            
            if not match_found: continue

            # Extract Data
            news_dt = item.get('NEWS_DT')
            try:
                filing_time = IST.localize(datetime.strptime(news_dt, "%Y-%m-%dT%H:%M:%S"))
            except:
                continue

            subject = item.get('NEWSSUB')
            link = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{item.get('ATTACHMENTNAME')}"
            
            # --- LOGIC BRANCHING ---
            
            # BRANCH A: HISTORY MODE (Return last 5 updates, regardless of time)
            if mode == "HISTORY":
                date_pretty = filing_time.strftime('%d-%b %H:%M')
                history_buffer.append(f"🗓 `{date_pretty}`\n**{name}**\n{subject}\n🔗 [PDF]({link})")
                if len(history_buffer) >= 5: break

            # BRANCH B: LIVE POLLING (Only return if < 15 mins old)
            elif mode == "LIVE":
                if filing_time > cutoff:
                    msg = f"🚨 **LIVE UPDATE | {name}**\n📝 {subject}\n🔗 [Read Document]({link})"
                    send_telegram(msg)
                    print(f"Sent Alert for {name}")

        # Send Compiled History
        if mode == "HISTORY":
            if history_buffer:
                final_msg = f"📂 **Last 5 Updates for {targets[0]}**\n\n" + "\n\n".join(history_buffer)
                send_telegram(final_msg)
            else:
                send_telegram(f"❌ No recent data found for **{targets[0]}** in BSE feeds.")

    except Exception as e:
        print(f"Error: {e}")
        # Only alert on error if it was a manual request (don't spam on polling)
        if EVENT_NAME == "workflow_dispatch":
            send_telegram(f"⚠️ System Error: {str(e)}")

if __name__ == "__main__":
    check_bse()
