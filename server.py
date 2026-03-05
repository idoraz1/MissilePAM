import asyncio
from playwright.async_api import async_playwright
from flask import Flask, send_from_directory, jsonify, request, send_file
from flask_cors import CORS
import threading
from datetime import datetime
import pychromecast
from gtts import gTTS
import os
import time
import logging
import json
import math
import zipfile
import io

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)

local_ip = "YOUR_LOCAL_IP"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CITIES_FILE = os.path.join(BASE_DIR, "cities.json")

# ─── קודי פיקוד העורף (מבוסס JSON אמיתי) ───
# cat=1  : ירי רקטות וטילים          → EMERGENCY (אדום)
# cat=6  : חדירת כלי טיס עוין        → UAV       (כתום)
# cat=10 : שני מצבים לפי title:
#          "הסתיים"   → PENDING       (צהוב - סיום)
#          אחרת       → EARLY_WARNING (סגול - התרעה מקדימה)

ALERT_TYPE_EMERGENCY = "EMERGENCY"
ALERT_TYPE_UAV       = "UAV"
ALERT_TYPE_EARLY     = "EARLY_WARNING"
ALERT_TYPE_PENDING   = "PENDING"

# ─── מילון פוליגונים פעילים ───
# מבנה: { "שם_עיר": { "polygon_type": ..., "last_updated": float, "lat": ..., "lng": ... } }
active_polygons: dict = {}
active_polygons_lock  = threading.Lock()

# כמה שניות לפני שאזעקה פעילה הופכת לצהובה
YELLOW_TIMEOUT_SECONDS = 60

CITIES_COORDS = {
    "ירושלים": {"lat": 31.7683, "lng": 35.2137},
    "תל אביב": {"lat": 32.0853, "lng": 34.7818},
    "חיפה": {"lat": 32.7940, "lng": 34.9896},
    "ראשון לציון": {"lat": 31.9730, "lng": 34.7925},
    "פתח תקווה": {"lat": 32.0840, "lng": 34.8878},
    "אשדוד": {"lat": 31.8014, "lng": 34.6435},
    "נתניה": {"lat": 32.3215, "lng": 34.8532},
    "באר שבע": {"lat": 31.2518, "lng": 34.7913},
    "בני ברק": {"lat": 32.0849, "lng": 34.8352},
    "חולון": {"lat": 32.0158, "lng": 34.7874},
    "רמת גן": {"lat": 32.0823, "lng": 34.8107},
    "אשקלון": {"lat": 31.6693, "lng": 34.5715},
    "רחובות": {"lat": 31.8944, "lng": 34.8113},
    "בת ים": {"lat": 32.0132, "lng": 34.7480},
    "בית שמש": {"lat": 31.7470, "lng": 34.9881},
    "כפר סבא": {"lat": 32.1713, "lng": 34.9080},
    "הרצליה": {"lat": 32.1624, "lng": 34.8447},
    "חדרה": {"lat": 32.4340, "lng": 34.9197},
    "מודיעין": {"lat": 31.8998, "lng": 35.0075},
    "לוד": {"lat": 31.9510, "lng": 34.8881},
    "רמלה": {"lat": 31.9272, "lng": 34.8710},
    "רעננה": {"lat": 32.1848, "lng": 34.8713},
    "מודיעין עילית": {"lat": 31.9333, "lng": 35.0415},
    "הוד השרון": {"lat": 32.1500, "lng": 34.8911},
    "קריית גת": {"lat": 31.6033, "lng": 34.7645},
    "קריית אתא": {"lat": 32.8052, "lng": 35.1054},
    "קריית מוצקין": {"lat": 32.8333, "lng": 35.0667},
    "קריית ביאליק": {"lat": 32.8333, "lng": 35.0833},
    "קריית ים": {"lat": 32.8333, "lng": 35.0667},
    "נהריה": {"lat": 33.0081, "lng": 34.9256},
    "עכו": {"lat": 32.9331, "lng": 35.0827},
    "כרמיאל": {"lat": 32.9149, "lng": 34.9254},
    "צפת": {"lat": 33.3293, "lng": 35.4965},
    "קריית שמונה": {"lat": 33.2073, "lng": 35.5695},
    "מטולה": {"lat": 33.2801, "lng": 35.5794},
    "אילת": {"lat": 29.5577, "lng": 34.9519},
    "שדרות": {"lat": 31.5256, "lng": 34.5943},
    "נתיבות": {"lat": 31.4172, "lng": 34.5878},
    "אופקים": {"lat": 31.3129, "lng": 34.6206},
    "אריאל": {"lat": 32.1046, "lng": 35.1745},
    "קצרין": {"lat": 32.9918, "lng": 35.6946},
    "מעלה אדומים": {"lat": 31.7820, "lng": 35.3032},
    "ביתר עילית": {"lat": 31.7000, "lng": 35.1167},
    "טבריה": {"lat": 32.7897, "lng": 35.5249},
    "עפולה": {"lat": 32.6105, "lng": 35.2869},
    "אור עקיבא": {"lat": 32.5000, "lng": 34.9167},
    "ראש פינה": {"lat": 32.9667, "lng": 35.5333},
    "יבנה": {"lat": 31.8753, "lng": 34.7397},
    "נס ציונה": {"lat": 31.9274, "lng": 34.7979},
    "מבשרת ציון": {"lat": 31.8000, "lng": 35.1500},
    "גבעת זאב": {"lat": 31.8500, "lng": 35.1667},
    "תקוע": {"lat": 31.6000, "lng": 35.2167},
    "שילת": {"lat": 31.9167, "lng": 35.0167},
    "באר יעקב": {"lat": 31.9333, "lng": 34.8333},
    "יהוד": {"lat": 31.8833, "lng": 34.8833},
    "שלומי": {"lat": 33.0760, "lng": 35.1432},
    "זרעית": {"lat": 33.0805, "lng": 35.2678},
    "חצור הגלילית": {"lat": 32.9818, "lng": 35.5539},
    "גוש עציון": {"lat": 31.6500, "lng": 35.1333},
    "שומרון": {"lat": 32.2000, "lng": 35.2500},
    "עוטף עזה": {"lat": 31.4287, "lng": 34.4697},
    "גולן": {"lat": 33.0000, "lng": 35.7500}
}

