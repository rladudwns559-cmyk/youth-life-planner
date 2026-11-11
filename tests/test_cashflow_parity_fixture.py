import json

from tools import build_cashflow_parity as parity


def test_browser_parity_fixture_is_exactly_what_python_calculates():
    committed = json.loads(parity.OUTPUT.read_text(encoding='utf-8'))
    assert committed == parity.build(), 'run: python -m tools.build_cashflow_parity'
    assert len(committed['cases']) >= 200
    assert any(c['expected']['disposable_after_policy'] < 0 for c in committed['cases'])
    assert all(c['expected']['policy_benefit_applied'] == 0 for c in committed['cases'])
