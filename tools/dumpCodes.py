import requests
import json
import time
import os
from datetime import datetime

# כתובת ה-API של ההתרעות בזמן אמת
ALERTS_URL = "https://www.oref.org.il/WarningMessages/Alert/Alerts.json"

# כותרות כדי לא להיחסם
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "Cache-Control": "no-cache"
}

LOG_DIR = "json_logs"

def save_json_snapshot(data):
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(LOG_DIR, f"alert_dump_{timestamp}.json")
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"[V] נשמר לוג: {filename}")
    # הדפסה למסך כדי שתראה מה קורה
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("-" * 50)

def main():
    print(f"[*] מתחיל האזנה ושמירת לוגים לתיקייה '{LOG_DIR}'...")
    last_data_str = ""

    while True:
        try:
            # הוספת פרמטר אקראי למניעת Cache
            url = f"{ALERTS_URL}?_={int(time.time()*1000)}"
            response = requests.get(url, headers=HEADERS, timeout=5)
            response.encoding = 'utf-8'

            # לפעמים השרת מחזיר מחרוזת ריקה או עם BOM
            content = response.text.strip().replace('\ufeff', '')
            
            if not content:
                # אם אין כלום והיה לנו מידע קודם - נרשום שהתרוקן
                if last_data_str != "EMPTY":
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] אין התרעות כרגע (הקובץ ריק).")
                    last_data_str = "EMPTY"
                time.sleep(2)
                continue

            # המרה ל-JSON
            current_data = json.loads(content)
            current_data_str = json.dumps(current_data, sort_keys=True)

            # אם המידע השתנה ממה שראינו בפעם הקודמת -> שמור קובץ!
            if current_data_str != last_data_str:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] >> זוהה שינוי בנתונים!")
                save_json_snapshot(current_data)
                last_data_str = current_data_str

        except json.JSONDecodeError:
            pass # קורה כשהקובץ ריק או לא תקין
        except Exception as e:
            print(f"[!] שגיאה: {e}")
        
        time.sleep(2)

if __name__ == "__main__":
    main()