cities_from_file = {}

def load_cities_from_file():
    global cities_from_file
    try:
        with open(CITIES_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        areas = raw_data.get("areas", {})
        count = 0
        for district_name, district_cities in areas.items():
            if isinstance(district_cities, dict):
                for city_name, city_data in district_cities.items():
                    if isinstance(city_data, dict) and "lat" in city_data and "long" in city_data:
                        cities_from_file[city_name] = {
                            "lat": city_data["lat"],
                            "lng": city_data["long"]
                        }
                        count += 1
        print(f"[Cities] נטענו {count} ישובים מקובץ cities.json")
    except FileNotFoundError:
        print("[Cities] קובץ cities.json לא נמצא!")
    except Exception as e:
        print(f"[Cities] שגיאה בטעינת cities.json: {e}")


current_status = {
    "status": "0",
    "active_area": "",
    "alert_type": "",
    "timestamp": 0,
    "is_test_mode": False,
    "all_alerts": [],
    "close_threat": False
}

esp_command = {"command": "idle", "file": 0, "volume": 25}

cast_devices    = {}
cast_browser    = None
previous_volumes = {}

last_my_area_alert_time = 0   # הפעם האחרונה שהייתה אזעקה באזור שלי
last_my_area_cat        = 1   # קטגוריה אחרונה של האזעקה אצלי
last_printed_live       = ""


# ════════════════════════════════════════════════════════════
#  לוגיקת פוליגונים
# ════════════════════════════════════════════════════════════

def get_polygon_type_from_cat(cat: str, title: str) -> str:
    """מחזיר את סוג הפוליגון לפי cat ו-title מה-JSON האמיתי."""
    if cat == "1":
        return ALERT_TYPE_EMERGENCY
    elif cat == "6":
        return ALERT_TYPE_UAV
    elif cat == "10":
        if "הסתיים" in title:
            return ALERT_TYPE_PENDING   # סיום אירוע
        else:
            return ALERT_TYPE_EARLY     # התרעה מקדימה
    return ALERT_TYPE_EMERGENCY         # ברירת מחדל


def upsert_polygons(cities: list, polygon_type: str):
    """מוסיף עיר חדשה או מרענן עיר קיימת (אפס טיימר → חזרה לאדום/כתום)."""
    now = time.time()
    with active_polygons_lock:
        for city in cities:
            coords = get_coords_for_city(city)
            if city in active_polygons:
                # עיר קיימת - רענן זמן ועדכן צבע (אפשר לחזור מצהוב לאדום)
                active_polygons[city]["last_updated"]  = now
                active_polygons[city]["polygon_type"]  = polygon_type
            else:
                # עיר חדשה
                active_polygons[city] = {
                    "name":         city,
                    "lat":          coords["lat"] if coords else None,
                    "lng":          coords["lng"] if coords else None,
                    "polygon_type": polygon_type,
                    "last_updated": now
                }


def end_event_for_cities(cities: list):
    """קוד 10 + 'הסתיים': מוחק את הערים שסיימו מהרשימה הפעילה."""
    with active_polygons_lock:
        for city in cities:
            if city in active_polygons:
                del active_polygons[city]
                print(f"[Polygon] הוסר: {city}")


def apply_early_warning(cities: list):
    """קוד 10 ללא 'הסתיים': מוסיף פוליגון סגול (לא דורס אדום/כתום קיים)."""
    now = time.time()
    with active_polygons_lock:
        for city in cities:
            if city not in active_polygons:
                # רק אם אין כבר אזעקה פעילה לאותה עיר
                coords = get_coords_for_city(city)
                active_polygons[city] = {
                    "name":         city,
                    "lat":          coords["lat"] if coords else None,
                    "lng":          coords["lng"] if coords else None,
                    "polygon_type": ALERT_TYPE_EARLY,
                    "last_updated": now
                }


def polygon_timeout_loop():
    """
    לולאה ברקע שרצה כל שנייה.
    אם עברה YELLOW_TIMEOUT_SECONDS מאז last_updated של פוליגון אדום/כתום
    → הופכת אותו לצהוב (PENDING).
    פוליגון צהוב/סגול לא נמחק אוטומטית - רק קוד 10+"הסתיים" ימחק אותו.
    """
    while True:
        now = time.time()
        with active_polygons_lock:
            for city, data in active_polygons.items():
                ptype = data["polygon_type"]
                age   = now - data["last_updated"]
                if ptype in (ALERT_TYPE_EMERGENCY, ALERT_TYPE_UAV):
                    if age >= YELLOW_TIMEOUT_SECONDS:
                        active_polygons[city]["polygon_type"] = ALERT_TYPE_PENDING
                        print(f"[Timeout] {city}: אדום/כתום → צהוב (לאחר {int(age)}s)")
        time.sleep(1)


def build_all_alerts_list() -> list:
    """בונה את הרשימה שנשלחת ל-frontend מתוך active_polygons."""
    with active_polygons_lock:
        return list(active_polygons.values())


# ════════════════════════════════════════════════════════════
#  עזר כללי
# ════════════════════════════════════════════════════════════

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "areas": ["קריית אתא"],
            "speakers": [],
            "play_startup_sound": False,
            "volumes": {"immediate": 1.0, "uav": 1.0, "early": 0.8, "all_clear": 0.5},
            "texts": {
                "alert_immediate": "אזעקה, ירי טילים ורקטות באזור {area}. נא להיכנס מיד למרחב המוגן.",
                "alert_uav": "חדירת כלי טיס עוין באזור {area}. נא להיכנס מיד למרחב המוגן.",
                "alert_early": "התרעה מקדימה באזור {area}. זמן התרעה מורחב.",
                "all_clear": "חזרה לשגרה",
                "startup": "מחובר"
            },
            "toggles": {
                "enable_immediate": True,
                "enable_uav": True,
                "enable_early": True,
                "enable_all_clear": True
            },
            "proximity_radius_km": 10,
            "esp32": {
                "volume_alert": 30, "volume_uav": 30, "volume_early": 25,
                "volume_all_clear": 20, "volume_startup": 20,
                "file_alert_immediate": 1, "file_all_clear": 2,
                "file_startup": 3, "file_uav": 4, "file_alert_early": 5
            }
        }


