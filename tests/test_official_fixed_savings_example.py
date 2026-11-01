"""M3.4 공식 예시의 수치 일치와 실제 상품 적용 불승인을 분리한다. 신규 계산/API 없음."""
import json
from datetime import date
from decimal import Decimal,ROUND_DOWN
from pathlib import Path
import pytest
from backend.finance import products,recurring

REVIEW=Path(__file__).resolve().parents[1]/'data/financial-products/research/ibk-fixed-review-v1.json'

def review():return json.loads(REVIEW.read_text(encoding='utf-8'))

def facts():return {item['field']:item for item in review()['facts']}

def candidate_projection():
    # 검증용 투영일 뿐 서비스 Source/카탈로그/상품 등록이 아니다.
    f=facts();ranges=f['contract_months']['value']
    return products.ProductSnapshot(
      product_id='IBK-FIXED-0001-REVIEW-ONLY',snapshot_version='1.0.0',product_name='정기적금 [정액적금] 검증 전용',institution='IBK기업은행',product_type='RECURRING_SAVINGS',
      source_id='RESEARCH-ONLY',evidence_locator='설명서1~4쪽 및 적립식예금약관제3~4조',basis_date='2026-09-07',collected_on='2026-10-25',verified_on='2026-10-25',
      official_material_status='CONFIRMED',key_fields_status='PARTIAL',subscription_status='UNCONFIRMED',target='사용자 자격 미검증',term_description='1~72개월;3년 초과시 금리 변동',
      minimum_monthly_payment=f['minimum_monthly_payment']['value'],maximum_monthly_payment=f['maximum_monthly_payment']['value'],payment_step=f['manual_payment_step']['value'],
      rate_options=(products.RateBand(min_months=ranges['min'],max_months=ranges['max'],base_rate_percent=None,max_total_rate_percent=None,evidence_locator='현재금리미확인;과거설명서/예시와분리'),),
      max_preferential_bonus_percentage_points=None,preferential_conditions=(),accumulation_method='FIXED_MONTHLY',rate_type='UNKNOWN',interest_method='SIMPLE',
      deposit_timing='ACTUAL_DATE',date_basis='ACTUAL_DAYS',rounding_method='OTHER',calculation_evidence_locator='설명서2쪽:실제일수/365·합산후절사',enrollment_method=None,
      product_detail_url=review()['candidate']['product_url'],unknown_fields=tuple(k for k,v in f.items() if v['status']=='UNKNOWN'),cross_check_notes=('M3.2 월수/반올림과 불일치',))

def test_official_example_matches_existing_function_without_approval():
    example=review()['official_example']
    result=recurring.calculate_recurring_savings(recurring.RecurringSavingsInput(example['monthly_payment_krw'],example['term_months'],Decimal(example['annual_rate_percent'])))
    assert result.estimated_interest_before_tax_krw==example['official_interest_before_tax_krw']==78000
    assert result.total_principal_krw==6000000 and result.estimated_maturity_before_tax_krw==6078000
    assert Decimal(result.unrounded_interest_krw)==Decimal('78000')
    assert review()['decision']['personalized_calculation_approved'] is False

def test_four_verification_results_remain_independent():
    assert review()['independent_results']==dict(official_example_numerically_reproduced=True,full_contract_matches_m32=False,current_rate_verified=False,user_conditions_verified=False)
    assert review()['decision']['compatibility_case']=='C'
    assert review()['decision']['verdict']=='M3_OFFICIAL_SAVINGS_CALCULATION_BLOCKED'

def test_source_links_dates_hashes_and_facts_have_locators():
    r=review();sources={s['source_id']:s for s in r['sources']}
    assert len(sources)==4
    assert sources['DESCRIPTION']['document_as_of']=='2026-09-07'
    assert sources['DESCRIPTION']['sha256']=='264dc55beb91b868feabd903d219061e399fb8248e1477139493cb68fefee087'
    assert sources['INSTALLMENT-TERMS']['document_as_of'] is None
    for item in r['facts']:
        assert item['source_id'] in sources and item['locator']
        assert sources[item['source_id']]['official_url'].startswith('https://')

def test_fixed_monthly_identification_is_not_sufficient():
    p=candidate_projection();assert p.accumulation_method=='FIXED_MONTHLY'
    codes=products.compatibility_reasons(p,date(2026,10,25))
    assert 'ACCUMULATION_UNSUPPORTED' not in codes
    assert {'DAY_BASIS_UNSUPPORTED','ROUNDING_UNVERIFIED','TIMING_UNSUPPORTED'}<=set(codes)

