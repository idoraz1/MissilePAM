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
                        state.current_status["status"]       = "1"
                        state.current_status["close_threat"] = False
                        state.current_status["active_area"]  = matched_area
                        state.current_status["alert_type"]   = title
                        state.current_status["timestamp"]    = int(time.time() * 1000)
                        state.current_status["is_early_warning"] = True

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

                    if not matched_area:
                        if utils.check_close_threat(cities, my_areas, radius_km):
                            state.current_status["close_threat"] = True

                    if matched_area:
                        state.current_status["status"]       = "1"
                        state.current_status["close_threat"] = False
                        state.current_status["active_area"]  = matched_area
                        state.current_status["alert_type"]   = title
                        state.current_status["timestamp"]    = int(time.time() * 1000)
                        state.current_status["is_early_warning"] = False

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
        await page.goto("https://www.oref.org.il/heb/alerts-history/")

        while True:
            now = time.time()

            if not state.current_status.get("is_test_mode", False):
                alerts = utils.build_all_alerts_list()
                state.current_status["all_alerts"] = alerts

                my_alert_active = now - state.last_my_area_alert_time < state.YELLOW_TIMEOUT_SECONDS

                if my_alert_active:
                    if state.current_status["status"] != "1":
                        state.current_status["status"] = "1"
                        print("\n>>> סטטוס: 1 (אזעקה אצלי) <<<\n")
                else:
                    conf     = config.load_config()
                    my_areas = conf.get("areas", [])
                    with state.active_polygons_lock:
                        my_area_pending = any(
                            state.active_polygons.get(city, {}).get("polygon_type") == state.ALERT_TYPE_PENDING
                            for area in my_areas
                            for city in state.active_polygons
                            if area in city
                        )
                    if my_area_pending:
                        if state.current_status["status"] != "2":
                            state.current_status["status"] = "2"
                            print("\n>>> סטטוס: 2 (ממתין לסיום) <<<\n")
                            broadcaster.trigger_google_home_thread("all_clear")
                    else:
                        if state.current_status["status"] != "0":
                            state.current_status["status"]       = "0"
                            state.current_status["active_area"]  = ""
                            state.current_status["alert_type"]   = ""
                            state.current_status["close_threat"] = False
                            print("\n>>> סטטוס: 0 (שגרה) <<<\n")

            await asyncio.sleep(1)