def save_config(config_data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)


def get_coords_for_city(city_name):
    for key, coords in CITIES_COORDS.items():
        if key in city_name:
            return coords
    if city_name in cities_from_file:
        return cities_from_file[city_name]
    for key, coords in cities_from_file.items():
        if key in city_name or city_name in key:
            return coords
    return None


def haversine_distance(lat1, lng1, lat2, lng2):
    R     = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a     = (math.sin(d_lat / 2) ** 2
             + math.cos(math.radians(lat1))
             * math.cos(math.radians(lat2))
             * math.sin(d_lng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def check_close_threat(alert_cities, my_areas, radius_km):
    for area in my_areas:
        area_coords = get_coords_for_city(area)
        if not area_coords:
            continue
        for city in alert_cities:
            city_coords = get_coords_for_city(city)
            if not city_coords:
                continue
            dist = haversine_distance(
                area_coords["lat"], area_coords["lng"],
                city_coords["lat"], city_coords["lng"]
            )
            if 0 < dist <= radius_km:
                return True
    return False


# ════════════════════════════════════════════════════════════
#  שמע ו-Google Home
# ════════════════════════════════════════════════════════════

def generate_audio_files(config, trigger_area=""):
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)
    texts       = config.get("texts", {})
    area_to_say = trigger_area if trigger_area else (config["areas"][0] if config.get("areas") else "")
    try:
        gTTS(texts.get("alert_immediate", "אזעקה").replace("{area}", area_to_say), lang='iw').save(
            os.path.join(AUDIO_DIR, "alert_immediate.mp3"))
        gTTS(texts.get("alert_uav", "כטב\"ם").replace("{area}", area_to_say), lang='iw').save(
            os.path.join(AUDIO_DIR, "alert_uav.mp3"))
        gTTS(texts.get("alert_early", "התרעה מקדימה").replace("{area}", area_to_say), lang='iw').save(
            os.path.join(AUDIO_DIR, "alert_early.mp3"))
        gTTS(texts.get("all_clear", "חזרה לשגרה"), lang='iw').save(
            os.path.join(AUDIO_DIR, "routine.mp3"))
        gTTS(texts.get("startup", "מחובר"), lang='iw').save(
            os.path.join(AUDIO_DIR, "connected.mp3"))
        gTTS(texts.get("alert_immediate", "אזעקה").replace("{area}", area_to_say), lang='iw').save(
            os.path.join(AUDIO_DIR, "alert.mp3"))
        print("[Audio] כל קבצי MP3 נוצרו בהצלחה.")
        return True
    except Exception as e:
        print(f"[Audio Error] {e}")
        return False


def discover_chromecasts():
    chromecasts, browser = pychromecast.get_chromecasts()
    names = [cc.name for cc in chromecasts]
    pychromecast.discovery.stop_discovery(browser)
    return names


def setup_active_chromecasts(config):
    global cast_devices, cast_browser
    speakers_to_find = config.get("speakers", [])
    if not speakers_to_find:
        print("[Google Home] אין רמקולים מוגדרים.")
        return
    cast_devices = {}
    chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=speakers_to_find)
    cast_browser = browser
    for cc in chromecasts:
        cc.wait()
        cast_devices[cc.name] = cc
        print(f"[Google Home] מחובר: {cc.name}")
    if config.get("play_startup_sound", False):
        for name in cast_devices:
            play_audio_thread("connected.mp3", name)


