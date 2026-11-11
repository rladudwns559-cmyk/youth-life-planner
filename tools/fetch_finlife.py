"""Fetch deposit and savings products from the FSS "금융상품한눈에" Open API and normalise them.

Free official source: 금융감독원 금융상품통합비교공시 Open API (https://finlife.fss.or.kr, free key).
This is disclosure data that each financial company reports to the FSS, so it is labelled
"금감원 공시 기준" and kept apart from the hand-verified records in `financial-renewals.json`.
It never feeds the existing recommendation ranking by itself.

Usage (repo root):
  FINLIFE_API_KEY=... python -m tools.fetch_finlife --output frontend/src/public-data/finlife-disclosures.json
  python -m tools.fetch_finlife --fixture-dir tests/fixtures/finlife --output out.json   # offline

Without a key (and without --fixture-dir) it exits 0 and writes nothing, so a scheduled run is a no-op.
"""
import argparse
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = 'https://finlife.fss.or.kr/finlifeapi/'
ENDPOINTS = {'DEPOSIT': 'depositProductsSearch.json', 'SAVINGS': 'savingProductsSearch.json'}
GROUPS = {'020000': '은행', '030300': '저축은행'}
JOIN_DENY = {'1': '제한없음', '2': '서민전용', '3': '일부제한'}
MAX_PAGES = 50
KST = timezone(timedelta(hours=9))


class FinlifeError(RuntimeError):
    pass


def _http_get(url: str) -> dict:
    request = urllib.request.Request(url, headers={'User-Agent': 'youth-life-planner/finlife-fetch'})
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 (fixed https host)
        return json.loads(response.read().decode('utf-8'))


def fetch_pages(kind: str, group: str, key: str, get=_http_get) -> tuple[list, list]:
    """All pages for one product kind and financial group. Raises on any API error code."""
    base_list, option_list = [], []
    page, max_page = 1, 1
    while page <= max_page:
        query = urllib.parse.urlencode({'auth': key, 'topFinGrpNo': group, 'pageNo': page})
        payload = get(f'{BASE}{ENDPOINTS[kind]}?{query}')
        result = payload.get('result') or {}
        if result.get('err_cd') != '000':
            raise FinlifeError(f"{kind}/{group} page {page}: {result.get('err_cd')} {result.get('err_msg')}")
        base_list += result.get('baseList') or []
        option_list += result.get('optionList') or []
        max_page = min(int(result.get('max_page_no') or 1), MAX_PAGES)
        page += 1
    return base_list, option_list


def _text(value) -> str | None:
    if value is None:
        return None
    text = ' '.join(str(value).split())
    return text or None


def _rate(value) -> float | None:
    if value in (None, ''):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and 0 <= number <= 20 else None


def _limit(value) -> int | None:
    if value in (None, ''):
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def normalise(kind: str, group: str, base_list: list, option_list: list) -> tuple[list, list]:
    """Return (products, rejected). Rates are kept per term; nothing is calculated or ranked."""
    options: dict[tuple, list] = {}
    for option in option_list:
        options.setdefault((option.get('fin_co_no'), option.get('fin_prdt_cd')), []).append(option)
    products, rejected = [], []
    for base in base_list:
        key = (base.get('fin_co_no'), base.get('fin_prdt_cd'))
        name, company = _text(base.get('fin_prdt_nm')), _text(base.get('kor_co_nm'))
        if not all(key) or not name or not company:
            rejected.append({'reason': 'MISSING_IDENTITY', 'product': key})
            continue
        rates = []
        for option in options.get(key, []):
            months = option.get('save_trm')
            base_rate, max_rate = _rate(option.get('intr_rate')), _rate(option.get('intr_rate2'))
            if not str(months or '').isdigit() or base_rate is None:
                continue
            rates.append({
                'months': int(months),
                'rate_type': _text(option.get('intr_rate_type_nm')),
                'saving_type': _text(option.get('rsrv_type_nm')),
                'base_rate_percent': base_rate,
                'max_rate_percent': max_rate if max_rate is not None and max_rate >= base_rate else None,
            })
        if not rates:
            rejected.append({'reason': 'NO_VALID_RATE', 'product': key})
            continue
        rates.sort(key=lambda r: (r['months'], r['saving_type'] or '', r['rate_type'] or ''))
        products.append({
            'product_id': f'FSS-{kind}-{key[0]}-{key[1]}',
            'kind': kind,
            'group': GROUPS.get(group, group),
            'institution': company,
            'product_name': name,
            'join_way': _text(base.get('join_way')),
            'join_member': _text(base.get('join_member')),
            'join_restriction': JOIN_DENY.get(str(base.get('join_deny')), None),
            'maximum_krw': _limit(base.get('max_limit')),
            'special_conditions': _text(base.get('spcl_cnd')),
            'maturity_interest': _text(base.get('mtrt_int')),
            'note': _text(base.get('etc_note')),
            'disclosure_month': _text(base.get('dcls_month')),
            'disclosure_start': _text(base.get('dcls_strt_day')),
            'disclosure_end': _text(base.get('dcls_end_day')),
            'rates': rates,
        })
    return products, rejected


def build(get_pages, today: date) -> dict:
    products, rejected = [], []
    for kind in ENDPOINTS:
        for group in GROUPS:
            base_list, option_list = get_pages(kind, group)
            found, bad = normalise(kind, group, base_list, option_list)
            products += found
            rejected += [{**item, 'kind': kind, 'group': group} for item in bad]
    products.sort(key=lambda p: (p['kind'], p['institution'], p['product_name'], p['product_id']))
    return {
        'source': '금융감독원 금융상품통합비교공시 Open API (금융상품한눈에)',
        'source_url': 'https://finlife.fss.or.kr',
        'basis': 'DISCLOSURE',
        'fetched_on': today.isoformat(),
        'note': '금융회사가 금감원에 공시한 자료입니다. 은행 페이지를 직접 읽은 재확인 자료와 구분하며, 가입 전 금융회사에서 최신 조건을 확인해야 합니다.',
        'product_count': len(products),
        'rejected_count': len(rejected),
        'products': products,
        'rejected': rejected,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--fixture-dir', type=Path, help='offline: <kind>-<group>-<page>.json files')
    parser.add_argument('--today', help='YYYY-MM-DD (default: today in KST)')
    args = parser.parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else datetime.now(KST).date()
    if args.fixture_dir:
        def get(url):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            kind = next(k for k, v in ENDPOINTS.items() if v in url)
            name = f"{kind}-{query['topFinGrpNo'][0]}-{query['pageNo'][0]}.json"
            path = args.fixture_dir / name
            return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'result': {'err_cd': '000', 'max_page_no': 1}}
        get_pages = lambda kind, group: fetch_pages(kind, group, 'FIXTURE', get)
    else:
        key = os.environ.get('FINLIFE_API_KEY', '').strip()
        if not key:
            print('FINLIFE_API_KEY is not set; nothing fetched.')
            return 0
        get_pages = lambda kind, group: fetch_pages(kind, group, key)
    data = build(get_pages, today)
    if data['product_count'] == 0:
        print('No products returned; existing file left unchanged.', file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f"{data['product_count']} products ({data['rejected_count']} rejected) -> {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
