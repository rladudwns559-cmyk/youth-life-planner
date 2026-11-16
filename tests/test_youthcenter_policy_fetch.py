import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from youthcenter_policy_fetch import schools, marriage, organisation, optional, age_range, apply_period, income, jobs, normalise, regions, write_if_changed  # noqa: E402

CODES = json.loads((ROOT / 'data/region-codes/sigungu.json').read_text(encoding='utf-8'))['codes']
CITIES = json.loads((ROOT / 'frontend/src/public-data/nationwide-districts.json').read_text(encoding='utf-8'))['cities']
JEONNAM = '12110,12130,12150,12170,12190,12710,12720,12730,12740,12750,12760,12770,12780,12790,12800,12810,12820,12830,12840,12850,12860,12870'


def policy(**kw):
    base = dict(plcyNo='P1', plcyNm='2026년 테스트 청년 월세 지원', plcyAprvSttsCd='0044002', lclsfNm='주거', mclsfNm='주거비 지원',
                sprvsnInstCdNm='안산시', plcySprtCn='월 20만원\n최대 12개월', plcyExplnCn='설명', zipCd='41271,41273',
                sprtTrgtMinAge='19', sprtTrgtMaxAge='34', sprtTrgtAgeLmtYn='Y', jobCd='0013010', earnCndSeCd='0043001',
                aplyPrdSeCd='0057001', aplyYmd='20261102 ~ 20261211', bizPrdSeCd='0056002', bizPrdEndYmd='        ',
                aplyUrlAddr='', refUrlAddr1='https://www.ansan.go.kr/x', addAplyQlfcCndCn='', lastMdfcnDt='2026-11-13 09:30:29')
    base.update(kw)
    return base


def test_code_table_covers_current_and_retired_codes():
    assert CODES['41273'] == [['경기', '안산시 단원구']]
    assert CODES['12000'] == [['광주', ''], ['전남', '']]
    assert CODES['29200'] == [['광주', '광산구']] and CODES['46110'] == [['전남', '목포시']]
    assert CODES['42730'] == CODES['51730'] == [['강원', '횡성군']]
    assert CODES['47720'] == [['대구', '군위군']]


def test_regions_compact_to_province_or_nationwide():
    assert regions(policy(), CODES, CITIES) == (['경기|안산시 단원구', '경기|안산시 상록구'], [])
    assert regions(policy(zipCd=JEONNAM), CODES, CITIES)[0] == ['전남']
    everything = ','.join(CODES)
    assert regions(policy(zipCd=everything), CODES, CITIES)[0] == ['*']
    assert regions(policy(zipCd='41271,99999'), CODES, CITIES) == (['경기|안산시 상록구'], ['99999'])
    assert regions(policy(zipCd=''), CODES, CITIES) == ([], [])


def test_age_jobs_income_and_period():
    assert age_range(policy()) == [19, 34]
    assert age_range(policy(sprtTrgtMinAge='0', sprtTrgtMaxAge='0')) is None
    assert age_range(policy(sprtTrgtAgeLmtYn='N')) is None
    assert age_range(policy(sprtTrgtMinAge='19', sprtTrgtMaxAge='0')) == [19, None]
    assert jobs(policy()) is None
    assert jobs(policy(jobCd='0013003')) == {'groups': ['unemployed'], 'other': False}
    assert jobs(policy(jobCd='0013001,0013009')) == {'groups': ['employed'], 'other': True}
    assert income(policy()) is None
    assert income(policy(earnCndSeCd='0043002', earnMinAmt='0', earnMaxAmt='5000')) == '연소득 5000만원 이하'
    assert income(policy(earnCndSeCd='0043003', earnEtcCn='기준 중위소득 150% 이하')) == '기준 중위소득 150% 이하'
    assert apply_period(policy()) == {'mode': 'PERIOD', 'start': '2026-11-02', 'end': '2026-12-11'}
    assert apply_period(policy(aplyPrdSeCd='0057002', aplyYmd='')) == {'mode': 'ALWAYS'}
    assert apply_period(policy(aplyYmd='')) == {'mode': 'OTHER'}