def play_audio(filename, target_speaker_name=None, override_volume=None):
    speakers = (
        [cast_devices[target_speaker_name]]
        if target_speaker_name and target_speaker_name in cast_devices
        else cast_devices.values()
    )
    url = f"http://{local_ip}:5000/audio/{filename}"
    for device in speakers:
        try:
            if override_volume is not None:
                device.set_volume(override_volume)
            mc = device.media_controller
            mc.play_media(url, 'audio/mp3')
            mc.block_until_active()
        except Exception:
            pass


def play_audio_thread(filename, target_speaker_name=None, override_volume=None):
    threading.Thread(target=play_audio,
                     args=(filename, target_speaker_name, override_volume),
                     daemon=True).start()


def trigger_google_home(status_code, cat="1"):
    global previous_volumes
    config  = load_config()
    volumes = config.get("volumes", {})
    toggles = config.get("toggles", {})
    try:
        if status_code == "alert":
            if cat == "6":
                if not toggles.get("enable_uav", True): return
                play_audio_thread("alert_uav.mp3", override_volume=volumes.get("uav", 1.0))
            elif cat == "10":
                if not toggles.get("enable_early", True): return
                play_audio_thread("alert_early.mp3", override_volume=volumes.get("early", 0.8))
            else:
                if not toggles.get("enable_immediate", True): return
                for name, device in cast_devices.items():
                    if device.status and device.status.volume_level is not None:
                        previous_volumes[name] = device.status.volume_level
                play_audio_thread("alert_immediate.mp3", override_volume=volumes.get("immediate", 1.0))

        elif status_code == "all_clear":
            if not toggles.get("enable_all_clear", True): return
            vol = volumes.get("all_clear", 0.5)
            for name, device in cast_devices.items():
                restore_vol = max(previous_volumes.get(name, 0.5), vol)
                try: device.set_volume(restore_vol)
                except: pass
            play_audio_thread("routine.mp3")
    except Exception as e:
        print(f"[Google Home] שגיאה: {e}")


