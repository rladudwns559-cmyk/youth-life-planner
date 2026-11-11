import json
from datetime import date
from pathlib import Path

import pytest

from tools import fetch_finlife as ff

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'finlife'


def test_offline_build_follows_pages_and_keeps_only_valid_rates(tmp_path):
    out = tmp_path / 'out.json'
    assert ff.main(['--fixture-dir', str(FIXTURES), '--output', str(out), '--today', '2026-11-11']) == 0
    data = json.loads(out.read_text(encoding='utf-8'))
    ids = [p['product_id'] for p in data['products']]
    # page 2 of SAVINGS/020000 was followed; the rate-less product was rejected
    assert ids == ['FSS-DEPOSIT-0020001-DP-C', 'FSS-SAVINGS-0010001-SV-A', 'FSS-SAVINGS-0010002-SV-B']
    assert data['rejected'] == [{'reason': 'NO_VALID_RATE', 'product': ['0010001', 'SV-NORATE'], 'kind': 'SAVINGS', 'group': '020000'}]
    assert data['basis'] == 'DISCLOSURE' and data['fetched_on'] == '2026-11-11'


def test_rates_are_sorted_typed_and_never_invented():
    data = ff.build(lambda kind, group: ff.fetch_pages(kind, group, 'K', _fixture_get), date(2026, 11, 11))
    by_id = {p['product_id']: p for p in data['products']}
    a = by_id['FSS-SAVINGS-0010001-SV-A']
    assert [r['months'] for r in a['rates']] == [6, 12]
    assert a['rates'][1] == {'months': 12, 'rate_type': '단리', 'saving_type': '자유적립식', 'base_rate_percent': 3.5, 'max_rate_percent': 4.2}
    assert a['maximum_krw'] == 500000 and a['join_restriction'] == '제한없음'
    b = by_id['FSS-SAVINGS-0010002-SV-B']
    # a max rate below the base rate is not trusted; an empty limit stays unknown
    assert b['rates'][0]['max_rate_percent'] is None and b['maximum_krw'] is None
    c = by_id['FSS-DEPOSIT-0020001-DP-C']
    assert [r['months'] for r in c['rates']] == [12]  # non-numeric term dropped


def test_api_error_code_stops_the_run():
    def get(url):
        return {'result': {'err_cd': '010', 'err_msg': '미등록 인증키'}}
    with pytest.raises(ff.FinlifeError):
        ff.fetch_pages('SAVINGS', '020000', 'BAD', get)


def test_without_key_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.delenv('FINLIFE_API_KEY', raising=False)
    out = tmp_path / 'out.json'
    assert ff.main(['--output', str(out)]) == 0
    assert not out.exists()


def test_empty_result_keeps_existing_file(tmp_path):
    empty = tmp_path / 'empty'
    empty.mkdir()
    out = tmp_path / 'out.json'
    out.write_text('previous', encoding='utf-8')
    assert ff.main(['--fixture-dir', str(empty), '--output', str(out)]) == 1
    assert out.read_text(encoding='utf-8') == 'previous'


def _fixture_get(url):
    from urllib.parse import parse_qs, urlsplit
    q = parse_qs(urlsplit(url).query)
    kind = 'DEPOSIT' if 'deposit' in url else 'SAVINGS'
    path = FIXTURES / f"{kind}-{q['topFinGrpNo'][0]}-{q['pageNo'][0]}.json"
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'result': {'err_cd': '000', 'max_page_no': 1}}
