import threading

# ─── קודי פיקוד העורף ───
ALERT_TYPE_EMERGENCY = "EMERGENCY"
ALERT_TYPE_UAV       = "UAV"
ALERT_TYPE_EARLY     = "EARLY_WARNING"
ALERT_TYPE_PENDING   = "PENDING"

# ─── מילון פוליגונים פעילים ───
active_polygons: dict = {}
active_polygons_lock  = threading.Lock()

YELLOW_TIMEOUT_SECONDS = 60

cities_from_file = {}
cities_polygons = {}

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

last_my_area_alert_time = 0
last_my_area_cat        = 1
last_printed_live       = ""
