import asyncio
import time
import json
from playwright.async_api import async_playwright
import src.state as state
import src.config as config
import src.utils as utils
import src.broadcaster as broadcaster

async def run_playwright():
    async with async_playwright() as p:
        headless_mode = config.PUBLIC_MODE or getattr(config, 'HEADLESS_MODE', True)
        browser = await p.chromium.launch(headless=headless_mode)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = await context.new_page()

        async def handle_response(response):
            if state.current_status.get("is_test_mode", False):
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
                    return

                if isinstance(cities, str):
                    cities = [cities]

                cat   = str(data.get("cat", "1"))
                title = data.get("title", "")

                conf      = config.load_config()
                my_areas  = conf.get("areas", [])
                radius_km = conf.get("proximity_radius_km", 10)

                is_end_event    = (cat == "10" and "הסתיים" in title)
                is_early_warning = (cat == "10" and "הסתיים" not in title)
                is_active_alert  = cat in ("1", "6")

                if is_end_event:
                    utils.end_event_for_cities(cities)

                elif is_early_warning:
                    utils.apply_early_warning(cities)
                    
                    matched_area = next(
                        (area for area in my_areas
                         if any(area in city for city in cities)), None
                    )
                    if matched_area:
                        state.current_status["active_area"]  = matched_area
                        state.current_status["alert_type"]   = title
                        state.current_status["timestamp"]    = int(time.time() * 1000)

                        if time.time() - state.last_my_area_alert_time > 15:
                            broadcaster.generate_audio_files(conf, matched_area)
                            broadcaster.trigger_google_home_thread("alert_early", cat)

                        state.last_my_area_alert_time = time.time()
                        state.last_my_area_cat        = cat

                elif is_active_alert:
                    polygon_type = utils.get_polygon_type_from_cat(cat, title)
                    utils.upsert_polygons(cities, polygon_type)

                    matched_area = next(
                        (area for area in my_areas
                         if any(area in city for city in cities)), None
                    )

                    if matched_area:
                        state.current_status["active_area"]  = matched_area
                        state.current_status["alert_type"]   = title
                        state.current_status["timestamp"]    = int(time.time() * 1000)

                        if time.time() - state.last_my_area_alert_time > 15:
                            broadcaster.generate_audio_files(conf, matched_area)
                            broadcaster.trigger_google_home_thread("alert", cat)

                        state.last_my_area_alert_time = time.time()
                        state.last_my_area_cat        = cat

                log_msg = f"[Live] cat={cat} | {title} | {len(cities)} ישובים"
                if log_msg != state.last_printed_live:
                    print(log_msg)
                    state.last_printed_live = log_msg

            except Exception as e:
                print(f"[Playwright Error] {e}")

        page.on("response", handle_response)

        conf = config.load_config()
        print(f"[Playwright] מאזין להתרעות. אזורים: {conf.get('areas', [])}")
        
        try:
            await page.goto("https://www.oref.org.il/heb/alerts-history/", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"[Playwright] שגיאה בטעינת הדף הראשונית, ממשיך לנסות ברקע: {e}")

        while True:
            now = time.time()

            if not state.current_status.get("is_test_mode", False):
                alerts = utils.build_all_alerts_list()
                state.current_status["all_alerts"] = alerts

                conf = config.load_config()
                my_areas = conf.get("areas", [])
                radius_km = conf.get("proximity_radius_km", 10)

                has_emergency = False
                has_early_warning = False
                has_pending = False
                has_close_threat = False

                with state.active_polygons_lock:
                    for city, data in state.active_polygons.items():
                        polygon_type = data.get("polygon_type")
                        is_my_area = any(area in city for area in my_areas)
                        
                        if is_my_area:
                            if polygon_type in (state.ALERT_TYPE_EMERGENCY, state.ALERT_TYPE_UAV):
                                has_emergency = True
                            elif polygon_type == state.ALERT_TYPE_EARLY:
                                has_early_warning = True
                            elif polygon_type == state.ALERT_TYPE_PENDING:
                                has_pending = True
                        elif polygon_type in (state.ALERT_TYPE_EMERGENCY, state.ALERT_TYPE_UAV):
                            if utils.check_close_threat([city], my_areas, radius_km):
                                has_close_threat = True

                new_status = "0"
                if has_emergency:
                    new_status = "4"
                elif has_early_warning:
                    new_status = "3"
                elif has_close_threat:
                    new_status = "2"
                elif has_pending:
                    new_status = "1"

                # If status changed
                if state.current_status["status"] != new_status:
                    old_status = state.current_status["status"]
                    state.current_status["status"] = new_status
                    
                    if new_status == "4":
                        print("\n>>> סטטוס: 4 (אזעקה מידית) <<<\n")
                    elif new_status == "3":
                        print("\n>>> סטטוס: 3 (התרעה מוקדמת) <<<\n")
                    elif new_status == "2":
                        print("\n>>> סטטוס: 2 (עירני) <<<\n")
                    elif new_status == "1":
                        print("\n>>> סטטוס: 1 (ממתין לסיום אירוע) <<<\n")
                        if old_status in ("4", "3"):
                            broadcaster.trigger_google_home_thread("all_clear")
                    elif new_status == "0":
                        state.current_status["active_area"]  = ""
                        state.current_status["alert_type"]   = ""
                        state.current_status["close_threat"] = False
                        print("\n>>> סטטוס: 0 (שגרה) <<<\n")

            await asyncio.sleep(1)
