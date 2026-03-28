import requests
import subprocess
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from datetime import datetime, timedelta
from db import get_task_status, update_task_metrics
from xml_builder import fetch_all_fragments, find_tag



def process_camera(store, cam, date_id, start_t, end_t):
    task_name = f"[{date_id} | {store['name']} | Cam {cam}]"

    if get_task_status(date_id, store['name'], cam):
        return f"[SKIP] {task_name} Уже обработано."

    base_url = f"http://{store['ip']}:{store['port']}"

    # ИНИЦИАЛИЗАЦИЯ СЕССИИ И УМНАЯ АВТОРИЗАЦИЯ
    session = requests.Session()
    try:
        test_r = session.get(f"{base_url}/ISAPI/System/status", timeout=10)
        if test_r.status_code == 401:
            auth_header = test_r.headers.get('WWW-Authenticate', '')
            if 'Digest' in auth_header:
                session.auth = HTTPDigestAuth(store['user'], store['password'])
            else:
                session.auth = HTTPBasicAuth(store['user'], store['password'])
        else:
            session.auth = HTTPBasicAuth(store['user'], store['password'])
    except Exception as e:
        session.close()
        return f"[!] {task_name} Ошибка подключения к камере: {e}"

    print(f"[*] {task_name} Поиск фрагментов ({start_t} - {end_t})...")
    fragments = fetch_all_fragments(session, base_url, cam, start_t, end_t)

    if not fragments:
        update_task_metrics(date_id, store['name'], cam, 'NO_DATA')
        session.close()
        return f"[-] {task_name} Нет записей движения за этот период."

    events = []
    current_event = []

    for item in fragments:
        start_str = find_tag(item, 'startTime').text.replace('Z', '')
        end_str = find_tag(item, 'endTime').text.replace('Z', '')

        start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
        end_dt = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S")

        if not current_event:
            current_event = [(item, start_dt, end_dt)]
        else:
            last_end_dt = current_event[-1][2]
            gap_seconds = (start_dt - last_end_dt).total_seconds()

            if gap_seconds <= GAP_THRESHOLD_SEC:
                current_event.append((item, start_dt, end_dt))
            else:
                events.append(current_event)
                current_event = [(item, start_dt, end_dt)]

    if current_event:
        events.append(current_event)

    print(f"[*] {task_name} Найдено {len(events)} уникальных роликов.")

    total_dl_time = 0.0
    total_ff_time = 0.0
    MAX_RETRIES = 3
    RETRY_DELAY = 5

    # ОБРАБОТКА КАЖДОГО СОБЫТИЯ
    for event_idx, event_fragments in enumerate(events, 1):
        temp_files = []
        event_start = event_fragments[0][1].strftime("%Y%m%d%H%M%S")
        event_end = event_fragments[-1][2].strftime("%Y%m%d%H%M%S")

        # 1. СКАЧИВАНИЕ ФРАГМЕНТОВ
        start_dl_time = time.time()
        try:
            for i, (item, _, _) in enumerate(event_fragments, 1):
                uri_elem = find_tag(item, 'playbackURI')
                if uri_elem is None: continue

                uri = uri_elem.text
                chunk_name = os.path.join(TEMP_DIR, f"{store['name']}_{cam}_{date_id}_E{event_idx}_{i:03d}.ps")
                dl_xml = f"<?xml version='1.0' encoding='utf-8'?><downloadRequest><playbackURI>{uri}</playbackURI></downloadRequest>"

                chunk_success = False
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        with session.post(f"{base_url}/ISAPI/ContentMgmt/download", data=dl_xml, stream=True,
                                          timeout=60) as r:
                            if r.status_code == 503:
                                time.sleep(RETRY_DELAY)
                                continue

                            r.raise_for_status()
                            with open(chunk_name, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=1024 * 1024):
                                    if chunk: f.write(chunk)
                        chunk_success = True
                        break
                    except requests.exceptions.RequestException as e:
                        if attempt == MAX_RETRIES: raise
                        time.sleep(RETRY_DELAY)

                if not chunk_success:
                    raise Exception("Лимит попыток скачивания.")
                temp_files.append(chunk_name)

        except Exception as e:
            for tf in temp_files:
                if os.path.exists(tf): os.remove(tf)
            update_task_metrics(date_id, store['name'], cam, 'FAILED_DL')
            session.close()
            return f"[!] {task_name} Ошибка при выгрузке события {event_idx}: {e}"

        total_dl_time += (time.time() - start_dl_time)

        # 2. СКЛЕЙКА FFMPEG
        start_ff_time = time.time()
        final_filename = f"{date_id.replace('-', '')}_{store['name']}_Camera{cam:02d}_{event_start}_{event_end}.mp4"
        final_filepath = os.path.join(READY_DIR, final_filename)
        list_txt_path = os.path.join(TEMP_DIR, f"list_{store['name']}_{cam}_{date_id}_E{event_idx}.txt")

        with open(list_txt_path, 'w', encoding='utf-8') as f:
            for tf in temp_files:
                abs_path = os.path.abspath(tf).replace('\\', '/')
                f.write(f"file '{abs_path}'\n")

        # Основная попытка склейки
        ff_cmd = ["ffmpeg"] + CFG["FF_DEFAULT"][:4] + ["-i", list_txt_path] + CFG["FF_DEFAULT"][4:] + [final_filepath]
        result = subprocess.run(ff_cmd, capture_output=True, text=True)

        # БЛОК SELF-HEALING
        if result.returncode != 0 and ("sample rate not set" in result.stderr or "0 channels" in result.stderr):
            print(f"      [~] {task_name} Битый аудиоканал (Соб. {event_idx}). Применяем fallback...")
            ff_cmd_fallback = ["ffmpeg"] + CFG["FF_FALLBACK"][:4] + ["-i", list_txt_path] + CFG["FF_FALLBACK"][4:] + [
                final_filepath]
            result = subprocess.run(ff_cmd_fallback, capture_output=True, text=True)

        total_ff_time += (time.time() - start_ff_time)

        # 3. ОЧИСТКА МУСОРА
        if os.path.exists(list_txt_path): os.remove(list_txt_path)
        for tf in temp_files:
            if os.path.exists(tf): os.remove(tf)

        if result.returncode != 0:
            update_task_metrics(date_id, store['name'], cam, 'FAILED_FFMPEG')
            if os.path.exists(final_filepath): os.remove(final_filepath)
            session.close()
            error_log = result.stderr.strip()[-300:].replace('\n', ' ') if result.stderr else 'Нет лога ошибки'
            return f"[!] {task_name} Ошибка FFmpeg (Соб. {event_idx}): {error_log}"

    session.close()
    update_task_metrics(date_id, store['name'], cam, 'SUCCESS', round(total_dl_time, 2), round(total_ff_time, 2))
    return f"[+] {task_name} УСПЕХ! Создано роликов: {len(events)} (DL: {round(total_dl_time, 1)}s | FF: {round(total_ff_time, 1)}s)"