def test_published_rate_example_and_current_rate_are_not_merged():
    f=facts();example=review()['official_example']
    assert f['base_rate']['value']==dict(percent='2.40',min_months=12,max_months=23,as_of='2026-09-07')
    assert example['rate_kind']=='ILLUSTRATIVE_NOT_VERIFIED_CURRENT_RATE'
    assert f['current_base_rate']['status']=='UNKNOWN' and f['current_base_rate']['value'] is None
    assert f['preferential_rate']['value'] is None  # 우대 없음(0)으로 바꾸지 않는다.

@pytest.mark.parametrize('months,mismatch',[(0,True),(1,False),(72,False),(73,True)])
def test_published_term_boundaries_do_not_authorize_calculation(months,mismatch):
    result=products.evaluate_product(candidate_projection(),500000,months,date(2026,10,25))
    assert ('TERM_MISMATCH' in result['reason_codes']) is mismatch
    assert result['calculation'] is None

@pytest.mark.parametrize('amount,below',[(9999,True),(10000,False),(500000,False)])
def test_minimum_won_step_and_unknown_maximum(amount,below):
    result=products.evaluate_product(candidate_projection(),amount,12,date(2026,10,25))
    assert ('BELOW_MINIMUM' in result['reason_codes']) is below
    assert 'LIMITS_UNKNOWN' in result['reason_codes']
    assert candidate_projection().maximum_monthly_payment is None
    assert candidate_projection().payment_step==1

def test_calendar_leap_and_intermediate_precision_are_not_invented():
    f=facts()
    assert f['day_count_basis']['value']=='ACTUAL_DAYS_DENOMINATOR_365'
    assert f['whole_interest_won_treatment']['value']=='SUM_THEN_TRUNCATE_KRW'
    for key in ('first_installment_date','last_installment_date','initial_maturity_date','leap_year_special_rule','installment_intermediate_rounding'):
        assert f[key]['status']=='UNKNOWN' and f[key]['value'] is None
    assert '다음 영업일' in f['holiday_payment']['value'] and '만기 이연' in f['late_payment']['value']

def test_integer_example_cannot_prove_won_treatment_equivalence():
    # 합성 산술 반례다. 아래 수치를 은행이 지급할 이자라고 주장하지 않는다.
    r=recurring.calculate_recurring_savings(recurring.RecurringSavingsInput(10025,12,Decimal('2.40')))
    assert Decimal(r.unrounded_interest_krw)==Decimal('1563.9')
    assert r.estimated_interest_before_tax_krw==1564
    assert int(Decimal(r.unrounded_interest_krw).to_integral_value(rounding=ROUND_DOWN))==1563

def test_actual_days_and_truncation_still_block_even_if_unknowns_are_cleared(monkeypatch):
    def forbidden(*args):raise AssertionError('C mismatch must not reach M3.2')
    monkeypatch.setattr(recurring,'calculate_recurring_savings',forbidden)
    p=candidate_projection().model_copy(update=dict(key_fields_status='VERIFIED',subscription_status='OPEN_AS_OF_SOURCE',rate_type='FIXED',maximum_monthly_payment=1000000,
      rate_options=(products.RateBand(min_months=12,max_months=12,base_rate_percent='2.40',max_total_rate_percent=None,evidence_locator='합성조건보완시험'),)))
    result=products.evaluate_product(p,500000,12,date(2026,10,25))
    assert {'DAY_BASIS_UNSUPPORTED','ROUNDING_UNVERIFIED'}<=set(result['reason_codes']) and result['calculation'] is None

@pytest.mark.parametrize('change,code',[
 (dict(calculation_evidence_locator=None),'CALCULATION_EVIDENCE_MISSING'),
 (dict(key_fields_status='CONFLICT'),'SOURCE_CONFLICT'),
 (dict(subscription_status='UNCONFIRMED'),'SUBSCRIPTION_UNCONFIRMED')])
def test_missing_or_conflicting_evidence_cannot_enable_calculation(change,code):
    result=products.evaluate_product(candidate_projection().model_copy(update=change),500000,12,date(2026,10,25))
    assert code in result['reason_codes'] and result['calculation'] is None

def test_research_record_is_not_a_service_snapshot_and_existing_three_stay_blocked(monkeypatch):
    def forbidden(*args):raise AssertionError('existing real snapshots must not calculate')
    monkeypatch.setattr(recurring,'calculate_recurring_savings',forbidden)
    catalog=products.load_catalog()
    assert len(catalog.products)==3
    assert candidate_projection().product_id not in {p.product_id for p in catalog.products}
    assert review()['scope']=='RESEARCH_ONLY_NOT_SERVICE_CATALOG'
    assert review()['decision']['served_in_catalog'] is False
    for p in catalog.products:
        assert products.evaluate_product(p,500000,12,date(2026,10,25))['calculation'] is None
