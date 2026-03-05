import json
import math
import time
import re
import src.state as state
import src.config as config

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


def load_cities_from_file():
    try:
        with open(config.CITIES_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        areas = raw_data.get("areas", {})
        count = 0
        for district_name, district_cities in areas.items():
            if isinstance(district_cities, dict):
                for city_name, city_data in district_cities.items():
                    if isinstance(city_data, dict) and "lat" in city_data and "long" in city_data:
                        state.cities_from_file[city_name] = {
                            "lat": city_data["lat"],
                            "lng": city_data["long"]
                        }
                        count += 1
        print(f"[Cities] נטענו {count} ישובים מקובץ cities.json")
    except FileNotFoundError:
        print("[Cities] קובץ cities.json לא נמצא!")
    except Exception as e:
        print(f"[Cities] שגיאה בטעינת cities.json: {e}")


def load_cities_polygons():
    """טוען את קובץ הפוליגונים המלא"""
    try:
        with open(config.CITIES_POLYGONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for city_name, city_data in data.items():
            if isinstance(city_data, dict) and "polygon" in city_data:
                state.cities_polygons[city_name] = {
                    "polygon": city_data["polygon"],
                    "lat": city_data.get("lat"),
                    "lng": city_data.get("lng")
                }
                count += 1
        print(f"[Polygons] נטענו {count} פוליגונים מקובץ cities_polygons.json")
    except FileNotFoundError:
        print("[Polygons] קובץ cities_polygons.json לא נמצא! נשתמש בעיגולים בלבד.")
    except Exception as e:
        print(f"[Polygons] שגיאה בטעינת cities_polygons.json: {e}")


def get_polygon_type_from_cat(cat: str, title: str) -> str:
    if cat == "1":
        return state.ALERT_TYPE_EMERGENCY
    elif cat == "6":
        return state.ALERT_TYPE_UAV
    elif cat == "10":
        if "הסתיים" in title:
            return state.ALERT_TYPE_PENDING
        else:
            return state.ALERT_TYPE_EARLY
    return state.ALERT_TYPE_EMERGENCY


def match_city_name(city_name: str) -> str:
    """
    מחפש התאמה לשם עיר עם לוגיקה משופרת:
    1. Exact Match - התאמה מלאה
    2. Partial Match עם גבולות מילה (רווח, מקף, סוף מחרוזת)
    """
    if city_name in state.cities_polygons:
        return city_name
    if city_name in state.cities_from_file:
        return city_name
    for key in CITIES_COORDS:
        if key == city_name:
            return key

    for key in state.cities_polygons:
        pattern = r'^' + re.escape(city_name) + r'($|[\s\-])'
        if re.match(pattern, key):
            return key
        pattern = r'^' + re.escape(key) + r'($|[\s\-])'
        if re.match(pattern, city_name):
            return key

    for key in state.cities_polygons:
        if city_name in key or key in city_name:
            return key

    return None


def get_coords_for_city(city_name: str):
    """מחזיר קואורדינטות + פוליגון אם קיים"""
    matched_name = match_city_name(city_name)
    if not matched_name:
        return None

    if matched_name in state.cities_polygons:
        return state.cities_polygons[matched_name]

    if matched_name in state.cities_from_file:
        return state.cities_from_file[matched_name]

    if matched_name in CITIES_COORDS:
        return CITIES_COORDS[matched_name]

    return None


def upsert_polygons(cities: list, polygon_type: str):
    now = time.time()
    with state.active_polygons_lock:
        for city in cities:
            coords = get_coords_for_city(city)
            if city in state.active_polygons:
                state.active_polygons[city]["last_updated"]  = now
                state.active_polygons[city]["polygon_type"]  = polygon_type
            else:
                state.active_polygons[city] = {
                    "name":         city,
                    "lat":          coords["lat"] if coords else None,
                    "lng":          coords["lng"] if coords else None,
                    "polygon":      coords.get("polygon") if coords and isinstance(coords, dict) else None,
                    "polygon_type": polygon_type,
                    "last_updated": now
                }


def end_event_for_cities(cities: list):
    with state.active_polygons_lock:
        for city in cities:
            if city in state.active_polygons:
                del state.active_polygons[city]
                print(f"[Polygon] הוסר: {city}")


def apply_early_warning(cities: list):
    now = time.time()
    with state.active_polygons_lock:
        for city in cities:
            if city not in state.active_polygons:
                coords = get_coords_for_city(city)
                state.active_polygons[city] = {
                    "name":         city,
                    "lat":          coords["lat"] if coords else None,
                    "lng":          coords["lng"] if coords else None,
                    "polygon":      coords.get("polygon") if coords and isinstance(coords, dict) else None,
                    "polygon_type": state.ALERT_TYPE_EARLY,
                    "last_updated": now
                }


def polygon_timeout_loop():
    while True:
        now = time.time()
        with state.active_polygons_lock:
            for city, data in state.active_polygons.items():
                ptype = data["polygon_type"]
                age   = now - data["last_updated"]
                if ptype in (state.ALERT_TYPE_EMERGENCY, state.ALERT_TYPE_UAV):
                    if age >= state.YELLOW_TIMEOUT_SECONDS:
                        state.active_polygons[city]["polygon_type"] = state.ALERT_TYPE_PENDING
                        print(f"[Timeout] {city}: אדום/כתום → צהוב (לאחר {int(age)}s)")
        time.sleep(1)


def build_all_alerts_list() -> list:
    with state.active_polygons_lock:
        return list(state.active_polygons.values())


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
