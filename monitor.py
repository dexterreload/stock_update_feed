import os
import time
import requests
import pytz
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
IST = pytz.timezone('Asia/Kolkata')

# Verified Scrip Codes
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

def send_telegram(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def setup_driver():
    """Launches a Stealthy Headless Chrome Browser"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Modern headless mode (undetectable)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def run_monk_mode():
    mode = os.environ.get("INPUT_MODE", "LIVE")
    target_input = os.environ.get("INPUT_COMPANY", "").strip().upper()
    
    print(f"🚀 Launching Chrome Engine... (Mode: {mode})")
    driver = setup_driver()
    
    try:
        # --- SCENARIO A: HISTORY (MANUAL REQUEST) ---
        if mode == "HISTORY" and target_input:
            # 1. Identify Target
            target_code = None
            target_name = None
            for name, code in WATCHLIST.items():
                if target_input in name:
                    target_code = code
                    target_name = name
                    break
            
            if not target_code:
                send_telegram(f"❌ Unknown Company: {target_input}")
                return

            # 2. Visit the EXACT Company Page from your screenshot
            url = f"https://www.bseindia.com/stock-share-price/x/y/{target_code}/corp-announcements/"
            print(f"🔗 Visiting: {url}")
            driver.get(url)
            time.sleep(5) # Let JavaScript load
            
            # 3. Scrape the "Corp Announcements" Table
            # The table rows are usually in a specific div. We grab all text to be safe.
            rows = driver.find_elements(By.XPATH, "//table[contains(@class, 'table')]//tr")
            
            found_count = 0
            history_msg = f"📂 **Official History: {target_name}**\n\n"
            
            for row in rows:
                text = row.text
                if not text or len(text) < 20: continue
                
                # Check if it looks like a filing (contains date/PDF size)
                if "MB" in text or "KB" in text or "XBRL" in text:
                    # Clean up the text for display
                    lines = text.split('\n')
                    summary = lines[0][:100] + "..." if len(lines) > 0 else "Update"
                    
                    history_msg += f"🔹 {summary}\n\n"
                    found_count += 1
                    if found_count >= 5: break
            
            if found_count > 0:
                send_telegram(history_msg)
            else:
                send_telegram(f"⚠️ Page loaded, but no filings found on screen for {target_name}.")

        # --- SCENARIO B: LIVE MONITORING (ALL STOCKS) ---
        else:
            # For live monitoring, checking 18 pages is too slow.
            # We hit the GLOBAL announcements page and filter for our 18 names.
            url = "https://www.bseindia.com/corporates/ann.aspx"
            print(f"📡 Scanning Global Feed: {url}")
            driver.get(url)
            time.sleep(3)
            
            rows = driver.find_elements(By.XPATH, "//table[@id='lblann']/tbody/tr")
            
            now = datetime.now(IST)
            cutoff = now - timedelta(minutes=20) # 20 min buffer
            
            for row in rows[:40]: # Check top 40 global filings
                text = row.text.upper()
                
                # Check against ALL 18 companies
                matched_company = None
                for name in WATCHLIST.keys():
                    if name in text:
                        matched_company = name
                        break
                
                if matched_company:
                    # Found a match! Extract Link
                    try:
                        link_elem = row.find_element(By.TAG_NAME, "a")
                        link = link_elem.get_attribute("href")
                        
                        # Send Alert
                        send_telegram(f"🚨 **LIVE: {matched_company}**\nFound on BSE Dashboard.\n🔗 [Open Link]({link})")
                        print(f"✅ Found: {matched_company}")
                    except:
                        pass

    except Exception as e:
        print(f"🔥 Critical Error: {e}")
        send_telegram(f"⚠️ Monitor Crashed: {str(e)}")
    
    finally:
        driver.quit()
        print("🔒 Browser Closed")

if __name__ == "__main__":
    run_monk_mode()
