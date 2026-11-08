import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.opportunities.catalog import load_catalog
from tools.build_asset_programs_public import (CHANGED_NOTE, PUBLIC_DISCLAIMER, STALE_TO_REVIEW, apply_verification, attach_rates,
                                               build, flagged_programs, public_intake)

ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9))
VERIFICATION = json.loads((ROOT / 'data/asset-programs/verification-20261108.json').read_text(encoding='utf-8'))
SOURCE_CHECK = json.loads((ROOT / 'data/asset-programs/source-check-20261108.json').read_text(encoding='utf-8'))
RATES = json.loads((ROOT / 'data/asset-programs/rates-20261108.json').read_text(encoding='utf-8'))
PUBLIC = json.loads((ROOT / 'frontend/src/public-data/asset-programs-public.json').read_text(encoding='utf-8'))


def noon(d):
    return datetime(d.year, d.month, d.day, 12, 0, tzinfo=KST)


def test_committed_public_file_is_the_build_of_its_recorded_inputs():
    catalog = apply_verification(load_catalog(), VERIFICATION)
    flagged = flagged_programs(catalog, SOURCE_CHECK, VERIFICATION)
    start = date.fromisoformat(PUBLIC['built_on'])
    rebuilt = attach_rates(build(catalog, start, len(PUBLIC['schedules']) - 1, flagged), catalog, RATES)
    assert rebuilt['schedules'] == PUBLIC['schedules']
    assert [r['intake'] for r in rebuilt['programs']] == [r['intake'] for r in PUBLIC['programs']]
    assert [r.get('rate') for r in rebuilt['programs']] == [r.get('rate') for r in PUBLIC['programs']]


def _built():
    catalog = apply_verification(load_catalog(), VERIFICATION)
    return catalog, build(catalog, date(2026, 11, 8), 1, set())


def _rates(**changes):
    entry = dict(RATES['rates'][0], **changes)
    return dict(RATES, rates=[entry])


def test_only_the_verified_program_carries_a_rate_and_it_keeps_base_and_preferential_separate():
    rated = {r['program']['program_id']: r['rate'] for r in PUBLIC['programs'] if 'rate' in r}
    assert list(rated) == ['KR-YOUTH-FUTURE']
    rate = rated['KR-YOUTH-FUTURE']
    assert rate['base_percent'] == '5' and rate['preferential_label'] == '우대 최대 2~3%' and rate['verified_on'] == '2026-11-08'
    assert set(rate) == {'base_percent', 'term_label', 'preferential_label', 'source_id', 'verified_on'}  # no yield, no maturity amount
    assert '기여금' not in json.dumps(rate, ensure_ascii=False) and '13.2' not in json.dumps(rate, ensure_ascii=False)


def test_rate_is_rejected_unless_its_source_was_read_on_the_check_date():
    catalog, data = _built()
    with pytest.raises(ValueError, match='RATE_SOURCE_NOT_VERIFIED_ON_CHECK_DATE'):  # unread source keeps its 10/30 date
        attach_rates(build(load_catalog(), date(2026, 11, 8), 1, set()), load_catalog(), RATES)
    with pytest.raises(ValueError, match='RATE_SOURCE_NOT_LINKED_TO_PROGRAM'):
        attach_rates(data, catalog, _rates(source_id='seoul'))
    with pytest.raises(ValueError, match='UNKNOWN_OR_DUPLICATE_RATE_PROGRAM'):
        attach_rates(data, catalog, _rates(program_id='NOPE'))
    dup = dict(RATES, rates=[RATES['rates'][0], RATES['rates'][0]])
    with pytest.raises(ValueError, match='UNKNOWN_OR_DUPLICATE_RATE_PROGRAM'):
        attach_rates(data, catalog, dup)


@pytest.mark.parametrize('value', ['abc', '-1', '101', 'NaN', 'Infinity'])
def test_rate_value_must_be_a_finite_percentage(value):
    catalog, data = _built()
    with pytest.raises(ValueError, match='INVALID_RATE'):
        attach_rates(data, catalog, _rates(base_percent=value))


def test_rate_needs_evidence_and_a_term_label():
    catalog, data = _built()
    with pytest.raises(ValueError, match='RATE_EVIDENCE_REQUIRED'):
        attach_rates(data, catalog, _rates(evidence=' '))
    with pytest.raises(ValueError, match='RATE_TERM_REQUIRED'):
        attach_rates(data, catalog, _rates(term_label=''))


