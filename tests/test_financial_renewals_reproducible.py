import json
from datetime import date
from pathlib import Path

from backend.finance.discovery import load_catalog
from backend.finance.renewal import compile_renewals

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data/financial-products/discovery-extended-20261103.json'
REVIEWS = ROOT / 'data/financial-products/verified-basic-rates-extended-20261103.json'
COMMITTED = ROOT / 'frontend/src/public-data/financial-renewals.json'


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _batches():
    """Every dated recheck batch (files with an 'updates' list), oldest folder first."""
    found = []
    for path in sorted((ROOT / 'data/financial-products/renewals').glob('*/*.json')):
        data = _read(path)
        if isinstance(data, dict) and 'updates' in data:
            found.append((path, data))
    return found


def test_committed_public_renewals_are_exactly_the_compile_of_the_recorded_batches():
    committed = _read(COMMITTED)
    reviews = {e['product_id']: e for e in _read(REVIEWS)['entries']}
    result = compile_renewals(load_catalog(CATALOG), reviews, [data for _, data in _batches()], date.fromisoformat(committed['built_on']))
    assert json.loads(json.dumps(result)) == committed, 'financial-renewals.json was edited by hand or built from different inputs'


def test_every_recheck_entry_says_what_was_read_and_is_not_a_bare_date_bump():
    for path, batch in _batches():
        for entry in batch['updates']:
            note = entry['evidence_note'].strip()
            assert len(note) >= 40, (path.name, entry['product']['product_id'])
            assert all(s['reviewed_on'] == batch['checked_on'] for s in entry['product']['sources']), (path.name, entry['product']['product_id'])
