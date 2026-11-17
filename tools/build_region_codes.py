"""Build the 5-digit 시·군·구 code table used to read the 온통청년 policy API's zipCd field.

Input: the 행정안전부 법정동코드 archive already recorded in nationwide-districts.json
(jscode20261026.zip, sha256 checked). Output: data/region-codes/sigungu.json mapping each code
to the app's [province, city] pairs (city '' means the whole province).

Policies registered before an administrative change can still carry the old codes, so a short
list of retired codes (전남광주통합특별시 이전 광주·전남, 강원·전북 특별자치도 이전, 군위군 편입,
인천 구 개편) is added by hand. Retired codes whose area was split map to the whole province.

Usage: python tools/build_region_codes.py PATH/TO/jscode20261026.zip
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from youthcenter_fetch import MERGED_GWANGJU_JEONNAM, city_name, province_key  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DISTRICTS = ROOT / 'frontend/src/public-data/nationwide-districts.json'
OUT = ROOT / 'data/region-codes/sigungu.json'

GWANGJU_OLD = {'29000': '', '29110': '동구', '29140': '서구', '29155': '남구', '29170': '북구', '29200': '광산구'}
JEONNAM_OLD = {
    '46000': '', '46110': '목포시', '46130': '여수시', '46150': '순천시', '46170': '나주시', '46230': '광양시',
    '46710': '담양군', '46720': '곡성군', '46730': '구례군', '46770': '고흥군', '46780': '보성군', '46790': '화순군',
    '46800': '장흥군', '46810': '강진군', '46820': '해남군', '46830': '영암군', '46840': '무안군', '46860': '함평군',
    '46870': '영광군', '46880': '장성군', '46890': '완도군', '46900': '진도군', '46910': '신안군',
}
# Same suffix after the special self-governing province changes (강원 42→51 in 2023, 전북 45→52 in 2024).
SUFFIX_MOVES = {'42': '51', '45': '52'}
OTHER_OLD = {
    '47720': ('대구', '군위군'),   # 군위군 moved from 경북 to 대구 in 2023
    '28110': ('인천', ''),         # 중구: split into 제물포구 and 영종구
    '28140': ('인천', '제물포구'),  # 동구 joined 제물포구
    '28260': ('인천', ''),         # 서구: split into 서해구 and 검단구
}


def parse(archive: Path) -> list[tuple[str, str, str]]:
    with zipfile.ZipFile(archive) as z:
        name = next(n for n in z.namelist() if re.search(r'KIKcd_B\.\d{8}$', n))
        text = z.read(name).decode('cp949')
    rows = []
    for line in text.splitlines()[1:]:
        code = line[:10]
        if not re.fullmatch(r'\d{5}00000', code):
            continue
        parts = [p for p in re.split(r'\s{2,}', line[10:].strip()) if not re.fullmatch(r'\d{8}', p)]
        rows.append((code[:5], parts[0], parts[1] if len(parts) > 1 else ''))
    return rows


def build(rows, cities):
    codes: dict[str, list[list[str]]] = {}
    skipped = []
    for code, sido, sgg in rows:
        if '출장' in sgg or '출장' in sido:
            skipped.append(code)
            continue
        prov = province_key(sido)
        if prov == MERGED_GWANGJU_JEONNAM:
            if not sgg:
                codes[code] = [['광주', ''], ['전남', '']]
                continue
            prov = '광주' if city_name('광주', sgg, cities) else '전남'
        if not prov:
            skipped.append(code)
            continue
        codes[code] = [[prov, city_name(prov, sgg, cities) if sgg else '']]
    for old, city in GWANGJU_OLD.items():
        codes.setdefault(old, [['광주', city]])
    for old, city in JEONNAM_OLD.items():
        codes.setdefault(old, [['전남', city]])
    for code, pairs in list(codes.items()):
        for old, new in SUFFIX_MOVES.items():
            if code.startswith(new):
                codes.setdefault(old + code[2:], pairs)
    for old, pair in OTHER_OLD.items():
        codes.setdefault(old, [list(pair)])
    return dict(sorted(codes.items())), skipped


def main() -> int:
    archive = Path(sys.argv[1])
    districts = json.loads(DISTRICTS.read_text(encoding='utf-8'))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != districts['source']['archive_sha256']:
        print('The archive does not match the one recorded in nationwide-districts.json.')
        return 1
    codes, skipped = build(parse(archive), districts['cities'])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'schema_version': 1,
        'source': {k: districts['source'][k] for k in ('institution', 'title', 'url', 'basis_date', 'archive_sha256', 'member')},
        'note': '5자리 법정 시·군·구 코드 → 앱의 [광역지역, 시·군·구]. 시·군·구가 빈 값이면 광역 전체. 행정구역 개편 이전 코드 일부를 함께 둡니다.',
        'codes': codes,
    }
    OUT.write_bytes((json.dumps(payload, ensure_ascii=False, indent=0) + '\n').encode('utf-8'))
    print(json.dumps({'codes': len(codes), 'skipped': skipped}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
