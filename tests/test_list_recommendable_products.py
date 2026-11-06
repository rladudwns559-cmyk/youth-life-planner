from tools.list_recommendable_products import recommendable, to_markdown


def _product(pid, schedule='MONTHLY', maximum_kind='KNOWN'):
    return dict(product_id=pid, institution='테스트은행', product_name=pid, kind='SAVINGS', schedule=schedule,
                maximum_kind=maximum_kind, sources=[dict(url=f'https://example.test/{pid}', mode='OFFICIAL_PAGE')])


def _data():
    records = {
        'OK': dict(status='CURRENT', checked_on='2026-11-07', valid_until='2026-11-14', product=_product('OK')),
        'UNKNOWN-CAP': dict(status='CURRENT', checked_on='2026-11-07', valid_until='2026-11-14', product=_product('UNKNOWN-CAP', maximum_kind='UNKNOWN')),
        'DAILY': dict(status='CURRENT', checked_on='2026-11-07', valid_until='2026-11-14', product=_product('DAILY', schedule='DAILY')),
        'HELD': dict(status='UNCONFIRMED', checked_on='2026-11-07', valid_until=None, product=_product('HELD')),
        'NO-RATE': dict(status='CURRENT', checked_on='2026-11-07', valid_until='2026-11-14', product=_product('NO-RATE')),
    }
    rates = {pid: {'12': {}} for pid in ('OK', 'UNKNOWN-CAP', 'DAILY', 'HELD')}
    return dict(records=records, recommendations=dict(rate_by_product=rates))


def test_only_current_rate_verified_capped_monthly_or_lump_products_are_listed():
    assert [r['product_id'] for r in recommendable(_data())] == ['OK']


def test_listing_is_read_only_and_reports_deadline():
    data = _data()
    before = repr(data)
    rows = recommendable(data)
    assert repr(data) == before
    assert rows[0]['valid_until'] == '2026-11-14'
    assert '`OK`' in to_markdown(rows) and '기한 2026-11-14' in to_markdown(rows)
