import sqlite3
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = "archive_state.db"

def get_task_status(date_id, store_name, cam_id):
    with sqlite3.connect(DB_NAME) as conn:
        res = conn.execute(
            "SELECT status FROM sync_log WHERE date_id=? AND store_name=? AND cam_id=? AND status IN ('SUCCESS', 'NO_DATA')",
            (date_id, store_name, cam_id)
        ).fetchone()
        return res[0] if res else None


def update_task_metrics(date_id, store_name, cam_id, status, dl_time=0.0, proc_time=0.0):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            INSERT OR REPLACE INTO sync_log 
            (date_id, store_name, cam_id, status, download_time_sec, process_time_sec, last_attempt) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (date_id, store_name, cam_id, status, dl_time, proc_time, now))

def check_failed_task(date_id):
    print("SEND TELEGRAM")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        message = cursor.execute(
            '''
            SELECT date_id, store_name, cam_id, status 
            FROM sync_log
            WHERE date_id = ? AND status IN ('FAILED_DL', 'FAILED_FFMPEG', 'FAILED_FFMPEG')
            '''
        ,(date_id,))
        failed_task = cursor.fetchall()

        if not failed_task:
            return None

        message = f"<b>Отчёт об ошибках выгрузки</b>\nДата: { date_id }\n\n"

        for _, store_name, cam_id, status in failed_task:
            if status == 'FAILED_DL':
                reason = "Ошибка скачивания"
            elif status == 'FAILED_FFMPEG':
                reason = "Ошибка конвертации видео"
            elif status == 'TIMEOUT_FFMPEG':
                reason = "Завис FFMPEG"
            else:
                reason = status

            message += f"<b>{ store_name }</b> (Кам.{ cam_id }) - <i>{ reason }</i>\n"

            return message
        return None


#Deleta data 25 days early
def delete_old_task(retention_days):
    threshold_date = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sync_log WHERE date_id < ?",(threshold_date,))


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sync_log (
                date_id TEXT,
                store_name TEXT,
                cam_id INTEGER,
                status TEXT,
                download_time_sec REAL,
                process_time_sec REAL,
                last_attempt TEXT,
                UNIQUE(date_id, store_name, cam_id)
            )
        ''')