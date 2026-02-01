import requests
import os
import sys
import pytz
from datetime import datetime, timedelta

# --- CONFIGURATION ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# WATCHLIST (Your 18 Companies)
WATCHLIST = [
    "CENTUM", "SUPRIYA LIFESCI", "STYLAM", "MRS BECTORS", "TIPS MUSIC",
    "CONTROL PRINT", "YATHARTH", "PRECISION WIRES", "WONDERLA", 
    "UGRO CAPITAL", "ENVIRO INFRA", "RATEGAIN", "VENUS PIPES", "SJS ENTERPRISES", 
    "SANGHVI MOVERS", "JASH ENGINEERING", "FINEOTEX", "ANTONY WASTE"
]

# Timezone
IST = pytz.timezone('Asia/Kolkata')

# LOGIC FROM BENNYTHADIKARAN REPO
# We must use a session and these specific headers
SESSION = requests.Session()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.bseindia.com/",
    "Origin": "https://www.bseindia.com"
}
SESSION.headers.update(HEADERS)

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("❌ TG Credentials missing")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def get_bse_announcements(page=1):
    """
    Fetches announcements using the logic from BennyThadikaran/BseIndiaApi
    Endpoint: AnnSubCategoryGetData/w
    """
    url = f"https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?categ=0&page_no={page}"
    try:
        response = SESSION.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("Table", [])
    except Exception as e:
        print(f"⚠️ API Error: {e}")
        return []

def run_monk_mode():
    # Detect Mode: Manual (GitHub Menu) or Automatic (Cron 10m)
    mode = os.environ.get("INPUT_MODE", "LIVE")
    target_company = os.environ.get("INPUT_COMPANY", "").strip()
    
    print(f"🧘 Monk Mode: {mode} | Target: {target_company or 'ALL'}")

    # For History, we might need to check multiple pages, but usually page 1-2 covers recent days
    all_announcements = []
    
    # Fetch Page 1 (Always)
    print("📡 Fetching Page 1...")
    all_announcements.extend(get_bse_announcements(1))

    # Logic: Filter & Process
    history_buffer = []
    now = datetime.now(IST)
    cutoff = now - timedelta(minutes=15) # 15 min lookback for LIVE alerts

    for item in all_announcements:
        name = item.get('SLONGNAME', '')
        
        # 1. WATCHLIST CHECK
        # (If user requested specific company, check that. Else check full watchlist)
        is_relevant = False
        if mode == "HISTORY" and target_company:
            if target_company.upper() in name.upper(): is_relevant = True
        else:
            # Standard Watchlist Check
            for w in WATCHLIST:
                if w in name.upper(): 
                    is_relevant = True
                    break
        
        if not is_relevant: continue

        # 2. PARSE DATA
        news_id = item.get('NEWSID')
        subject = item.get('NEWSSUB')
        link = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{item.get('ATTACHMENTNAME')}"
        
        # Parse Date (Critical for Live vs History)
        # Format: 2024-02-01T15:30:00
        try:
            dt_str = item.get('NEWS_DT')
            filing_time = IST.localize(datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S"))
            time_str = filing_time.strftime("%d-%b %H:%M")
        except:
            continue

        # 3. ACTION
        if mode == "LIVE":
            # Only alert if NEW (last 15 mins)
            if filing_time > cutoff:
                msg = f"🚨 **{name}**\n⏱ `{time_str}`\n📝 {subject}\n🔗 [PDF Link]({link})"
                send_telegram(msg)
                print(f"✅ Sent Alert for {name}")

        elif mode == "HISTORY":
            # Collect last 5 for digest
            history_buffer.append(f"🔹 `{time_str}`\n**{name}**\n{subject}\n🔗 [PDF]({link})")
            if len(history_buffer) >= 5: break

    # Send History Digest
    if mode == "HISTORY":
        if history_buffer:
            header = f"📚 **History Report ({target_company or 'Watchlist'})**\n\n"
            send_telegram(header + "\n\n".join(history_buffer))
        else:
            send_telegram(f"❌ No recent announcements found for {target_company or 'Watchlist'} on Page 1.")

if __name__ == "__main__":
    run_monk_mode()
