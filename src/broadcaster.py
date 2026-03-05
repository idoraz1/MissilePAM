import os
import pychromecast
from gtts import gTTS
import threading
import src.state as state
import src.config as config

def generate_audio_files(conf, trigger_area=""):
    if not os.path.exists(config.AUDIO_DIR):
        os.makedirs(config.AUDIO_DIR)
    texts       = conf.get("texts", {})
    area_to_say = trigger_area if trigger_area else (conf["areas"][0] if conf.get("areas") else "")
    try:
        gTTS(texts.get("alert_immediate", "אזעקה").replace("{area}", area_to_say), lang='iw').save(
            os.path.join(config.AUDIO_DIR, "alert_immediate.mp3"))
        gTTS(texts.get("alert_uav", "כטב\"ם").replace("{area}", area_to_say), lang='iw').save(
            os.path.join(config.AUDIO_DIR, "alert_uav.mp3"))
        gTTS(texts.get("alert_early", "התרעה מקדימה").replace("{area}", area_to_say), lang='iw').save(
            os.path.join(config.AUDIO_DIR, "alert_early.mp3"))
        gTTS(texts.get("all_clear", "חזרה לשגרה"), lang='iw').save(
            os.path.join(config.AUDIO_DIR, "routine.mp3"))
        gTTS(texts.get("startup", "מחובר"), lang='iw').save(
            os.path.join(config.AUDIO_DIR, "connected.mp3"))
        gTTS(texts.get("alert_immediate", "אזעקה").replace("{area}", area_to_say), lang='iw').save(
            os.path.join(config.AUDIO_DIR, "alert.mp3"))
        print("[Audio] כל קבצי MP3 נוצרו בהצלחה.")
        return True
    except Exception as e:
        print(f"[Audio Error] {e}")
        return False


def discover_chromecasts():
    chromecasts, browser = pychromecast.get_chromecasts()
    names = [cc.name for cc in chromecasts]
    pychromecast.discovery.stop_discovery(browser)
    return names


def setup_active_chromecasts(conf):
    speakers_to_find = conf.get("speakers", [])
    if not speakers_to_find:
        print("[Google Home] אין רמקולים מוגדרים.")
        return
    state.cast_devices = {}
    chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=speakers_to_find)
    state.cast_browser = browser
    for cc in chromecasts:
        cc.wait()
        state.cast_devices[cc.name] = cc
        print(f"[Google Home] מחובר: {cc.name}")
    if conf.get("play_startup_sound", False):
        for name in state.cast_devices:
            play_audio_thread("connected.mp3", name)


def play_audio(filename, target_speaker_name=None, override_volume=None):
    speakers = (
        [state.cast_devices[target_speaker_name]]
        if target_speaker_name and target_speaker_name in state.cast_devices
        else state.cast_devices.values()
    )
    url = f"http://{config.local_ip}:5000/audio/{filename}"
    for device in speakers:
        try:
            if override_volume is not None:
                device.set_volume(override_volume)
            mc = device.media_controller
            mc.play_media(url, 'audio/mp3')
            mc.block_until_active()
        except Exception:
            pass


def play_audio_thread(filename, target_speaker_name=None, override_volume=None):
    threading.Thread(target=play_audio,
                     args=(filename, target_speaker_name, override_volume),
                     daemon=True).start()


def trigger_google_home(status_code, cat="1"):
    conf  = config.load_config()
    volumes = conf.get("volumes", {})
    toggles = conf.get("toggles", {})
    try:
        if status_code == "alert":
            if cat == "6":
                if not toggles.get("enable_uav", True): return
                play_audio_thread("alert_uav.mp3", override_volume=volumes.get("uav", 1.0))
            elif cat == "10":
                if not toggles.get("enable_early", True): return
                play_audio_thread("alert_early.mp3", override_volume=volumes.get("early", 0.8))
            else:
                if not toggles.get("enable_immediate", True): return
                for name, device in state.cast_devices.items():
                    if device.status and device.status.volume_level is not None:
                        state.previous_volumes[name] = device.status.volume_level
                play_audio_thread("alert_immediate.mp3", override_volume=volumes.get("immediate", 1.0))

        elif status_code == "all_clear":
            if not toggles.get("enable_all_clear", True): return
            vol = volumes.get("all_clear", 0.5)
            for name, device in state.cast_devices.items():
                restore_vol = max(state.previous_volumes.get(name, 0.5), vol)
                try: device.set_volume(restore_vol)
                except: pass
            play_audio_thread("routine.mp3")
    except Exception as e:
        print(f"[Google Home] שגיאה: {e}")


def trigger_google_home_thread(status_code, cat="1"):
    threading.Thread(target=trigger_google_home,
                     args=(status_code, cat),
                     daemon=True).start()
