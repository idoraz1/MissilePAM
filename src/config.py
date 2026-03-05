import os
import json

local_ip = "YOUR_LOCAL_IP"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
CITIES_FILE = os.path.join(DATA_DIR, "cities.json")
CITIES_POLYGONS_FILE = os.path.join(DATA_DIR, "cities_polygons.json")

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
