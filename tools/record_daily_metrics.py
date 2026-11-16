"""Keep a small day-by-day record of the automatic updates, for the trend chart.

Two files, one per workflow, so the two daily jobs never edit the same file:
  frontend/src/public-data/metrics-ontong.json   온통청년 policies and youth centers
  frontend/src/public-data/metrics-support.json  the support program page comparison

Usage:
  python tools/record_daily_metrics.py ontong BEFORE.json AFTER.json [--centers CENTERS.json]
      BEFORE/AFTER are the policy list before and after today's fetch. New and removed
      policies add up over the day when the job runs more than once.
  python tools/record_daily_metrics.py support RECHECK.json
      RECHECK is one data/support-programs/rechecks/YYYYMMDD.json file.
  python tools/record_daily_metrics.py backfill
      Fills support days from the existing recheck files and today's ontong totals.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONTONG = ROOT / 'frontend/src/public-data/metrics-ontong.json'
SUPPORT = ROOT / 'frontend/src/public-data/metrics-support.json'
RECHECKS = ROOT / 'data/support-programs/rechecks'
KEEP_DAYS = 400


def korea_today() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=9)).date().isoformat()


def load(path: Path, note: str) -> dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data.get('days'), list):
                return data
        except json.JSONDecodeError:
            pass
    return {'schema_version': 1, 'note': note, 'days': []}


def save(path: Path, data: dict) -> None:
    data['days'] = sorted(data['days'], key=lambda d: d['date'])[-KEEP_DAYS:]
    # One day per line keeps the daily diff to a single line.
    lines = ',\n'.join('  ' + json.dumps(d, ensure_ascii=False, separators=(',', ':')) for d in data['days'])
    head = json.dumps({k: v for k, v in data.items() if k != 'days'}, ensure_ascii=False)[:-1]
    path.write_bytes((head + ',"days":[\n' + lines + '\n]}\n').encode('utf-8'))


def upsert(data: dict, date: str) -> dict:
    for d in data['days']:
        if d['date'] == date:
            return d
    row = {'date': date}
    data['days'].append(row)
    return row


def policy_ids(path: Path) -> set[str] | None:
    try:
        return {p['id'] for p in json.loads(path.read_text(encoding='utf-8')).get('policies', [])}
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
        return None


def record_ontong(before: Path, after: Path, centers: Path | None, date: str, out: Path = ONTONG) -> dict:
    data = load(out, '온통청년 정책·청년센터 일별 기록. new/removed는 그날 자동 수집에서 새로 생기거나 빠진 정책 수(첫 수집일은 비교 대상이 없어 null).')
    old, new = policy_ids(before), policy_ids(after)
    if new is None:
        raise SystemExit('The policy list after the fetch could not be read.')
    row = upsert(data, date)
    row['policies'] = len(new)
    if old:
        row['new'] = (row.get('new') or 0) + len(new - old)
        row['removed'] = (row.get('removed') or 0) + len(old - new)
    else:
        row.setdefault('new', None)
        row.setdefault('removed', None)
    if centers and centers.exists():
        row['centers'] = len(json.loads(centers.read_text(encoding='utf-8')).get('centers', []))
    save(out, data)
    return row


def record_support(recheck: Path, out: Path = SUPPORT) -> dict:
    data = load(out, '지원사업 공식 페이지 자동 대조 일별 결과(RENEWED 일치·갱신, CLOSED_SIGNAL 마감 표시, NOT_MATCHED 대조 실패).')
    result = json.loads(recheck.read_text(encoding='utf-8'))
    counts = result.get('counts') or {}
    row = upsert(data, result['checked_on'])
    row.update({'checked': len(result.get('results') or []), 'renewed': counts.get('RENEWED', 0),
                'closed_signal': counts.get('CLOSED_SIGNAL', 0), 'not_matched': counts.get('NOT_MATCHED', 0)})
    save(out, data)
    return row


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    mode = argv[0]
    if mode == 'ontong':
        centers = Path(argv[argv.index('--centers') + 1]) if '--centers' in argv else None
        print(json.dumps(record_ontong(Path(argv[1]), Path(argv[2]), centers, korea_today()), ensure_ascii=False))
        return 0
    if mode == 'support':
        print(json.dumps(record_support(Path(argv[1])), ensure_ascii=False))
        return 0
    if mode == 'backfill':
        for f in sorted(RECHECKS.glob('*.json')):
            record_support(f)
        policies = ROOT / 'frontend/src/public-data/youth-policies.json'
        fetched = json.loads(policies.read_text(encoding='utf-8')).get('fetched_on') or korea_today()
        record_ontong(Path('/nonexistent'), policies, ROOT / 'frontend/src/public-data/youth-centers-api.json', fetched)
        print('backfilled')
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
