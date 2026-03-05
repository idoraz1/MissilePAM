import requests
import json

CITIES_URL = "https://www.tzevaadom.co.il/static/cities.json?v=10"
POLYGONS_URL = "https://www.tzevaadom.co.il/static/polygons.json?v=5"
OUTPUT_FILE = "cities_polygons.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.tzevaadom.co.il/"
}

def download_json(url, name):
    print(f"[↓] מוריד {name}...")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    print(f"    ✅ הצלחה ({len(r.content) / 1024:.1f} KB)")
    return r.json()

def build_polygons():
    # ── הורדת הקבצים ──
    cities_raw = download_json(CITIES_URL, "cities.json")
    polygons_raw = download_json(POLYGONS_URL, "polygons.json")

    cities_data = cities_raw.get("cities", {})
    
    result = {}
    stats = {"with_polygon": 0, "without_polygon": 0, "skipped": 0}

    print("\n[⚙] מעבד נתונים...")

    for key, city in cities_data.items():
        
        # ── דילוג על אזורים (מפתחות שהם מספרים כמו "15", "16") ──
        # ישובים אמיתיים תמיד יש להם שם עברי כמפתח
        if key.isdigit():
            stats["skipped"] += 1
            continue

        # ── בדיקה שיש שדות חיוניים ──
        if "lat" not in city or "lng" not in city:
            stats["skipped"] += 1
            continue

        city_name = city.get("he", key)
        city_id = str(city.get("id", ""))

        # ── חיפוש פוליגון לפי ID ──
        polygon = polygons_raw.get(city_id, None)

        if polygon:
            stats["with_polygon"] += 1
        else:
            stats["without_polygon"] += 1

        # ── בניית הרשומה הסופית ──
        result[city_name] = {
            "lat": city["lat"],
            "lng": city["lng"],
            "polygon": polygon  # None אם לא נמצא
        }

    # ── שמירה לקובץ ──
    print(f"\n[💾] שומר ל-{OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # ── סטטיסטיקות ──
    print(f"\n{'='*45}")
    print(f"✅ ישובים עם פוליגון:    {stats['with_polygon']}")
    print(f"⚠️  ישובים ללא פוליגון:  {stats['without_polygon']}")
    print(f"🔕 דולגו (אזורים/חסרים): {stats['skipped']}")
    print(f"📦 סה\"כ רשומות בקובץ:   {len(result)}")
    print(f"{'='*45}")
    print(f"\n✅ הקובץ נשמר: {OUTPUT_FILE}")

    # ── הדפסת דוגמה ──
    sample_key = next(iter(result))
    sample = result[sample_key]
    print(f"\n📋 דוגמה ({sample_key}):")
    print(f"   lat: {sample['lat']}, lng: {sample['lng']}")
    if sample["polygon"]:
        print(f"   polygon: {len(sample['polygon'])} נקודות")
    else:
        print(f"   polygon: None")

if __name__ == "__main__":
    build_polygons()