def test_no_rates_file_changes_nothing():
    catalog, data = _built()
    assert attach_rates(data, catalog, None) is data and not any('rate' in r for r in data['programs'])


def test_overlay_changes_only_listed_sources_and_never_the_original_catalog():
    original = load_catalog()
    before = {s.source_id: s.verified_on for s in original.sources}
    updated = apply_verification(original, VERIFICATION)
    listed = {e['source_id'] for e in VERIFICATION['sources']}
    assert {s.source_id: s.verified_on for s in original.sources} == before
    for s in updated.sources:
        assert s.verified_on == (VERIFICATION['checked_on'] if s.source_id in listed else before[s.source_id])


def test_overlay_rejects_unknown_source_future_date_and_missing_evidence():
    catalog = load_catalog()
    ok = dict(source_id='future', verified_on='2026-11-08', evidence='read')
    with pytest.raises(ValueError, match='UNKNOWN_SOURCE_ID'):
        apply_verification(catalog, dict(checked_on='2026-11-08', sources=[dict(ok, source_id='nope')]))
    with pytest.raises(ValueError, match='VERIFIED_AFTER_CHECK_DATE'):
        apply_verification(catalog, dict(checked_on='2026-11-08', sources=[dict(ok, verified_on='2026-11-09')]))
    with pytest.raises(ValueError, match='VERIFICATION_EVIDENCE_REQUIRED'):
        apply_verification(catalog, dict(checked_on='2026-11-08', sources=[dict(ok, evidence=' ')]))


def test_changed_sources_flag_programs_unless_a_person_read_them():
    catalog = load_catalog()
    flagged = flagged_programs(catalog, SOURCE_CHECK, VERIFICATION)
    changed = {s['source_id'] for s in SOURCE_CHECK['sources'] if s['result'] != 'UNCHANGED_BYTES'}
    read = {e['source_id'] for e in VERIFICATION['sources']}
    expected = {p.program_id for p in catalog.programs if (changed - read) & set(p.source_ids)}
    assert flagged == expected and 'GG-YOUTH-WORKER' in flagged
    assert 'KR-YOUTH-FUTURE' not in flagged  # changed bytes, but read and confirmed
    assert flagged_programs(catalog, None, VERIFICATION) == set()


def test_flagged_program_is_never_fresh_and_keeps_the_review_note():
    catalog = apply_verification(load_catalog(), VERIFICATION)
    program = next(p for p in catalog.programs if p.program_id == 'GG-YOUTH-WORKER')
    row = public_intake(program, catalog, noon(date(2026, 11, 8)), {'GG-YOUTH-WORKER'})
    assert row['fresh'] is False and CHANGED_NOTE.strip() in row['note']
    assert public_intake(program, catalog, noon(date(2026, 11, 8)), {'GG-YOUTH-WORKER'})['note'].count(CHANGED_NOTE.strip()) == 1


def test_a_stale_open_status_can_never_appear_in_any_day_of_the_table():
    catalog = apply_verification(load_catalog(), VERIFICATION)
    for day, entries in PUBLIC['schedules'].items():
        for pid, e in entries.items():
            if not e['fresh']:
                assert e['status'] not in STALE_TO_REVIEW, (day, pid)


def test_freshness_expires_seven_days_after_the_manual_verification():
    entries = PUBLIC['schedules']
    verified = date.fromisoformat(VERIFICATION['checked_on'])
    assert entries[(verified + timedelta(days=7)).isoformat()]['KR-YOUTH-FUTURE']['fresh'] is True
    assert entries[(verified + timedelta(days=8)).isoformat()]['KR-YOUTH-FUTURE']['fresh'] is False


def test_public_snapshot_keeps_the_no_money_no_calculation_contract():
    assert PUBLIC['policy_benefit_applied_krw'] == 0 and PUBLIC['actual_product_calculation_count'] == 0
    assert all(r['calculation'] is None and r['benefit_applied_krw'] == 0 for r in PUBLIC['programs'])
    assert PUBLIC['disclaimer'].endswith(PUBLIC_DISCLAIMER)
    assert sum(PUBLIC['counts'].values()) == PUBLIC['program_count'] == len(PUBLIC['programs'])
