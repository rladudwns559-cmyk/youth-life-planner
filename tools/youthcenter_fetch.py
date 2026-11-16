"""Fetch the nationwide youth-center list from the 온통청년 Open API (getSpace).

Keeps only what the help panel shows (name, address, phone, homepage, region) and maps each
center to the province and city names the app already uses. The key comes from the
YOUTHCENTER_CENTER_KEY environment variable and is never printed or written.

The output is left untouched when the list did not change, so the file only moves when the
data does. A suspiciously small answer (an outage or a changed API) is refused instead of
replacing the list.

Usage: YOUTHCENTER_CENTER_KEY=... python tools/youthcenter_fetch.py [OUTPUT_JSON]
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISTRICTS = ROOT / 'frontend/src/public-data/nationwide-districts.json'
DEFAULT_OUT = ROOT / 'frontend/src/public-data/youth-centers-api.json'
URL = 'https://www.youthcenter.go.kr/go/ythip/getSpace'
PAGE_SIZE = 100
MIN_CENTERS = 300  # the API had 710 on 2026-11-16; far fewer means something went wrong

SOURCE = {
    'title': '온통청년 청년센터 정보 Open API',
    'institution': '한국고용정보원',
    'attribution': '출처: 온통청년(한국고용정보원)',
    'url': 'https://www.youthcenter.go.kr/youthApply/ythCenter/ythCenterMain',
}

# Official province names (and the short forms some records use) to the app's region keys.
PROVINCES = {
    '서울': '서울', '부산': '부산', '대구': '대구', '인천': '인천', '광주': '광주', '대전': '대전', '울산': '울산',
    '세종': '세종', '경기': '경기', '강원': '강원', '충북': '충북', '충청북': '충북', '충남': '충남', '충청남': '충남',
    '전북': '전북', '전라북': '전북', '전남': '전남', '전라남': '전남', '경북': '경북', '경상북': '경북',
    '경남': '경남', '경상남': '경남', '제주': '제주',
}
PROVINCE_SUFFIX = re.compile(r'(특별자치시|특별자치도|특별시|광역시|도)$')


def province_key(name: str) -> str | None:
    stem = PROVINCE_SUFFIX.sub('', (name or '').replace(' ', ''))
    return PROVINCES.get(stem)


def squash(text: str) -> str:
    return re.sub(r'\s+', '', text or '')


def city_name(province: str, sgg: str, cities: dict[str, list[str]]) -> str:
    """The app's city option for a district name, or '' when it cannot be matched safely."""
    options = cities.get(province, [])
    if not options or not sgg:
        return ''
    key = squash(sgg)
    for option in options:
        if squash(option) == key:
            return option
    # "수원시장안구" style names: fall back to the city that the ward belongs to.
    starts = [o for o in options if ' ' not in o and key.startswith(squash(o))]
    return max(starts, key=len) if starts else ''


def phone(value: str) -> str | None:
    text = (value or '').strip()
    digits = re.sub(r'\D', '', text)
    return text if 8 <= len(digits) <= 12 else None


def homepage(value: str) -> str | None:
    text = (value or '').strip()
    if text.startswith('www.'):
        text = 'https://' + text
    if not re.match(r'^https?://[^\s/]+\.[^\s]+$', text):
        return None
    return text


def normalise(records: list[dict], cities: dict[str, list[str]]) -> list[dict]:
    centers = []
    seen = set()
    for r in records:
        sn = str(r.get('cntrSn') or '').strip()
        name = (r.get('cntrNm') or '').strip()
        province = province_key(r.get('stdgCtpvCdNm') or '')
        if not sn or not name or not province or sn in seen:
            continue
        seen.add(sn)
        address = ' '.join(p for p in ((r.get('cntrAddr') or '').strip(), (r.get('cntrDaddr') or '').strip()) if p)
        sgg = (r.get('stdgSggCdNm') or '').strip()
        centers.append({
            'id': 'YC-' + sn,
            'province': province,
            'city': city_name(province, sgg, cities),
            'district_label': sgg,
            'name': name,
            'address': address,
            'phone': phone(r.get('cntrTelno') or ''),
            'url': homepage(r.get('cntrUrlAddr') or ''),
        })
    centers.sort(key=lambda c: (c['province'], c['city'], c['name'], c['id']))
    return centers


def fetch_all(key: str) -> list[dict]:
    records: list[dict] = []
    total = None
    for page in range(1, 60):
        query = urllib.parse.urlencode({'apiKeyNm': key, 'rtnType': 'json', 'pageNum': page, 'pageSize': PAGE_SIZE})
        request = urllib.request.Request(f'{URL}?{query}', headers={'User-Agent': 'youth-life-planner/1.0', 'Accept': 'application/json'})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode('utf-8', errors='replace'))
        result = data.get('result') or {}
        rows = result.get('youthPolicyList') or []
        total = (result.get('pagging') or {}).get('totCount', total)
        records.extend(rows)
        print(f'page {page}: {len(rows)} rows, totCount {total}, resultCode {data.get("resultCode")}')
        if not rows or (total is not None and len(records) >= int(total)):
            break
    return records


def write_if_changed(out: Path, centers: list[dict], today: str) -> bool:
    if out.exists():
        try:
            if json.loads(out.read_text(encoding='utf-8')).get('centers') == centers:
                return False
        except json.JSONDecodeError:
            pass
    payload = {'schema_version': 1, 'fetched_on': today, 'source': SOURCE, 'total': len(centers), 'centers': centers}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return True


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    key = os.environ.get('YOUTHCENTER_CENTER_KEY', '').strip()
    if not key:
        print('YOUTHCENTER_CENTER_KEY is not set. Nothing to do.')
        return 0
    try:
        records = fetch_all(key)
    except Exception as error:  # the message can echo the URL with the key
        print(f'Fetch failed: {type(error).__name__}')
        return 1
    cities = json.loads(DISTRICTS.read_text(encoding='utf-8'))['cities']
    centers = normalise(records, cities)
    if len(centers) < MIN_CENTERS:
        print(f'Only {len(centers)} centers came back (expected at least {MIN_CENTERS}). Keeping the current list.')
        return 1
    today = (datetime.now(timezone.utc) + timedelta(hours=9)).date().isoformat()
    changed = write_if_changed(out, centers, today)
    unmatched = sum(1 for c in centers if not c['city'] and c['province'] != '세종')
    print(json.dumps({'centers': len(centers), 'changed': changed, 'without_city': unmatched}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
