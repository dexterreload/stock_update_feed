import os
import time
import requests
import pytz
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIG ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
IST = pytz.timezone('Asia/Kolkata')

# Verified Scrip Codes
WATCHLIST = {
    "CENTUM ELECTRONICS": "517544",
    "SUPRIYA LIFESCIENCE": "543434",
    "STYLAM INDUSTRIES": "526951",
    "MRS BECTORS": "543253",
    "TIPS MUSIC": "532375",
    "CONTROL PRINT": "522295",
    "YATHARTH": "543950",
    "PRECISION WIRES": "523539",
    "WONDERLA": "538268",
    "UGRO CAPITAL": "511742",
    "ENVIRO INFRA": "544290",
    "RATEGAIN": "543417",
    "VENUS PIPES": "543528",
    "SJS ENTERPRISES": "543387",
    "SANGHVI MOVERS": "530073",
    "JASH ENGINEERING": "544402",
    "FINEOTEX": "533333",
    "ANTONY WASTE": "543254"
}

def send_telegram(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new") 
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

def run_monk_mode():
    mode = os.environ.get("INPUT_MODE", "LIVE")
    target_input = os.environ.get("INPUT_COMPANY", "").strip().upper()
    
    print(f"🚀 Launching Chrome... (Mode: {mode})")
    driver = setup_driver()
    
    try:
        # 1. Go to the MAIN Dashboard (Most reliable page)
        driver.get("https://www.bseindia.com/corporates/ann.aspx")
        time.sleep(3) # Wait for load

        # 2. Determine Search Target
        target_code = None
        target_name = None

        if mode == "HISTORY" and target_input:
            for name, code in WATCHLIST.items():
                if target_input in name:
                    target_code = code
                    target_name = name
                    break
            if not target_code:
                send_telegram(f"❌ Unknown Company: {target_input}")
                return
        
        # 3. Perform Search (If History) or Scan Top (If Live)
        if target_code:
            print(f"🔎 Searching for {target_name} ({target_code})...")
            
            # Find Search Box and Type Code
            search_box = driver.find_element(By.ID, "txtScrip")
            search_box.clear()
            search_box.send_keys(target_code)
            time.sleep(1)
            
            # Hit Enter (More reliable than clicking submit sometimes)
            search_box.send_keys(Keys.RETURN) 
            time.sleep(2)
            
            # Click Submit button explicitly to be sure
            try:
                driver.find_element(By.ID, "btnSubmit").click()
            except:
                pass
            
            time.sleep(5) # Wait for table refresh

        # 4. Scrape the Main Table (ID: lblann)
        print("📖 Reading Table...")
        rows = driver.find_elements(By.XPATH, "//table[@id='lblann']/tbody/tr")
        
        msg_buffer = []
        
        for row in rows:
            text = row.text
            if not text or len(text) < 10: continue

            # For HISTORY: Grab top 5
            if mode == "HISTORY":
                # Clean Text
                lines = text.split('\n')
                # Date is usually 1st col, Company 2nd, Desc 3rd
                # We just grab the whole block for context
                
                # Check if it has a PDF link
                try:
                    link = row.find_element(By.TAG_NAME, "a").get_attribute("href")
                except:
                    link = "No Link"

                msg_buffer.append(f"🔹 {lines[0][:100]}...\n🔗 [View PDF]({link})")
                if len(msg_buffer) >= 5: break
            
            # For LIVE: Check if Company is in Watchlist
            else:
                text_upper = text.upper()
                for name in WATCHLIST.keys():
                    if name in text_upper:
                        # Found a match!
                        try:
                            link = row.find_element(By.TAG_NAME, "a").get_attribute("href")
                            send_telegram(f"🚨 **LIVE: {name}**\n{text[:100]}...\n🔗 [View PDF]({link})")
                            print(f"✅ Alert sent for {name}")
                        except:
                            pass
                        break

        # Send History Report
        if mode == "HISTORY":
            if msg_buffer:
                final_msg = f"📂 **Official Filings: {target_name}**\n\n" + "\n\n".join(msg_buffer)
                send_telegram(final_msg)
            else:
                send_telegram(f"⚠️ Search ran, but table was empty for {target_name}. (BSE might be slow)")

    except Exception as e:
        print(f"🔥 Error: {e}")
        send_telegram(f"⚠️ System Error: {str(e)}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    run_monk_mode()
