"""Fetch youth policies from the 온통청년 Open API (getPlcy) and keep what the app can use.

For each approved policy that is still open or always open, this keeps the title, a short
summary, the region (zipCd read with data/region-codes/sigungu.json), the age range, the
employment groups, the income condition as text, the application period and the links.
Long texts are cut short and every record links back to its 온통청년 page, with attribution.

Code meanings were read from the 온통청년 policy search page (2026-11-16):
jobCd 0013001 재직자, 0013002 자영업자, 0013003 미취업자, 0013004 프리랜서, 0013005 일용근로자,
0013006 (예비)창업자, 0013007 단기근로자, 0013008 영농종사자, 0013009 기타, 0013010 제한없음;
schoolCd 0049001 고졸 미만, 0049002 고교 재학, 0049003 고졸 예정, 0049004 고교 졸업,
0049005 대학 재학, 0049006 대졸 예정, 0049007 대학 졸업, 0049008 석·박사, 0049009 기타, 0049010 제한없음;
mrgSttsCd 0055001 기혼, 0055002 미혼, 0055003 제한없음; earnCndSeCd 0043001 무관, 0043002 연소득 범위, other 기타(text); aplyPrdSeCd 0057001 일정별,
0057002 상시; bizPrdSeCd 0056001 시작~종료, 0056002 기타; plcyAprvSttsCd 0044002 승인.

The key comes from YOUTHCENTER_POLICY_KEY and is never printed or written. The output is left
alone when the policy list did not change, and a short answer is refused.

Usage: YOUTHCENTER_POLICY_KEY=... python tools/youthcenter_policy_fetch.py [OUTPUT_JSON]
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from youthcenter_fetch import get_json  # noqa: E402  (retries the API's passing 400/500 answers)

ROOT = Path(__file__).resolve().parents[1]
CODES = ROOT / 'data/region-codes/sigungu.json'
DISTRICTS = ROOT / 'frontend/src/public-data/nationwide-districts.json'
DEFAULT_OUT = ROOT / 'frontend/src/public-data/youth-policies.json'
URL = 'https://www.youthcenter.go.kr/go/ythip/getPlcy'
DETAIL = 'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/'
PAGE_SIZES = (100, 50)
MIN_RAW = 2000  # the API reported 4,020 policies on 2026-11-16

SOURCE = {
    'title': '온통청년 청년정책 Open API',
    'institution': '한국고용정보원',
    'attribution': '출처: 온통청년(한국고용정보원)',
    'url': 'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch',
}

# Employment groups the app asks about: employed, unemployed, self_employed.
JOBS = {
    '0013001': ['employed'], '0013005': ['employed'], '0013007': ['employed'],
    '0013002': ['self_employed'], '0013004': ['self_employed'], '0013008': ['self_employed'],
    '0013003': ['unemployed'], '0013006': ['self_employed', 'unemployed'],
}
NO_LIMIT_JOB = '0013010'
# Schooling stages the app asks about, from the 온통청년 schoolCd values.
SCHOOLS = {
    '0049001': 'below_hs', '0049002': 'hs_student', '0049003': 'hs_student', '0049004': 'hs_grad',
    '0049005': 'univ_student', '0049006': 'univ_expected', '0049007': 'univ_grad', '0049008': 'grad_school',
}
NO_LIMIT_SCHOOL, OTHER_SCHOOL = '0049010', '0049009'
MARRIAGE = {'0055001': 'married', '0055002': 'single'}
OTHER_JOB = '0013009'


def clean(text: str | None, limit: int) -> str:
    t = re.sub(r'\s+', ' ', (text or '').replace('&middot;', '·')).strip()
    return t if len(t) <= limit else t[:limit - 1].rstrip() + '…'


def ymd(text: str | None) -> str | None:
    m = re.fullmatch(r'(\d{4})(\d{2})(\d{2})', (text or '').strip())
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
    except ValueError:
        return None


def age_range(r: dict) -> list[int | None] | None:
    """[min, max] with None for an open end, or None when the policy sets no age limit."""
    try:
        low, high = int(r.get('sprtTrgtMinAge') or 0), int(r.get('sprtTrgtMaxAge') or 0)
    except ValueError:
        return None
    # 'Y' means 제한없음 (no age limit): that is how 온통청년's own detail page reads this field.
    if (r.get('sprtTrgtAgeLmtYn') or '').strip() == 'Y' or (low == 0 and high == 0):
        return None
    return [low or None, high or None]


def jobs(r: dict) -> dict | None:
    """Employment groups the policy names, or None when it says 제한없음 or nothing."""
    codes = [c.strip() for c in (r.get('jobCd') or '').split(',') if c.strip()]
    if not codes or NO_LIMIT_JOB in codes:
        return None
    groups = sorted({g for c in codes for g in JOBS.get(c, [])})
    return {'groups': groups, 'other': OTHER_JOB in codes or any(c not in JOBS and c != OTHER_JOB for c in codes)}


def schools(r: dict) -> dict | None:
    """Schooling stages the policy names, or None when it says 제한없음 or nothing."""
    codes = [c.strip() for c in (r.get('schoolCd') or '').split(',') if c.strip()]
    if not codes or NO_LIMIT_SCHOOL in codes:
        return None
    groups = sorted({SCHOOLS[c] for c in codes if c in SCHOOLS})
    return {'groups': groups, 'other': any(c not in SCHOOLS for c in codes)}


def marriage(r: dict) -> str | None:
    codes = {c.strip() for c in (r.get('mrgSttsCd') or '').split(',') if c.strip()}
    found = {MARRIAGE[c] for c in codes if c in MARRIAGE}
    return found.pop() if len(found) == 1 and codes <= set(MARRIAGE) else None


def income(r: dict) -> str | None:
    kind = (r.get('earnCndSeCd') or '').strip()
    if kind == '0043001':
        return None
    if kind == '0043002':
        low, high = (r.get('earnMinAmt') or '0').strip(), (r.get('earnMaxAmt') or '0').strip()
        if high not in ('', '0'):
            return f'연소득 {low}만원 이상 ~ {high}만원 이하' if low not in ('', '0') else f'연소득 {high}만원 이하'
    return clean(r.get('earnEtcCn'), 120) or '소득 기준 있음 · 공고 확인'


def organisation(r: dict) -> str:
    """The supervising body; a bare department name gets the body above it in front."""
    name = clean(r.get('sprvsnInstCdNm') or r.get('operInstCdNm'), 40)
    if re.search(r'(과|팀|실|담당관|센터)$', name):
        up = clean(r.get('rgtrUpInstCdNm') or r.get('rgtrInstCdNm'), 30)
        if up and up not in name and name not in up:
            name = f'{up} {name}'
    return name


NOTHING = {'', '-', '없음', '해당없음', '해당 없음', '제한없음', '무관'}


def optional(text: str | None, limit: int) -> str | None:
    t = clean(text, limit)
    return None if t.replace('.', '').strip() in NOTHING else t


def apply_period(r: dict) -> dict:
    kind = (r.get('aplyPrdSeCd') or '').strip()
    if kind == '0057002':
        return {'mode': 'ALWAYS'}
    days = re.findall(r'\d{8}', r.get('aplyYmd') or '')
    dates = [d for d in (ymd(x) for x in days) if d]
    if dates:
        return {'mode': 'PERIOD', 'start': min(dates), 'end': max(dates)}
    return {'mode': 'OTHER'}


def regions(r: dict, codes: dict, cities: dict) -> tuple[list[str], list[str]]:
    """Compact region keys ('*', '경기', '경기|안산시') and the zip codes that could not be read."""
    pairs, unknown = set(), []
    for code in (c.strip() for c in (r.get('zipCd') or '').split(',')):
        if not code:
            continue
        found = codes.get(code)
        if not found:
            unknown.append(code)
            continue
        pairs.update((p, c) for p, c in found)
    whole = {p for p, c in pairs if c == ''}
    for prov, options in cities.items():
        tops = [o for o in options if ' ' not in o]
        covered = {c for p, c in pairs if p == prov}

        def has(top: str) -> bool:
            wards = [o for o in options if o.startswith(top + ' ')]
            return top in covered or (bool(wards) and all(w in covered for w in wards))

        missing = [o for o in tops if not has(o)]
        # Lists entered before a district change can leave out a new district (인천 서해구·영종구,
        # 2026) or drop one city by mistake; on 2026-11-16 about 350 province-wide policies did.
        # A province with at least 8 cities that misses at most 2 of them (20%) counts as whole.
        near_whole = len(tops) >= 8 and len(missing) <= 2 and len(missing) <= 0.2 * len(tops)
        if prov not in whole and tops and (not missing or near_whole):
            whole.add(prov)
    if cities and all(p in whole for p in cities):
        return ['*'], unknown
    keys = sorted(whole) + sorted(f'{p}|{c}' for p, c in pairs if c and p not in whole)
    return keys, unknown


def normalise(records: list[dict], codes: dict, cities: dict, today: str) -> tuple[list[dict], dict]:
    out, seen = [], set()
    stats = {'not_approved': 0, 'closed': 0, 'no_region': 0, 'unknown_codes': set()}
    for r in records:
        pid = (r.get('plcyNo') or '').strip()
        title = clean(r.get('plcyNm'), 120)
        if not pid or not title or pid in seen:
            continue
        seen.add(pid)
        if (r.get('plcyAprvSttsCd') or '').strip() not in ('', '0044002'):
            stats['not_approved'] += 1
            continue
        period = apply_period(r)
        biz_end = ymd(r.get('bizPrdEndYmd')) if (r.get('bizPrdSeCd') or '').strip() == '0056001' else None
        if (period.get('end') and period['end'] < today) or (biz_end and biz_end < today):
            stats['closed'] += 1
            continue
        keys, unknown = regions(r, codes, cities)
        stats['unknown_codes'].update(unknown)
        if not keys:
            stats['no_region'] += 1
            continue
        apply_url = (r.get('aplyUrlAddr') or '').strip()
        ref_url = (r.get('refUrlAddr1') or '').strip()
        record = {
            'id': pid,
            'title': title,
            'category': clean(r.get('lclsfNm'), 30).replace('･', '·'),
            'subcategory': clean(r.get('mclsfNm'), 40).replace('･', '·'),
            'org': organisation(r),
            'summary': clean(r.get('plcySprtCn') or r.get('plcyExplnCn'), 180),
            'regions': keys,
            'age': age_range(r),
            'jobs': jobs(r),
            'school': schools(r),
            'marriage': marriage(r),
            'income': income(r),
            'extra': optional(r.get('addAplyQlfcCndCn'), 140),
            'apply': period,
            'url': DETAIL + pid,
            'apply_url': apply_url if apply_url.startswith(('http://', 'https://')) else (ref_url if ref_url.startswith(('http://', 'https://')) else None),
            'updated': (r.get('lastMdfcnDt') or '')[:10] or None,
        }
        out.append(record)
    out.sort(key=lambda p: p['id'])
    stats['unknown_codes'] = sorted(stats['unknown_codes'])
    return out, stats


def fetch_pass(key: str, size: int) -> list[dict]:
    records: list[dict] = []
    for page in range(1, 400):
        query = urllib.parse.urlencode({'apiKeyNm': key, 'rtnType': 'json', 'pageType': 1, 'pageNum': page, 'pageSize': size})
        data = get_json(f'{URL}?{query}')
        result = data.get('result') or {}
        rows = result.get('youthPolicyList') or []
        if not rows:
            break
        records.extend(rows)
        total = (result.get('pagging') or {}).get('totCount')
        if total is not None and page * size >= int(total):
            break
        time.sleep(1)
    return records


def fetch_all(key: str) -> list[dict]:
    records: list[dict] = []
    for i, size in enumerate(PAGE_SIZES):
        if i:
            time.sleep(5)
        try:
            rows = fetch_pass(key, size)
        except urllib.error.HTTPError as error:
            if not records:
                raise
            print(f'pageSize {size}: HTTP {error.code}; keeping the passes that already succeeded')
            continue
        records.extend(rows)
        print(f'pageSize {size}: {len(rows)} rows; merged distinct {len({r.get("plcyNo") for r in records})}')
    return records


def write_if_changed(out: Path, policies: list[dict], today: str) -> bool:
    if out.exists():
        try:
            if json.loads(out.read_text(encoding='utf-8')).get('policies') == policies:
                return False
        except json.JSONDecodeError:
            pass
    payload = {'schema_version': 1, 'fetched_on': today, 'source': SOURCE, 'total': len(policies), 'policies': policies}
    out.write_bytes((json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8'))
    return True


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    key = os.environ.get('YOUTHCENTER_POLICY_KEY', '').strip()
    if not key:
        print('YOUTHCENTER_POLICY_KEY is not set. Nothing to do.')
        return 0
    try:
        records = fetch_all(key)
    except Exception as error:  # the message can echo the URL with the key
        print(f'Fetch failed: {type(error).__name__}')
        return 1
    distinct = len({r.get('plcyNo') for r in records})
    if distinct < MIN_RAW:
        print(f'Only {distinct} policies came back (expected at least {MIN_RAW}). Keeping the current list.')
        return 1
    codes = json.loads(CODES.read_text(encoding='utf-8'))['codes']
    cities = json.loads(DISTRICTS.read_text(encoding='utf-8'))['cities']
    today = (datetime.now(timezone.utc) + timedelta(hours=9)).date().isoformat()
    policies, stats = normalise(records, codes, cities, today)
    changed = write_if_changed(out, policies, today)
    print(json.dumps({'raw_distinct': distinct, 'kept': len(policies), 'changed': changed, 'bytes': out.stat().st_size,
                      **{k: v for k, v in stats.items() if k != 'unknown_codes'}, 'unknown_codes': stats['unknown_codes'][:40]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
