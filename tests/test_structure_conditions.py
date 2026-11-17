import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from structure_conditions import age_from, employment_from  # noqa: E402
from backend.opportunities.personal_discovery import AgeRule, Rules, age_match  # noqa: E402
from backend.opportunities.current_discovery import apply_structured_conditions, STRUCTURED  # noqa: E402

DAY = date(2026, 11, 16)


def test_one_clear_range_becomes_a_rule_with_a_margin():
    age, why = age_from('강남구 거주 만 19~39세 미취업 청년입니다.')
    assert age == {'kind': 'CURRENT', 'minimum': 19, 'maximum': 39, 'older_exception': False, 'age_margin': 1} and why == 'age range'
    age, _ = age_from('공식 2026년 기준 19~39세(1986~2007년생). 시험 응시일 기준 미취업.')
    assert age['kind'] == 'BIRTH_RANGE' and (age['birth_start'], age['birth_end']) == ('1986-01-01', '2007-12-31')
    age, _ = age_from('공식 지원대상은 경남 주소18~39세, 1986~2008년생(고교졸업예정자 포함).')
    assert age['age_margin'] == 2
    age, _ = age_from('서울 거주 만19~39세, 제대군인은 최대42세까지 가능.')
    assert age['older_exception'] and age['older_exception_years'] == 3


def test_preferences_other_peoples_ages_and_mixed_ranges_stay_unknown():
    assert age_from('센터는 만 18~45세 청년을 우선 선발한다고 안내합니다. 우선 대상 밖이라는 이유로 제외하지 않습니다.')[0] is None
    assert age_from('부부 중 1명 이상이 19~39세인 무주택 청년 신혼부부')[0] is None
    assert age_from('청년 구간은 19~39세입니다. 신혼부부도 별도 소득조건으로 대상이므로 나이만으로 사업 전체를 제외하지 않습니다.')[0] is None
    assert age_from('일반 21~24세, 제대군인 25~27세')[0] is None
    assert age_from('나이 조건이 적혀 있지 않습니다.')[0] is None


def test_employment_only_when_the_wording_says_unemployed_without_exceptions():
    assert employment_from('충주 거주 19~39세 미취업 청년 대상입니다.')[0] == {'employed': 'FAIL', 'unemployed': 'PASS', 'self_employed': 'UNKNOWN'}
    assert employment_from('천안 청년. 미취업자, 졸업예정자, 이직예정자 순으로 선정 우선순위가 있습니다.')[0] is None
    assert employment_from('19~39세 미취업 청년입니다. 대학생과 1년 미만 비정규직 예외가 있습니다.')[0] is None
    assert employment_from('미취업 청년. 주 30시간 이하 아르바이트는 예외 심사')[0] is None


def test_margin_keeps_the_year_outside_the_range_as_check_needed():
    current = AgeRule(kind='CURRENT', minimum=19, maximum=39, age_margin=1, note='x')
    assert [age_match(current, a, DAY) for a in (17, 18, 19, 39, 40, 41)] == ['FAIL', 'UNKNOWN', 'PASS', 'PASS', 'UNKNOWN', 'FAIL']
    birth = AgeRule(kind='BIRTH_RANGE', birth_start='1986-01-01', birth_end='2007-12-31', age_margin=1, note='x')
    assert age_match(birth, 25, DAY) == 'PASS'
    assert age_match(birth, 17, DAY) == 'UNKNOWN'   # born 2008-2009, one year after the range
    assert age_match(birth, 15, DAY) == 'FAIL'
    assert age_match(birth, 41, DAY) == 'UNKNOWN'   # born 1984-1985, within a year before the range
    assert age_match(birth, 43, DAY) == 'FAIL'


def test_structured_conditions_never_replace_a_hand_set_rule():
    src = [{'url': 'https://www.example.go.kr/a', 'title': 't', 'basis_date': None, 'verified_on': '2026-11-01', 'evidence': 'OFFICIAL_PAGE', 'locator': 'l'}]
    hand = {'program_id': 'A', 'sources': src, 'age': {'kind': 'CURRENT', 'minimum': 20, 'maximum': 30, 'note': '수동'},
            'employed': 'PASS', 'employment_note': 'n', 'rent_note': 'n'}
    base = json.loads((ROOT / 'data/support-programs/personal-rules-20261101.json').read_text(encoding='utf-8'))
    rules = Rules.model_validate({**base, 'rules': [hand]})
    records = {'A': {'sources': src, 'age_note': 'a'}, 'B': {'sources': src, 'age_note': '만 19~39세'}}
    structured = {'conditions': [
        {'program_id': 'A', 'age': {'kind': 'CURRENT', 'minimum': 19, 'maximum': 39, 'age_margin': 1, 'note': 'x'},
         'employment': {'employed': 'FAIL', 'unemployed': 'PASS', 'self_employed': 'UNKNOWN'}},
        {'program_id': 'B', 'age': {'kind': 'CURRENT', 'minimum': 19, 'maximum': 39, 'age_margin': 1, 'note': '만 19~39세'}},
    ]}
    out = {r.program_id: r for r in apply_structured_conditions(rules, records, structured).rules}
    assert (out['A'].age.minimum, out['A'].age.maximum, out['A'].employed) == (20, 30, 'PASS')
    assert (out['B'].age.minimum, out['B'].age.age_margin, out['B'].employed) == (19, 1, 'UNKNOWN')


def test_the_stored_file_only_names_known_open_style_programs():
    data = json.loads(STRUCTURED.read_text(encoding='utf-8'))
    ids = [c['program_id'] for c in data['conditions']]
    assert len(ids) == len(set(ids)) and len(ids) > 50
    for c in data['conditions']:
        if 'age' in c:
            AgeRule.model_validate(c['age'])
            assert c['age']['age_margin'] >= 1


def test_conditions_read_on_official_pages_keep_the_quote():
    from backend.opportunities.current_discovery import VERIFIED_CONDITIONS
    data = json.loads(VERIFIED_CONDITIONS.read_text(encoding='utf-8'))
    assert data['checked_on'] == '2026-11-17'
    for c in data['conditions']:
        AgeRule.model_validate(c['age'])
        assert '공식 상세(2026-11-17 확인)' in c['age']['note'] and '"' in c['age']['note']
