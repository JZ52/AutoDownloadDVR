import os
from dotenv import load_dotenv
from db import check_failed_task
import requests

load_dotenv('.env')


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
THREAD_ID = os.getenv("THREAD_ID")


def send_info(date_id, retries = 3):
    message = check_failed_task(date_id)
    if not message:
        return
    url = f"https://api.telegram.org/bot{ TELEGRAM_BOT_TOKEN }/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    if THREAD_ID:
        payload["message_thread_id"] = THREAD_ID

    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return
        except Exception as e:
            print(f"Исключение при отправке сообщения: {e}")
        time.sleep(5)  # Пауза перед повторной попыткой