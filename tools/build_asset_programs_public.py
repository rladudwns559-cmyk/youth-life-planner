"""Build the public (frontend-only) policy-savings snapshot with a per-day status table.

The public site has no server, so the browser must not decide intake status. Python evaluates every
program for each of the next N days with the existing `backend.opportunities.matching.intake` rule
and writes the results to `schedules`; the browser only looks up today's row (like the financial
renewals). The catalog is never modified: manual verifications are read from a dated overlay file and
applied in memory, and sources whose bytes changed since capture (and were not read by a person) flag
their programs as needing review.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.opportunities.catalog import load_catalog  # noqa: E402
from backend.opportunities.matching import discover, intake  # noqa: E402

KST = timezone(timedelta(hours=9))
DEFAULT_OUT = ROOT / 'frontend/src/public-data/asset-programs-public.json'
CHANGED_NOTE = ' 공식 원문 변경이 감지되어 기존 조건은 재검토가 필요합니다. 새 모집 공고는 알림 영역에서 별도로 확인하세요.'
PUBLIC_DISCLAIMER = ' 공개 화면의 고정 자료이며 자동 갱신 서버는 연결 준비 중입니다.'
NEEDS_REVIEW = ('CONTENT_CHANGED_REVIEW_REQUIRED', 'FETCH_FAILED_REVIEW_REQUIRED')
STALE_TO_REVIEW = ('OPEN', 'UPCOMING', 'UNKNOWN')


def apply_verification(catalog, verification: dict | None):
    """Return a catalog whose listed sources carry a newer verified_on. Only sources named in the overlay change."""
    if not verification:
        return catalog
    checked_on = date.fromisoformat(verification['checked_on'])
    known = {s.source_id for s in catalog.sources}
    updates = {}
    for entry in verification['sources']:
        if entry['source_id'] not in known:
            raise ValueError(f"UNKNOWN_SOURCE_ID {entry['source_id']}")
        verified = date.fromisoformat(entry['verified_on'])
        if verified > checked_on:
            raise ValueError('VERIFIED_AFTER_CHECK_DATE')
        if not entry.get('evidence', '').strip():
            raise ValueError('VERIFICATION_EVIDENCE_REQUIRED')
        updates[entry['source_id']] = entry['verified_on']
    sources = tuple(s.model_copy(update={'verified_on': updates[s.source_id]}) if s.source_id in updates else s for s in catalog.sources)
    return catalog.model_copy(update={'sources': sources})


def flagged_programs(catalog, source_check: dict | None, verification: dict | None) -> set[str]:
    """Programs with a source whose bytes changed (or failed to load) and that nobody has read since."""
    if not source_check:
        return set()
    read = {e['source_id'] for e in (verification or {}).get('sources', [])}
    bad = {s['source_id'] for s in source_check['sources'] if s['result'] in NEEDS_REVIEW and s['source_id'] not in read}
    return {p.program_id for p in catalog.programs if bad & set(p.source_ids)}


def public_intake(program, catalog, moment: datetime, flagged: set[str]) -> dict:
    row = intake(program, catalog, moment)
    if program.program_id in flagged:
        row['fresh'] = False
        if row['status'] in STALE_TO_REVIEW:
            row['status'] = 'REVIEW_REQUIRED'
            row['label'] = '최신 공고 재확인 필요'
        if CHANGED_NOTE.strip() not in (row.get('note') or ''):
            row['note'] = (row.get('note') or '') + CHANGED_NOTE
    return row


def build(catalog, start: date, days: int, flagged: set[str]) -> dict:
    noon = lambda d: datetime(d.year, d.month, d.day, 12, 0, tzinfo=KST)
    data = json.loads(json.dumps(discover(catalog, noon(start)), ensure_ascii=False, default=str))
    by_id = {p.program_id: p for p in catalog.programs}
    for row in data['programs']:
        row['intake'] = json.loads(json.dumps(public_intake(by_id[row['program']['program_id']], catalog, noon(start), flagged), ensure_ascii=False, default=str))
    data['counts'] = {k: Counter(r['intake']['status'] for r in data['programs']).get(k, 0) for k in data['counts']}
    data['disclaimer'] = data['disclaimer'].rstrip() + PUBLIC_DISCLAIMER
    schedules = {}
    for offset in range(days + 1):
        day = start + timedelta(days=offset)
        entries = {}
        for p in catalog.programs:
            i = public_intake(p, catalog, noon(day), flagged)
            entries[p.program_id] = dict(status=i['status'], label=i['label'], fresh=i['fresh'], phase=i['phase'])
        schedules[day.isoformat()] = entries
    data['built_on'] = start.isoformat()
    data['schedules'] = schedules
    data['schedule_note'] = '날짜별 모집 상태는 Python이 공식 일정과 확인일로 미리 계산한 표입니다. 화면은 오늘 날짜의 행을 읽기만 합니다.'
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', help='first date (YYYY-MM-DD, KST); default today')
    parser.add_argument('--days', type=int, default=45)
    parser.add_argument('--verification', type=Path, action='append', default=[])
    parser.add_argument('--source-check', type=Path)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    start = date.fromisoformat(args.start) if args.start else datetime.now(KST).date()
    catalog = load_catalog()
    verification = None
    for path in args.verification:  # later overlays win per source
        part = json.loads(path.read_text(encoding='utf-8'))
        verification = part if verification is None else dict(part, sources=verification['sources'] + part['sources'])
    catalog = apply_verification(catalog, verification)
    source_check = json.loads(args.source_check.read_text(encoding='utf-8')) if args.source_check else None
    flagged = flagged_programs(catalog, source_check, verification)
    data = build(catalog, start, args.days, flagged)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(built_on=data['built_on'], programs=data['program_count'], counts=data['counts'], flagged=sorted(flagged), days=len(data['schedules'])), ensure_ascii=False))


if __name__ == '__main__':
    main()
