from flask import Flask, send_from_directory, jsonify, request, send_file
from flask_cors import CORS
import logging
import threading
import time
import zipfile
import io
import os
from datetime import datetime

import src.state as state
import src.config as config
import src.utils as utils
import src.broadcaster as broadcaster

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)

@app.route('/')
def serve_dashboard():
    if config.PUBLIC_MODE:
        return send_from_directory(config.FRONTEND_DIR, 'public_index.html')
    return send_from_directory(config.FRONTEND_DIR, 'index.html')

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(config.AUDIO_DIR, filename)

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'GET':
        return jsonify(config.load_config())
    if config.PUBLIC_MODE:
        return jsonify({"success": False, "message": "מערכת ציבורית - אין הרשאה"}), 403
    new_config = request.json
    config.save_config(new_config)
    broadcaster.generate_audio_files(new_config)
    threading.Thread(target=lambda: broadcaster.setup_active_chromecasts(new_config), daemon=True).start()
    return jsonify({"success": True, "message": "הגדרות נשמרו"})

@app.route('/api/status')
def status_api():
    s = dict(state.current_status)
    s["all_alerts"] = utils.build_all_alerts_list()
    return jsonify(s)

@app.route('/api/devices')
def get_devices():
    return jsonify({"devices": broadcaster.discover_chromecasts()})

@app.route('/api/test', methods=['POST'])
def test_audio():
    if config.PUBLIC_MODE:
        return jsonify({"success": False, "message": "מערכת ציבורית - אין הרשאה"}), 403
    data     = request.json
    filename = ("alert_immediate.mp3" if data.get("type") == "alert"
                else f"{data.get('type', 'connected')}.mp3")
    broadcaster.play_audio_thread(filename, target_speaker_name=data.get("speaker"))
    return jsonify({"success": True})

@app.route('/api/test_esp', methods=['POST'])
def test_esp_hardware():
    if config.PUBLIC_MODE:
        return jsonify({"success": False, "message": "מערכת ציבורית - אין הרשאה"}), 403
    def run_esp_test():
        state.current_status["status"]       = "1"
        state.current_status["active_area"]  = "בדיקת מערכת (ESP32)"
        state.current_status["alert_type"]   = "בדיקה יזומה"
        state.current_status["is_test_mode"] = True
        time.sleep(5)
        state.current_status["status"]       = "0"
        state.current_status["active_area"]  = ""
        state.current_status["alert_type"]   = ""
        state.current_status["is_test_mode"] = False
    threading.Thread(target=run_esp_test, daemon=True).start()
    return jsonify({"success": True})

@app.route('/api/clear_alerts', methods=['POST'])
def clear_alerts():
    if config.PUBLIC_MODE:
        return jsonify({"success": False, "message": "מערכת ציבורית - אין הרשאה"}), 403
    with state.active_polygons_lock:
        state.active_polygons.clear()
    state.current_status["status"]       = "0"
    state.current_status["active_area"]  = ""
    state.current_status["alert_type"]   = ""
    state.current_status["close_threat"] = False
    state.last_my_area_alert_time        = 0
    state.last_my_area_cat               = 1
    state.last_printed_live              = ""
    print("[Manual] המפה נוקתה ידנית.")
    return jsonify({"success": True, "message": "המפה נוקתה"})

@app.route('/api/esp_command')
def esp_command_api():
    if config.PUBLIC_MODE:
        return jsonify({"command": "idle", "file": 0, "volume": 0})
    cmd = dict(state.esp_command)
    state.esp_command = {"command": "idle", "file": 0, "volume": 25}
    return jsonify(cmd)

@app.route('/api/esp_play', methods=['POST'])
def esp_play():
    if config.PUBLIC_MODE:
        return jsonify({"success": False, "message": "מערכת ציבורית - אין הרשאה"}), 403
    data        = request.json
    file_num    = int(data.get("file", 1))
    volume      = int(data.get("volume", 25))
    state.esp_command = {"command": "play", "file": file_num, "volume": volume}
    return jsonify({"success": True, "queued_file": file_num})

@app.route('/api/esp_sd_zip')
def esp_sd_zip():
    if config.PUBLIC_MODE:
        return jsonify({"success": False, "message": "מערכת ציבורית - אין הרשאה"}), 403
    conf        = config.load_config()
    esp_cfg     = conf.get("esp32", {})
    zip_buffer  = io.BytesIO()
    file_mapping = {
        esp_cfg.get("file_alert_immediate", 1): "alert_immediate.mp3",
        esp_cfg.get("file_all_clear",        2): "routine.mp3",
        esp_cfg.get("file_startup",           3): "connected.mp3",
        esp_cfg.get("file_uav",               4): "alert_uav.mp3",
        esp_cfg.get("file_alert_early",       5): "alert_early.mp3",
    }
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for sd_num, src_filename in file_mapping.items():
            src_path = os.path.join(config.AUDIO_DIR, src_filename)
            if os.path.exists(src_path):
                zf.write(src_path, f"MP3/{sd_num:04d}.mp3")
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip',
                     as_attachment=True, download_name='SD_Card_Files.zip')

@app.route('/api/esp_sd_status')
def esp_sd_status():
    if config.PUBLIC_MODE:
        return jsonify([])
    conf    = config.load_config()
    esp_cfg = conf.get("esp32", {})
    file_mapping = {
        esp_cfg.get("file_alert_immediate", 1): ("alert_immediate.mp3", "אזעקה מידית"),
        esp_cfg.get("file_all_clear",        2): ("routine.mp3",         "חזרה לשגרה"),
        esp_cfg.get("file_startup",           3): ("connected.mp3",       "מערכת מחוברת"),
        esp_cfg.get("file_uav",               4): ("alert_uav.mp3",       'כטב"ם עוין'),
        esp_cfg.get("file_alert_early",       5): ("alert_early.mp3",     "התרעה מוקדמת"),
    }
    result = []
    for sd_num, (filename, label) in file_mapping.items():
        path   = os.path.join(config.AUDIO_DIR, filename)
        exists = os.path.exists(path)
        result.append({
            "sd_file":  f"{sd_num:04d}.mp3",
            "label":    label,
            "filename": filename,
            "exists":   exists,
            "size_kb":  round(os.path.getsize(path) / 1024, 1) if exists else 0,
            "updated":  datetime.fromtimestamp(os.path.getmtime(path)).strftime("%H:%M %d/%m/%Y") if exists else "-"
        })
    return jsonify(result)


def run_flask():
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
