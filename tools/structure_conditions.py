"""Turn age and employment wording in the stored notice summaries into structured rules.

Only for open programs whose age or employment is still "추가 확인". The text comes from
each program's age_note / required_checks, which were written from the official notice.
Anything ambiguous (two different ranges, a range plus wording that contradicts it) is left
alone and reported, so a rule is only proposed when the wording says one thing.

Usage:
  python tools/structure_conditions.py propose  -> data/support-programs/structured-conditions-20261116.json
  python tools/structure_conditions.py review   -> prints every proposal with the words it came from
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'frontend/src/public-data/current-support-web.json'
OUT = ROOT / 'data/support-programs/structured-conditions-20261116.json'

DASH = r'\s*[~∼\-–]\s*'
CURRENT = re.compile(r'만?\s*(\d{2})\s*세?' + DASH + r'만?\s*(\d{2})\s*세')
CURRENT2 = re.compile(r'만?\s*(\d{2})\s*세\s*이상\s*(?:만\s*)?(\d{2})\s*세\s*이하')
BIRTH_YEARS = re.compile(r'((?:19|20)\d{2})\s*년?' + DASH + r'((?:19|20)\d{2})\s*년\s*?(?:생|출생)')
BIRTH_DATES = re.compile(r'((?:19|20)\d{2})\s*[.\-]\s*(\d{1,2})\s*[.\-]\s*(\d{1,2})\.?' + DASH + r'((?:19|20)\d{2})\s*[.\-]\s*(\d{1,2})\s*[.\-]\s*(\d{1,2})')
MILITARY = re.compile(r'제대군인|병역|군\s*복무|복무기간|의무복무')
# Wording that says the range does not decide who may apply (a preference, someone else's age,
# a second group with its own rule): the age is left as 추가 확인.
NOT_A_LIMIT = re.compile(r'우선\s*(?:선발|대상).{0,30}제외하지\s*않|나이만으로.{0,20}제외하지\s*않|부부\s*중|별도\s*연령|소상공인의\s*별도')
HIGH_SCHOOL = re.compile(r'고(?:교|등학교)\s*졸업\s*예정|고3')
STATED_YEARS = re.compile(r'최대\s*3\s*(?:년|세)|최대\s*42\s*세')
UNCLEAR = re.compile(r'기준일\s*미|산정\s*기준.{0,6}미|연령.{0,8}(확인되지|미확인|미기재)|상충|서로 다른|과거')


def age_from(text: str) -> tuple[dict | None, str]:
    births = {(f'{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}', f'{m[4]}-{int(m[5]):02d}-{int(m[6]):02d}') for m in BIRTH_DATES.finditer(text)}
    years = {(f'{m[1]}-01-01', f'{m[2]}-12-31') for m in BIRTH_YEARS.finditer(text)}
    ranges = {(int(m[1]), int(m[2])) for m in CURRENT.finditer(text)} | {(int(m[1]), int(m[2])) for m in CURRENT2.finditer(text)}
    ranges = {r for r in ranges if 10 <= r[0] < r[1] <= 49}
    military = bool(MILITARY.search(text))
    if NOT_A_LIMIT.search(text):
        return None, "range is a preference or not the applicant's own"
    # The notice's reference date (application day, 1 January, notice day) and the high-school
    # senior exception make the year right outside the range uncertain, not a clear mismatch.
    margin = 2 if HIGH_SCHOOL.search(text) else 1
    extra = {'age_margin': margin, **({'older_exception_years': 3} if military and STATED_YEARS.search(text) else {})}
    if births and len(births) == 1:
        s, e = next(iter(births))
        return dict(kind='BIRTH_RANGE', birth_start=s, birth_end=e, older_exception=military, **extra), 'birth dates'
    if years and len(years) == 1 and not births:
        s, e = next(iter(years))
        # A matching age range alongside the years ("만 19~39세(1986~2007년생)") is the same rule.
        return dict(kind='BIRTH_RANGE', birth_start=s, birth_end=e, older_exception=military, **extra), 'birth years'
    if births or years:
        return None, 'several birth ranges'
    if len(ranges) == 1:
        if UNCLEAR.search(text):
            return None, 'range with an unclear reference date'
        lo, hi = next(iter(ranges))
        return dict(kind='CURRENT', minimum=lo, maximum=hi, older_exception=military, **extra), 'age range'
    if len(ranges) > 1:
        return None, 'several age ranges'
    return None, 'no range'


ONLY_UNEMPLOYED = re.compile(r'미취업\s*(?:청년|자|상태|자만|청년만|중인)|구직\s*중인\s*미취업|취업하지\s*않은')
WORKING_OK = re.compile(r'재직|근로\s*중|직장인|취업자도|단기\s*(?:근로|노동)|주\s*\d+\s*시간|아르바이트|무관|일용|시간제|고용보험\s*미가입|사업자|비정규직|예외|우선|이직')
ONLY_EMPLOYED = re.compile(r'재직\s*(?:중인\s*)?(?:청년|자)(?:만|에\s*한)|재직\s*중인\s*청년|재직자\s*대상|근로\s*청년\s*대상')
NOT_WORKING_OK = re.compile(r'미취업|구직|취업\s*준비|예비')


def employment_from(text: str) -> tuple[dict | None, str]:
    if ONLY_UNEMPLOYED.search(text) and not WORKING_OK.search(text):
        return dict(employed='FAIL', unemployed='PASS', self_employed='UNKNOWN'), 'unemployed only'
    if ONLY_EMPLOYED.search(text) and not NOT_WORKING_OK.search(text):
        return dict(employed='PASS', unemployed='FAIL', self_employed='UNKNOWN'), 'employed only'
    return None, 'no clear employment wording'


def snippet(text: str, pattern: re.Pattern) -> str:
    m = pattern.search(text)
    if not m:
        return ''
    return text[max(0, m.start() - 25):m.end() + 25].replace('\n', ' ')


def proposals():
    w = json.loads(WEB.read_text(encoding='utf-8'))
    intake = w['schedule_pool'][w['calendar'][max(w['calendar'])]] if False else None
    out, skipped = [], []
    for i, p in enumerate(w['programs']):
        r = w['personal']['rules'][i]
        age_unknown = r is None or r['age']['kind'] == 'UNKNOWN'
        emp_unknown = r is None or all(r[k] == 'UNKNOWN' for k in ('employed', 'unemployed', 'self_employed'))
        if not (age_unknown or emp_unknown):
            continue
        # The project only builds matching rules on pages read directly, not on search-index copies.
        if any(src['evidence'] == 'OFFICIAL_INDEXED_PAGE' for src in p['sources']):
            skipped.append((p['program_id'], 'all', 'search-index evidence only'))
            continue
        text = ' '.join([p['age_note'], *(p['required_checks'] or [])])
        item = {'program_id': p['program_id'], 'title': p['title']}
        if age_unknown:
            age, why = age_from(p['age_note'])
            if age:
                item['age'] = {**age, 'note': p['age_note']}
                item['age_from'] = why
            else:
                skipped.append((p['program_id'], 'age', why))
        if emp_unknown:
            emp, why = employment_from(text)
            if emp:
                item['employment'] = emp
                item['employment_from'] = snippet(text, ONLY_UNEMPLOYED if emp['employed'] == 'FAIL' else ONLY_EMPLOYED)
            else:
                skipped.append((p['program_id'], 'employment', why))
        if 'age' in item or 'employment' in item:
            out.append(item)
    return out, skipped


def main(argv):
    mode = argv[0] if argv else 'review'
    out, skipped = proposals()
    if mode == 'propose':
        # Programs filled on an earlier run no longer look empty; keep what is already in the file.
        if OUT.exists() and '--fresh' not in argv:
            earlier = {c['program_id']: c for c in json.loads(OUT.read_text(encoding='utf-8'))['conditions']}
            fresh = {x['program_id'] for x in out}
            out = [*out, *({'program_id': pid, **c} for pid, c in earlier.items() if pid not in fresh)]
        payload = {
            'schema_version': 1,
            'built_on': '2026-11-16',
            'method': '모집 중 사업 중 나이·취업 조건이 비어 있던 사업의 공고 요약 문구(age_note·required_checks)에서 하나의 범위만 명시된 경우에만 구조화. 범위가 여러 개이거나 기준일이 불분명하면 추가 확인으로 둠.',
            'conditions': [{k: v for k, v in item.items() if k in ('program_id', 'age', 'employment')} for item in out],
        }
        OUT.write_bytes((json.dumps(payload, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    report = {'proposed': len(out), 'with_age': sum('age' in x for x in out), 'with_employment': sum('employment' in x for x in out),
              'skipped': {k: sum(1 for s in skipped if f'{s[1]}:{s[2]}' == k) for k in sorted({f'{s[1]}:{s[2]}' for s in skipped})}}
    print(json.dumps(report, ensure_ascii=False))
    if mode == 'review':
        for x in out:
            a = x.get('age')
            age = '' if not a else (f"{a['minimum']}~{a['maximum']}세" if a['kind'] == 'CURRENT' else f"{a['birth_start']}~{a['birth_end']}") + (' +병역' if a and a['older_exception'] else '')
            print(json.dumps([x['program_id'], x['title'][:30], age, x.get('age_from', ''), (a or {}).get('note', '')[:120],
                              x.get('employment', {}).get('employed', ''), x.get('employment_from', '')[:90]], ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
