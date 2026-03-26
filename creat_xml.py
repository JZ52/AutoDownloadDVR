import uuid
import xml.etree.ElementTree as ET


def find_tag(element, tag_name):
    if element is None: return None
    for el in element.iter():
        if el.tag.endswith(tag_name): return el
    return None

def fetch_all_fragments(session, base_url, cam, start_t, end_t):
    all_fragments = []
    pos = 0

    while True:
        search_id = str(uuid.uuid4()).upper()
        payload = f"""<?xml version="1.0" encoding="utf-8"?>
        <CMSearchDescription xmlns="http://www.isapi.org/ver20/XMLSchema">
            <searchID>{search_id}</searchID>
            <trackList><trackID>{cam}01</trackID></trackList>
            <timeSpanList><timeSpan><startTime>{start_t}</startTime><endTime>{end_t}</endTime></timeSpan></timeSpanList>
            <maxResults>40</maxResults>
            <searchResultPostion>{pos}</searchResultPostion>
        </CMSearchDescription>"""

        try:
            r = session.post(f"{ base_url }/ISAPI/ContentMgmt/search", data=payload, timeout=15)
            r.raise_for_status()
            root = ET.fromstring(r.text)

            match_list = find_tag(root, 'matchList')
            if match_list is None or len(list(match_list)) == 0: break

            items = find_all_tags(match_list, 'searchMatchItem')
            if not items: break

            all_fragments.extend(items)

            status = find_tag(root, 'responseStatusStrg')
            if status is not None and status.text == "MORE":
                pos += 40
            else:
                break
        except Exception as e:
            print(f"Ошибка поиска ISAPI: {e}")
            break

    return all_fragments