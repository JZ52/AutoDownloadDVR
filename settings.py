import os
import configparser
import shlex


def load_config():
    config = configparser.ConfigParser()
    ini_path = "config.ini"
    settings = {
        "TEMP_DIR": "temp_chunks",
        "READY_DIR": "ready_videos",
        "STORES_FILE": "stores.json",
        "DB_NAME": "archive_state.db",
        "MAX_PARALLEL_THREADS": 10,
        "LOOKBACK_DAYS": 7,
        "GAP_THRESHOLD_SEC": 30,
        "FF_DEFAULT": ["-y", "-f", "concat", "-safe", "0", "-c:v", "copy", "-c:a", "copy"],
        "FF_FALLBACK": ["-y", "-f", "concat", "-safe", "0", "-c:v", "copy", "-an"]
    }
    if os.path.exists(ini_path):
        config.read(ini_path, encoding='utf-8')
        if config.has_section('PATHS'):
            settings["TEMP_DIR"] = config.get('PATHS', 'temp_dir', fallback=settings["TEMP_DIR"])
            settings["READY_DIR"] = config.get('PATHS', 'ready_dir', fallback=settings["READY_DIR"])
            settings["STORES_FILE"] = config.get('PATHS', 'stores_file', fallback=settings["STORES_FILE"])
            settings["DB_NAME"] = config.get('PATHS', 'db_name', fallback=settings["DB_NAME"])
        if config.has_section('FFMPEG'):
            if config.has_option('FFMPEG', 'default_args'):
                settings["FF_DEFAULT"] = shlex.split(config.get('FFMPEG', 'default_args'))
            if config.has_option('FFMPEG', 'fallback_args'):
                settings["FF_FALLBACK"] = shlex.split(config.get('FFMPEG', 'fallback_args'))
        if config.has_section('LOGIC'):
            settings["MAX_PARALLEL_THREADS"] = config.getint('LOGIC', 'MAX_PARALLEL_THREADS', fallback=settings["MAX_PARALLEL_THREADS"])
            settings["LOOKBACK_DAYS"] = config.getint('LOGIC', 'LOOKBACK_DAYS', fallback=settings["LOOKBACK_DAYS"])
            settings["GAP_THRESHOLD_SEC"] = config.getint('LOGIC', 'GAP_THRESHOLD_SEC', fallback=settings["GAP_THRESHOLD_SEC"])
    return settings

CFG = load_config()
TEMP_DIR = CFG["TEMP_DIR"]
READY_DIR = CFG["READY_DIR"]
STORES_FILE = CFG["STORES_FILE"]
DB_NAME = CFG["DB_NAME"]
MAX_PARALLEL_THREADS = CFG["MAX_PARALLEL_THREADS"]
LOOKBACK_DAYS = CFG["LOOKBACK_DAYS"]
GAP_THRESHOLD_SEC = CFG["GAP_THRESHOLD_SEC"]

# Создаем папки при импорте этого модуля
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(READY_DIR, exist_ok=True)