def trigger_google_home_thread(status_code, cat="1"):
    threading.Thread(target=trigger_google_home,
                     args=(status_code, cat),
                     daemon=True).start()


# ════════════════════════════════════════════════════════════
#  Flask Routes
# ════════════════════════════════════════════════════════════

@app.route('/')
def serve_dashboard():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'GET':
        return jsonify(load_config())
    new_config = request.json
    save_config(new_config)
    generate_audio_files(new_config)
    threading.Thread(target=lambda: setup_active_chromecasts(new_config), daemon=True).start()
    return jsonify({"success": True, "message": "הגדרות נשמרו"})

@app.route('/api/status')
def status_api():
    s = dict(current_status)
    s["all_alerts"] = build_all_alerts_list()
    return jsonify(s)

@app.route('/api/devices')
def get_devices():
    return jsonify({"devices": discover_chromecasts()})

@app.route('/api/test', methods=['POST'])
def test_audio():
    data     = request.json
    filename = ("alert_immediate.mp3" if data.get("type") == "alert"
                else f"{data.get('type', 'connected')}.mp3")
    play_audio_thread(filename, target_speaker_name=data.get("speaker"))
    return jsonify({"success": True})

@app.route('/api/test_esp', methods=['POST'])
def test_esp_hardware():
    def run_esp_test():
        current_status["status"]       = "1"
        current_status["active_area"]  = "בדיקת מערכת (ESP32)"
        current_status["alert_type"]   = "בדיקה יזומה"
        current_status["is_test_mode"] = True
        time.sleep(5)
        current_status["status"]       = "0"
        current_status["active_area"]  = ""
        current_status["alert_type"]   = ""
        current_status["is_test_mode"] = False
    threading.Thread(target=run_esp_test, daemon=True).start()
    return jsonify({"success": True})

@app.route('/api/clear_alerts', methods=['POST'])
def clear_alerts():
    global last_my_area_alert_time, last_my_area_cat, last_printed_live
    with active_polygons_lock:
        active_polygons.clear()
    current_status["status"]       = "0"
    current_status["active_area"]  = ""
    current_status["alert_type"]   = ""
    current_status["close_threat"] = False
    last_my_area_alert_time        = 0
    last_my_area_cat               = 1
    last_printed_live              = ""
    print("[Manual] המפה נוקתה ידנית.")
    return jsonify({"success": True, "message": "המפה נוקתה"})

