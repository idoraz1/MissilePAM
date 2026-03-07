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
        browser = await p.chromium.launch(headless=True)
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
                        state.current_status["status"]       = "3"
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

                conf     = config.load_config()
                my_areas = conf.get("areas", [])
                
                has_emergency = False
                has_early = False
                has_pending = False
                
                with state.active_polygons_lock:
                    for city, data in state.active_polygons.items():
                        is_my_area = any(area in city for area in my_areas)
                        if is_my_area:
                            ptype = data.get("polygon_type")
                            if ptype in (state.ALERT_TYPE_EMERGENCY, state.ALERT_TYPE_UAV):
                                has_emergency = True
                            elif ptype == state.ALERT_TYPE_EARLY:
                                has_early = True
                            elif ptype == state.ALERT_TYPE_PENDING:
                                has_pending = True

                my_alert_active = now - state.last_my_area_alert_time < state.YELLOW_TIMEOUT_SECONDS

                # 4: EMERGENCY, 3: EARLY_WARNING, 2: CLOSE_THREAT, 1: PENDING_EVENT, 0: ROUTINE
                new_status = "0"
                
                if has_emergency or (my_alert_active and not state.current_status.get("is_early_warning", False)):
                    new_status = "4"
                elif has_early or (my_alert_active and state.current_status.get("is_early_warning", False)):
                    new_status = "3"
                elif state.current_status.get("close_threat", False):
                    new_status = "2"
                elif has_pending:
                    new_status = "1"
                else:
                    new_status = "0"

                if state.current_status["status"] != new_status:
                    state.current_status["status"] = new_status
                    if new_status == "4":
                        print("\n>>> סטטוס: 4 (אזעקה מידית) <<<\n")
                    elif new_status == "3":
                        print("\n>>> סטטוס: 3 (התרעה מוקדמת) <<<\n")
                    elif new_status == "2":
                        print("\n>>> סטטוס: 2 (עירני) <<<\n")
                    elif new_status == "1":
                        print("\n>>> סטטוס: 1 (ממתין לסיום אירוע) <<<\n")
                        broadcaster.trigger_google_home_thread("all_clear")
                    elif new_status == "0":
                        state.current_status["active_area"]  = ""
                        state.current_status["alert_type"]   = ""
                        state.current_status["close_threat"] = False
                        print("\n>>> סטטוס: 0 (שגרה) <<<\n")

            await asyncio.sleep(1)
