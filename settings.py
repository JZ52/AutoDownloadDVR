import os
import configparser
import shlex

def load_config():
    config = configparser.ConfigParser()
    ini_path = "config.ini"
    settings = {
        "TEMP_DIR": "temp_chunks",
        "READY_DIR": "ready_videos",
        "FF_DEFAULT": ["-y", "-f", "concat", "-safe", "0", "-c:v", "copy", "-c:a", "copy"],
        "FF_FALLBACK": ["-y", "-f", "concat", "-safe", "0", "-c:v", "copy", "-an"]
    }
    if os.path.exists(ini_path):
        config.read(ini_path, encoding='utf-8')
        if config.has_section('PATHS'):
            settings["TEMP_DIR"] = config.get('PATHS', 'temp_dir', fallback=settings["TEMP_DIR"])
            settings["READY_DIR"] = config.get('PATHS', 'ready_dir', fallback=settings["READY_DIR"])
        if config.has_section('FFMPEG'):
            if config.has_option('FFMPEG', 'default_args'):
                settings["FF_DEFAULT"] = shlex.split(config.get('FFMPEG', 'default_args'))
            if config.has_option('FFMPEG', 'fallback_args'):
                settings["FF_FALLBACK"] = shlex.split(config.get('FFMPEG', 'fallback_args'))
    return settings

CFG = load_config()
TEMP_DIR = CFG["TEMP_DIR"]
READY_DIR = CFG["READY_DIR"]

# Создаем папки при импорте этого модуля
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(READY_DIR, exist_ok=True)

STORES_FILE = "stores.json"
DB_NAME = "archive_state.db"
MAX_PARALLEL_THREADS = 15
LOOKBACK_DAYS = 7
GAP_THRESHOLD_SEC = 30