def test_normalise_keeps_open_approved_policies_with_links():
    rows = [policy(), policy(), policy(plcyNo='P2', aplyYmd='20260101 ~ 20260301'), policy(plcyNo='P3', plcyAprvSttsCd='0044001'),
            policy(plcyNo='P4', bizPrdSeCd='0056001', bizPrdEndYmd='20261031'), policy(plcyNo='P5', zipCd='')]
    out, stats = normalise(rows, CODES, CITIES, '2026-11-16')
    assert [p['id'] for p in out] == ['P1']
    assert stats['closed'] == 2 and stats['not_approved'] == 1 and stats['no_region'] == 1
    p = out[0]
    assert p['url'] == 'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/P1'
    assert p['apply_url'] == 'https://www.ansan.go.kr/x'
    assert p['summary'] == '월 20만원 최대 12개월'
    assert p['updated'] == '2026-11-13' and p['org'] == '안산시' and p['extra'] is None


def test_write_only_when_policies_change(tmp_path):
    out = tmp_path / 'p.json'
    policies, _ = normalise([policy()], CODES, CITIES, '2026-11-16')
    assert write_if_changed(out, policies, '2026-11-16') is True
    assert write_if_changed(out, policies, '2026-11-17') is False
    data = json.loads(out.read_text(encoding='utf-8'))
    assert data['fetched_on'] == '2026-11-16' and data['source']['attribution'] == '출처: 온통청년(한국고용정보원)'


def test_department_names_get_their_body_and_empty_notes_are_dropped():
    assert organisation(policy(sprvsnInstCdNm='건강증진과', rgtrUpInstCdNm='충청남도 태안군')) == '충청남도 태안군 건강증진과'
    assert organisation(policy(sprvsnInstCdNm='안산시', rgtrUpInstCdNm='경기도')) == '안산시'
    assert optional('해당없음', 50) is None and optional('-', 50) is None
    assert optional('관내 거주 6개월 이상', 50) == '관내 거주 6개월 이상'


def test_province_missing_a_new_district_counts_as_whole():
    incheon_old = '28710,28290,28245,28200,28177,28237,28185,28720,28125'  # no 서해구 28275, 영종구 28155
    assert regions(policy(zipCd=incheon_old), CODES, CITIES)[0] == ['인천']
    # Small provinces stay strict: 울산 without 울주군 is not the whole of 울산.
    assert regions(policy(zipCd='31110,31140,31170,31200'), CODES, CITIES)[0] == ['울산|남구', '울산|동구', '울산|북구', '울산|중구']
    # Missing three of 인천's cities is a partial list.
    assert regions(policy(zipCd='28710,28290,28245,28200,28177,28237,28185,28720'), CODES, CITIES)[0][0].startswith('인천|')


def test_department_name_that_already_names_its_body_is_not_doubled():
    assert organisation(policy(sprvsnInstCdNm='전남광주통합특별시 화순군 인구청년정책과', rgtrUpInstCdNm='전남광주통합특별시 화순군')) == '전남광주통합특별시 화순군 인구청년정책과'


def test_schooling_and_marriage_codes():
    assert schools(policy()) is None
    assert schools(policy(schoolCd='0049010')) is None
    assert schools(policy(schoolCd='0049005,0049006')) == {'groups': ['univ_expected', 'univ_student'], 'other': False}
    assert schools(policy(schoolCd='0049002,0049003,0049009')) == {'groups': ['hs_student'], 'other': True}
    assert marriage(policy()) is None
    assert marriage(policy(mrgSttsCd='0055003')) is None
    assert marriage(policy(mrgSttsCd='0055001')) == 'married'
    assert marriage(policy(mrgSttsCd='0055002')) == 'single'
    out, _ = normalise([policy(schoolCd='0049007', mrgSttsCd='0055001')], CODES, CITIES, '2026-11-16')
    assert out[0]['school'] == {'groups': ['univ_grad'], 'other': False} and out[0]['marriage'] == 'married'
