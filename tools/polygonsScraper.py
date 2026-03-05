import asyncio
import json
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "tzevaadom_scan"
os.makedirs(OUTPUT_DIR, exist_ok=True)

found_files = []

async def scan_tzevaadom():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        # ── האזנה לכל תגובת רשת ──
        async def handle_response(response):
            url = response.url
            try:
                if response.status != 200:
                    return

                # סינון לפי סוג תוכן
                content_type = response.headers.get("content-type", "")
                
                # דילוג על תמונות, פונטים, CSS
                skip_types = ["image/", "font/", "text/css", "video/", "audio/"]
                if any(s in content_type for s in skip_types):
                    return

                body = await response.body()
                size_kb = len(body) / 1024

                # מילות מפתח שמעידות על נתוני מפה
                geo_keywords = [
                    b"coordinates", b"polygon", b"geometry",
                    b"features", b"geojson", b"GeoJSON",
                    b"\u05d9\u05e9\u05d5\u05d1",  # ישוב
                    b"\u05e4\u05d5\u05dc\u05d9\u05d2\u05d5\u05df",  # פוליגון
                ]

                body_lower = body.lower()
                is_geo = any(kw.lower() in body_lower for kw in geo_keywords)
                is_json = "json" in content_type or url.endswith(".json")
                is_large = size_kb > 50  # קבצים גדולים תמיד שווה לשמור

                if is_geo or is_json or is_large:
                    # יצירת שם קובץ מה-URL
                    safe_name = url.replace("https://", "").replace("http://", "")
                    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in safe_name)
                    safe_name = safe_name[:150]  # הגבלת אורך שם קובץ

                    # ניסיון לפענח כ-JSON
                    decoded = None
                    try:
                        decoded = json.loads(body.decode("utf-8"))
                    except:
                        try:
                            decoded = body.decode("utf-8")
                        except:
                            decoded = f"[binary data - {size_kb:.1f}KB]"

                    # שמירה לקובץ
                    out_path = os.path.join(OUTPUT_DIR, f"{safe_name}.txt")
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(f"URL: {url}\n")
                        f.write(f"Content-Type: {content_type}\n")
                        f.write(f"Size: {size_kb:.1f} KB\n")
                        f.write(f"Is GEO: {is_geo}\n")
                        f.write("-" * 60 + "\n")
                        if isinstance(decoded, (dict, list)):
                            f.write(json.dumps(decoded, ensure_ascii=False, indent=2))
                        else:
                            f.write(str(decoded))

                    found_files.append({
                        "url": url,
                        "size_kb": round(size_kb, 1),
                        "is_geo": is_geo,
                        "content_type": content_type,
                        "saved_as": out_path
                    })

                    # הדפסה בזמן אמת
                    geo_tag = "🗺️  GEO" if is_geo else "📄"
                    print(f"{geo_tag} | {size_kb:7.1f}KB | {url[:80]}")

            except Exception as e:
                pass  # מדלגים על שגיאות בשקט

        page.on("response", handle_response)

        # ── שלב 1: טעינת דף הבית ──
        print("\n[1] טוען דף הבית...")
        await page.goto("https://www.tzevaadom.co.il/", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)

        # ── שלב 2: ניסיון לפתוח את המפה ──
        print("\n[2] מחפש כפתור מפה...")
        map_selectors = [
            "a[href*='map']", "button:has-text('מפה')",
            "a:has-text('מפה')", "[class*='map']",
            "nav a", ".menu a"
        ]
        for selector in map_selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    print(f"    נמצא: {selector}")
                    await el.click()
                    await asyncio.sleep(3)
                    break
            except:
                pass

        # ── שלב 3: ניווט ישיר לדפים אפשריים ──
        sub_pages = [
            "https://www.tzevaadom.co.il/map",
            "https://www.tzevaadom.co.il/maps",
            "https://www.tzevaadom.co.il/alerts",
            "https://www.tzevaadom.co.il/history",
            "https://www.tzevaadom.co.il/heb/",
        ]
        for url in sub_pages:
            print(f"\n[3] מנסה: {url}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=15000)
                await asyncio.sleep(3)
            except:
                print(f"    ❌ לא נגיש")

        # ── שלב 4: חיפוש קבצי JSON ישירות ──
        print("\n[4] מנסה נתיבי JSON ידועים...")
        json_paths = [
            "/data/cities.json",
            "/data/polygons.json",
            "/data/areas.json",
            "/data/alerts.json",
            "/data/zones.json",
            "/static/data/cities.json",
            "/static/polygons.json",
            "/api/cities",
            "/api/polygons",
            "/api/areas",
            "/api/zones",
            "/assets/data.json",
            "/assets/cities.json",
        ]
        for path in json_paths:
            try:
                resp = await page.request.get(f"https://www.tzevaadom.co.il{path}")
                if resp.status == 200:
                    body = await resp.body()
                    size_kb = len(body) / 1024
                    print(f"    ✅ נמצא! {path} ({size_kb:.1f}KB)")
                    out_path = os.path.join(OUTPUT_DIR, f"DIRECT_{path.replace('/', '_')}.json")
                    with open(out_path, "wb") as f:
                        f.write(body)
                else:
                    print(f"    ❌ {path} → {resp.status}")
            except Exception as e:
                print(f"    ⚠️  {path} → {e}")

        # ── שלב 5: המתנה ידנית לאינטראקציה ──
        print("\n[5] הדפדפן פתוח — תוכל לנווט ידנית.")
        print("    לחץ על אזורים במפה, פתח תפריטים, חפש ישובים.")
        print("    כל בקשת רשת תירשם אוטומטית.")
        print("    לחץ ENTER כשסיימת.\n")
        input(">>> לחץ ENTER לסיום הסריקה...")

        # ── סיכום ──
        await browser.close()

        print(f"\n{'='*60}")
        print(f"סה\"כ קבצים שנשמרו: {len(found_files)}")
        print(f"{'='*60}")

        # מיון לפי גודל
        found_files.sort(key=lambda x: x["size_kb"], reverse=True)

        # הדפסת קבצי GEO בלבד
        geo_files = [f for f in found_files if f["is_geo"]]
        print(f"\n🗺️  קבצי GEO שנמצאו ({len(geo_files)}):")
        for f in geo_files:
            print(f"  {f['size_kb']:8.1f}KB | {f['url']}")

        print(f"\n📄 כל הקבצים הגדולים (מעל 100KB):")
        for f in [x for x in found_files if x["size_kb"] > 100]:
            print(f"  {f['size_kb']:8.1f}KB | {f['url']}")

        # שמירת סיכום
        summary_path = os.path.join(OUTPUT_DIR, "_SUMMARY.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(found_files, f, ensure_ascii=False, indent=2)
        print(f"\nסיכום נשמר: {summary_path}")
        print(f"כל הקבצים נשמרו בתיקייה: {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(scan_tzevaadom())