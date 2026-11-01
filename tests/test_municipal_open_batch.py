"""Protect explicit intake and district identity for the 2026-11-01 additions."""
from datetime import date
import json
import pytest
from backend.opportunities.current_discovery import ROOT, current_inputs, current_intake


@pytest.mark.parametrize('filename', ['municipal-open-gap-20261101.json','municipal-intakes-20261101.json'])
def test_new_local_notices_have_dated_open_evidence_and_expire(filename):
    catalog, _, evidence = current_inputs()
    path = ROOT / 'data/support-programs' / filename
    new = json.loads(path.read_text(encoding='utf-8'))['programs']
    by_id = {p.program_id: p for p in catalog.programs}
    for item in new:
        program = by_id[item['program_id']]
        assert program.city and len(program.provinces) == 1
        assert evidence[program.program_id]['verified_on'] == '2026-11-01'
        assert current_intake(program, date(2026,11,1), evidence) == 'VERIFIED_OPEN'
        assert current_intake(program, date(2026,11,9), evidence) != 'VERIFIED_OPEN'
        assert program.eligibility == 'UNKNOWN' and program.benefit_applied_krw == 0

