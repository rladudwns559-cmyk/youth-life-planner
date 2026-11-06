"""List the rechecked products that can actually reach the public recommendation shelf.

Read-only helper for the weekly recheck. It never changes data, dates or decisions. A product is
listed when its latest recheck is CURRENT, it has a verified basic rate for at least one term, its
payment schedule is MONTHLY or LUMP_SUM and its cap is not UNKNOWN (UNKNOWN caps are decided as
MISSING by `backend.finance.discovery.decision` and never become FIT/PARTIAL).
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path


def recommendable(renewals: dict) -> list[dict]:
    rates = renewals['recommendations']['rate_by_product']
    rows = []
    for pid, record in renewals['records'].items():
        product = record['product']
        if record['status'] != 'CURRENT' or pid not in rates:
            continue
        if product['schedule'] not in ('MONTHLY', 'LUMP_SUM') or product['maximum_kind'] == 'UNKNOWN':
            continue
        page = next((s['url'] for s in product['sources'] if s['mode'] == 'OFFICIAL_PAGE'), None)
        rows.append(dict(product_id=pid, institution=product['institution'], product_name=product['product_name'],
                         kind=product['kind'], checked_on=record['checked_on'], valid_until=record['valid_until'],
                         official_page=page))
    return sorted(rows, key=lambda r: (r['valid_until'] or '', r['institution'], r['product_id']))


def to_markdown(rows: list[dict]) -> str:
    by_bank = defaultdict(list)
    for r in rows:
        by_bank[r['institution']].append(r)
    lines = [f'추천 화면에 나올 수 있는 재확인 상품 {len(rows)}개 · {len(by_bank)}개 은행', '']
    for bank in sorted(by_bank, key=lambda b: (-len(by_bank[b]), b)):
        lines.append(f'## {bank} ({len(by_bank[bank])})')
        for r in by_bank[bank]:
            lines.append(f"- [ ] `{r['product_id']}` {r['product_name']} · {r['kind']} · 확인 {r['checked_on']} · 기한 {r['valid_until']} · {r['official_page'] or '공식 페이지 없음'}")
        lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--renewals', type=Path, default=Path('frontend/src/public-data/financial-renewals.json'))
    parser.add_argument('--format', choices=('markdown', 'json'), default='markdown')
    args = parser.parse_args()
    rows = recommendable(json.loads(args.renewals.read_text(encoding='utf-8')))
    print(to_markdown(rows) if args.format == 'markdown' else json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
