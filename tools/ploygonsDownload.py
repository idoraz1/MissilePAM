import requests
import json

# הורדת הקבצים
polygons_url = "https://www.tzevaadom.co.il/static/polygons.json?v=5"
cities_url   = "https://www.tzevaadom.co.il/static/cities.json?v=10"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.tzevaadom.co.il/"
}

print("מוריד polygons.json...")
polygons_raw = requests.get(polygons_url, headers=headers).json()

print("מוריד cities.json...")
cities_raw = requests.get(cities_url, headers=headers).json()

# שמירה מקומית
with open("tz_polygons.json", "w", encoding="utf-8") as f:
    json.dump(polygons_raw, f, ensure_ascii=False, indent=2)

with open("tz_cities.json", "w", encoding="utf-8") as f:
    json.dump(cities_raw, f, ensure_ascii=False, indent=2)

# ── הצצה למבנה polygons.json ──
print("\n=== polygons.json ===")
print(f"סוג: {type(polygons_raw)}")
if isinstance(polygons_raw, list):
    print(f"מספר רשומות: {len(polygons_raw)}")
    print("דוגמה (רשומה ראשונה):")
    print(json.dumps(polygons_raw[0], ensure_ascii=False, indent=2))
elif isinstance(polygons_raw, dict):
    keys = list(polygons_raw.keys())
    print(f"מפתחות ראשיים: {keys[:5]}")
    first_key = keys[0]
    print(f"דוגמה ('{first_key}'):")
    print(json.dumps(polygons_raw[first_key], ensure_ascii=False, indent=2))

# ── הצצה למבנה cities.json ──
print("\n=== cities.json ===")
print(f"סוג: {type(cities_raw)}")
if isinstance(cities_raw, list):
    print(f"מספר רשומות: {len(cities_raw)}")
    print("דוגמה (רשומה ראשונה):")
    print(json.dumps(cities_raw[0], ensure_ascii=False, indent=2))
elif isinstance(cities_raw, dict):
    keys = list(cities_raw.keys())
    print(f"מפתחות ראשיים: {keys[:5]}")
    first_key = keys[0]
    print(f"דוגמה ('{first_key}'):")
    print(json.dumps(cities_raw[first_key], ensure_ascii=False, indent=2))

print("\nהקבצים נשמרו: tz_polygons.json, tz_cities.json")