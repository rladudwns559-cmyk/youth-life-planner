import json
from datetime import date

from backend.finance.discovery import load_catalog
from backend.finance.renewal import compile_renewals
from tools import auto_recheck as ar

TODAY = date(2026, 11, 12)
RATES = [
    {'min_months': 6, 'max_months': 11, 'base_rate_percent': '3.30'},
    {'min_months': 12, 'max_months': 23, 'base_rate_percent': '3.70'},
    {'min_months': 24, 'max_months': 35, 'base_rate_percent': '3.50'},
    {'min_months': 36, 'max_months': 36, 'base_rate_percent': '3.50'},
]
TABLE = '가입기간 기본금리 최고금리 6개월 이상 3.30 % 3.90 % 12개월 이상 3.70 % 4.30 % 24개월 이상 3.50 % 4.10 % 36개월 이상 3.50 % 4.10 %'


def test_rate_table_in_order_matches_and_a_changed_row_does_not():
    assert ar.rates_on_page(RATES, TABLE)[0]
    changed = TABLE.replace('12개월 이상 3.70', '12개월 이상 3.60')
    assert not ar.rates_on_page(RATES, changed)[0]
    # the old value still printed elsewhere on the page must not rescue a changed table
    assert not ar.rates_on_page(RATES, changed + ' 지난달 금리 3.70 %')[0]


def test_descending_tables_and_merged_equal_rows_match():
    descending = '36개월 3.50 24개월 3.50 12개월 3.70 6개월 3.30'
    assert ar.rates_on_page(RATES, descending)[0]
    merged = '6개월 3.30 12개월 3.70 24개월~36개월 3.50'
    assert ar.rates_on_page(RATES, merged)[0]


def test_rates_far_apart_or_out_of_order_do_not_match():
    far = '6개월 3.30 ' + '가' * 3000 + ' 12개월 3.70 24개월 3.50 36개월 3.50'
    assert not ar.rates_on_page(RATES, far)[0]
    shuffled = '3.70 그리고 3.50 그리고 3.30 그리고 3.90'
    assert not ar.rates_on_page(RATES, shuffled)[0]


def test_single_rate_needs_a_rate_label_and_ignores_amounts():
    one = [{'min_months': 1, 'max_months': 6, 'base_rate_percent': '2.00'}]
    assert ar.rates_on_page(one, '기본이율 1개월~6개월 2.00')[0]
    assert not ar.rates_on_page(one, '수수료 2.00 달러')[0]
    assert not ar.rates_on_page(one, '기본이율 최고 1,002.00원')[0]


def test_name_check_uses_the_core_name_and_sees_sales_ended():
    assert ar.name_on_page('광주FC적금 · 정액적립식', '상품명 광주 FC 적금 안내') == (True, False)
    assert ar.name_on_page('가나 적금', '다라 적금') == (False, False)
    assert ar.name_on_page('가나 적금', '가나 적금(2026.10.01 판매중단)') == (True, True)
    assert ar.name_on_page('가나 적금', '가나 적금(판매중단) 가나 적금 신규 안내') == (True, False)


def _page_for(product):
    rows = ' '.join(f"{r['min_months']}개월 이상 기본금리 {r['base_rate_percent']} %" for r in sorted(product['rates'], key=lambda r: r['min_months']))
    return f"{product['product_name'].split(' · ')[0]} 상품안내 " + '설명 ' * 200 + rows


def test_evaluate_renews_only_matching_pages_and_the_batch_compiles():
    latest = ar.latest_entries()
    renewals = json.loads(ar.PUBLIC.read_text(encoding='utf-8'))
    ids = [r['product_id'] for r in ar.recommendable(renewals)][:4]
    good, changed, broken, short = ids
    by_url = {ar.source_url(latest[i][1]['product']): i for i in ids}

    def get_text(url):
        pid = by_url[url]
        product = latest[pid][1]['product']
        if pid == broken:
            raise TimeoutError('blocked')
        if pid == short:
            return '점검 중'
        text = _page_for(product)
        if pid == changed:
            text = text.replace(f"{product['rates'][0]['base_rate_percent']} %", '9.99 %', 1)
        return text

    updates, report = ar.evaluate(TODAY, get_text, set(ids))
    outcome = {r['product_id']: r['outcome'] for r in report}
    assert outcome == {good: 'RENEWED', changed: 'MISMATCH', broken: 'UNREADABLE', short: 'UNREADABLE'}
    assert [u['product']['product_id'] for u in updates] == [good]
    entry = updates[0]
    assert 'automated comparison' in entry['evidence_note'] and 'not a human reading' in entry['evidence_note']
    assert all(s['reviewed_on'] == TODAY.isoformat() and '(자동 대조)' in s['title'] for s in entry['product']['sources'])
    assert any(s['mode'] == 'OFFICIAL_PAGE' for s in entry['product']['sources'])
    # rates are copied, never rewritten
    assert entry['product']['rates'] == [dict(r, evidence_locator=entry['product']['rates'][0]['evidence_locator']) for r in latest[good][1]['product']['rates']]

    batches = []
    for path in sorted(ar.RENEWALS.glob('*/*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict) and 'updates' in data:
            batches.append(data)
    batches.append({'checked_on': TODAY.isoformat(), 'updates': updates, 'holds': []})
    reviews = {e['product_id']: e for e in json.loads(ar.REVIEWS.read_text(encoding='utf-8'))['entries']}
    result = compile_renewals(load_catalog(ar.CATALOG), reviews, batches, TODAY)
    assert result['records'][good]['checked_on'] == TODAY.isoformat()
    assert result['records'][good]['valid_until'] == '2026-11-19'
    assert result['records'][changed]['checked_on'] != TODAY.isoformat()


def test_rates_from_a_document_also_need_a_sale_page_that_lists_the_product():
    latest = ar.latest_entries()
    pid = 'BNK-BUSAN-BIG-SAVINGS'
    product = latest[pid][1]['product']
    modes = {s['url']: s['mode'] for s in product['sources']}
    document = next(u for u, m in modes.items() if m != 'OFFICIAL_PAGE')
    page = next(u for u, m in modes.items() if m == 'OFFICIAL_PAGE')

    def with_listing(url):
        return _page_for(product) if url == document else '상품공시실 목록 ' + '안내 ' * 200 + product['product_name']

    updates, report = ar.evaluate(TODAY, with_listing, {pid})
    assert report[0]['outcome'] == 'RENEWED'
    assert {s['url'] for s in updates[0]['product']['sources']} == {document, page}

    def without_listing(url):
        return _page_for(product) if url == document else '상품공시실 목록 ' + '안내 ' * 200

    updates, report = ar.evaluate(TODAY, without_listing, {pid})
    assert updates == [] and report[0]['outcome'] == 'MISMATCH'
