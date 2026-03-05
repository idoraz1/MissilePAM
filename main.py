import time
import threading
import asyncio

from src.utils import load_cities_from_file, load_cities_polygons, polygon_timeout_loop
from src.config import load_config
from src.broadcaster import generate_audio_files, setup_active_chromecasts
from src.scraper import run_playwright
from src.server import run_flask

if __name__ == "__main__":
    load_cities_from_file()
    load_cities_polygons()
    init_config = load_config()
    generate_audio_files(init_config)

    threading.Thread(target=polygon_timeout_loop, daemon=True).start()
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    setup_active_chromecasts(init_config)
    asyncio.run(run_playwright())