@app.route('/api/esp_command')
def esp_command_api():
    global esp_command
    cmd = dict(esp_command)
    esp_command = {"command": "idle", "file": 0, "volume": 25}
    return jsonify(cmd)

@app.route('/api/esp_play', methods=['POST'])
def esp_play():
    global esp_command
    data        = request.json
    file_num    = int(data.get("file", 1))
    volume      = int(data.get("volume", 25))
    esp_command = {"command": "play", "file": file_num, "volume": volume}
    return jsonify({"success": True, "queued_file": file_num})

@app.route('/api/esp_sd_zip')
def esp_sd_zip():
    config      = load_config()
    esp_cfg     = config.get("esp32", {})
    zip_buffer  = io.BytesIO()
    file_mapping = {
        esp_cfg.get("file_alert_immediate", 1): "alert_immediate.mp3",
        esp_cfg.get("file_all_clear",        2): "routine.mp3",
        esp_cfg.get("file_startup",           3): "connected.mp3",
        esp_cfg.get("file_uav",               4): "alert_uav.mp3",
        esp_cfg.get("file_alert_early",       5): "alert_early.mp3",
    }
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for sd_num, src_filename in file_mapping.items():
            src_path = os.path.join(AUDIO_DIR, src_filename)
            if os.path.exists(src_path):
                zf.write(src_path, f"MP3/{sd_num:04d}.mp3")
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip',
                     as_attachment=True, download_name='SD_Card_Files.zip')

@app.route('/api/esp_sd_status')
def esp_sd_status():
    config  = load_config()
    esp_cfg = config.get("esp32", {})
    file_mapping = {
        esp_cfg.get("file_alert_immediate", 1): ("alert_immediate.mp3", "אזעקה מידית"),
        esp_cfg.get("file_all_clear",        2): ("routine.mp3",         "חזרה לשגרה"),
        esp_cfg.get("file_startup",           3): ("connected.mp3",       "מערכת מחוברת"),
        esp_cfg.get("file_uav",               4): ("alert_uav.mp3",       'כטב"ם עוין'),
        esp_cfg.get("file_alert_early",       5): ("alert_early.mp3",     "התרעה מוקדמת"),
    }
    result = []
    for sd_num, (filename, label) in file_mapping.items():
        path   = os.path.join(AUDIO_DIR, filename)
        exists = os.path.exists(path)
        result.append({
            "sd_file":  f"{sd_num:04d}.mp3",
            "label":    label,
            "filename": filename,
            "exists":   exists,
            "size_kb":  round(os.path.getsize(path) / 1024, 1) if exists else 0,
            "updated":  datetime.fromtimestamp(os.path.getmtime(path)).strftime("%H:%M %d/%m/%Y") if exists else "-"
        })
    return jsonify(result)


def run_flask():
    app.run(host='0.0.0.0', port=5000, use_reloader=False)


# ════════════════════════════════════════════════════════════
#  Playwright — האזנה ל-Oref
# ════════════════════════════════════════════════════════════

