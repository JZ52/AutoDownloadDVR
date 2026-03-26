import os
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from db import init_db


def main():
    print("=== Инициализация системы ===")


    if not os.path.exists(STORES_FILE):
        print(f"Файл {STORES_FILE} не найден. Работа остановлена.")
        return

    with open(STORES_FILE, 'r', encoding='utf-8') as f:
        stores = json.load(f)

    tasks = []
    now = datetime.now()

    for i in range(1, LOOKBACK_DAYS + 1):
        target_day = now - timedelta(days=i)
        date_id = target_day.strftime("%Y-%m-%d")

        for store in stores:
            if not store.get('enabled', True): continue

            st_time = store.get("time_start", "09:00:00")
            end_time = store.get("time_end", "21:00:00")

            start_t = f"{date_id}T{st_time}"
            end_t = f"{date_id}T{end_time}"

            for cam in store.get('cameras', []):
                tasks.append((store, cam, date_id, start_t, end_t))

    print(f"Сформирована очередь из {len(tasks)} проверок за последние {LOOKBACK_DAYS} дней.")
    print("Запускаем Worker Pool...\n")

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_THREADS) as executor:
        futures = [executor.submit(process_camera, *t) for t in tasks]
        for future in futures:
            print(future.result())

    print("\n=== Все задачи в пуле завершены ===")


if __name__ == "__main__":
    init_db()
    main()