async def run_playwright():
    global current_status, last_my_area_alert_time, last_my_area_cat, last_printed_live

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = await context.new_page()

        async def handle_response(response):
            global current_status, last_my_area_alert_time, last_my_area_cat, last_printed_live

            if current_status.get("is_test_mode", False):
                return

            if "Alerts.json" not in response.url:
                return

            try:
                if response.status != 200:
                    return

                raw  = await response.text()
                raw  = raw.strip().replace('\ufeff', '')
                if not raw:
                    return

                data = json.loads(raw)
                if not isinstance(data, dict):
                    return

                cities = data.get("data", [])
                if not cities:
                    return  # קובץ ריק = אין אזעקות

                if isinstance(cities, str):
                    cities = [cities]

                cat   = str(data.get("cat", "1"))
                title = data.get("title", "")

                config    = load_config()
                my_areas  = config.get("areas", [])
                radius_km = config.get("proximity_radius_km", 10)

                # ── טיפול לפי סוג הודעה ──
                is_end_event    = (cat == "10" and "הסתיים" in title)
                is_early_warning = (cat == "10" and "הסתיים" not in title)
                is_active_alert  = cat in ("1", "6")

                if is_end_event:
                    # מחיקת ערים שסיימו
                    end_event_for_cities(cities)

                elif is_early_warning:
                    # סגול - לא דורס אדום/כתום קיים
                    apply_early_warning(cities)

                elif is_active_alert:
                    # אדום / כתום + אפס טיימר לערים קיימות
                    polygon_type = get_polygon_type_from_cat(cat, title)
                    upsert_polygons(cities, polygon_type)

                    # ── בדיקה אם האזעקה באזור שלי ──
                    matched_area = next(
                        (area for area in my_areas
                         if any(area in city for city in cities)), None
                    )

                    if not matched_area:
                        # בדיקת קרבה גיאוגרפית
                        if check_close_threat(cities, my_areas, radius_km):
                            current_status["close_threat"] = True

                    if matched_area:
                        current_status["close_threat"] = False
                        current_status["active_area"]  = matched_area
                        current_status["alert_type"]   = title
                        current_status["timestamp"]    = int(time.time() * 1000)

                        # כריזה רק אם זו אזעקה חדשה (לא רענון של אותה אחת)
                        if time.time() - last_my_area_alert_time > 15:
                            generate_audio_files(config, matched_area)
                            trigger_google_home_thread("alert", cat)

                        last_my_area_alert_time = time.time()
                        last_my_area_cat        = cat

                # לוג קצר
                log_msg = f"[Live] cat={cat} | {title} | {len(cities)} ישובים"
                if log_msg != last_printed_live:
                    print(log_msg)
                    last_printed_live = log_msg

            except Exception as e:
                print(f"[Playwright Error] {e}")

        page.on("response", handle_response)

        config = load_config()
        print(f"[Playwright] מאזין להתרעות. אזורים: {config.get('areas', [])}")
        await page.goto("https://www.oref.org.il/heb/alerts-history/")

        # ── לולאה ראשית: עדכון current_status כל שנייה ──
        while True:
            now = time.time()

            if not current_status.get("is_test_mode", False):
                alerts = build_all_alerts_list()
                current_status["all_alerts"] = alerts

                # האם יש אזעקה פעילה (אדום/כתום) באזור שלי?
                my_alert_active = now - last_my_area_alert_time < YELLOW_TIMEOUT_SECONDS

                if my_alert_active:
                    if current_status["status"] != "1":
                        current_status["status"] = "1"
                        print("\n>>> סטטוס: 1 (אזעקה אצלי) <<<\n")
                else:
                    # בדוק אם האזור שלי עדיין צהוב (PENDING) במפה
                    config   = load_config()
                    my_areas = config.get("areas", [])
                    with active_polygons_lock:
                        my_area_pending = any(
                            active_polygons.get(city, {}).get("polygon_type") == ALERT_TYPE_PENDING
                            for area in my_areas
                            for city in active_polygons
                            if area in city
                        )
                    if my_area_pending:
                        if current_status["status"] != "2":
                            current_status["status"] = "2"
                            print("\n>>> סטטוס: 2 (ממתין לסיום) <<<\n")
                            trigger_google_home_thread("all_clear")
                    else:
                        if current_status["status"] != "0":
                            current_status["status"]       = "0"
                            current_status["active_area"]  = ""
                            current_status["alert_type"]   = ""
                            current_status["close_threat"] = False
                            print("\n>>> סטטוס: 0 (שגרה) <<<\n")

            await asyncio.sleep(1)


# ════════════════════════════════════════════════════════════
#  נקודת כניסה
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    load_cities_from_file()
    init_config = load_config()
    generate_audio_files(init_config)

    # הפעלת לולאת טיימר פוליגונים בthread נפרד
    threading.Thread(target=polygon_timeout_loop, daemon=True).start()

    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    setup_active_chromecasts(init_config)
    asyncio.run(run_playwright())
