from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.finance import savings_matching as core
from backend.web import savings_matching as web
from backend.web.app import app

DAY=date(2026,10,30)
PROFILE=dict(age=24,region='안산시',student_status=True,employment_status='employed',monthly_income=1500000,
             monthly_rent=450000,monthly_fixed_expenses=200000,other_monthly_expenses=350000,user_savings_capacity=300000)
IDS={'KAKAO-FREE-SAVINGS','KBANK-CODEK-SAVINGS','KBANK-PRIMARY-SAVINGS','TOSS-FREE-SAVINGS'}
client=TestClient(app)

@pytest.fixture
def catalog():return core.load_matching_catalog()

def changed(catalog,mutate):
    data=catalog.model_dump(mode='json');mutate(data)
    return core.MatchingCatalog.model_validate_json(json.dumps(data,ensure_ascii=False))

def ids(result):return {r['product']['product_id'] for r in result['matches']}

def test_official_dataset_is_three_banks_four_products_and_old_catalog_unchanged(catalog):
    assert len(catalog.products)==4
    assert {p.bank_id for p in catalog.products}=={'KAKAO','KBANK','TOSS'}
    from backend.finance import products
    assert len(products.load_catalog().products)==3
    assert all(p.calculation_status=='NOT_VERIFIED' for p in catalog.products)

@pytest.mark.parametrize('amount,count',[(0,0),(1,1),(999,1),(1000,4),(300000,4),(300001,3),(3000000,3),(3000001,0),(1000000000000,0)])
def test_monthly_bounds_are_inclusive_and_full_amount_is_not_capped(catalog,amount,count):
    result=core.match_savings(catalog,amount,12,DAY)
    assert result['matched_count']==count
    assert result['monthly_amount']==amount
    assert result['total_count']==4
    assert result['matched_count']+result['excluded_count']+result['review_count']==4

@pytest.mark.parametrize('months,expected',[(1,{'KBANK-CODEK-SAVINGS'}),(2,set()),(3,{'KBANK-CODEK-SAVINGS','TOSS-FREE-SAVINGS'}),
    (5,{'TOSS-FREE-SAVINGS'}),(6,IDS),(12,IDS),(18,IDS-{'KBANK-CODEK-SAVINGS'}),(24,IDS),(36,IDS),(37,set()),(120,set())])
def test_term_boundaries_and_discrete_terms(catalog,months,expected):
    assert ids(core.match_savings(catalog,300000,months,DAY))==expected

@pytest.mark.parametrize('amount,months',[(True,12),(-1,12),('300000',12),(1.5,12),(1000,True),(1000,0),(1000,121),(1000,'12')])
def test_pure_function_rejects_invalid_context(catalog,amount,months):
    with pytest.raises(ValueError):core.match_savings(catalog,amount,months,DAY)

def test_verified_age_window_and_future_dates(catalog):
    assert len(core.match_savings(catalog,300000,12,date(2026,11,6))['matches'])==4
    stale=core.match_savings(catalog,300000,12,date(2026,11,7))
    assert stale['matched_count']==0 and stale['review_count']==4
    assert all('SOURCE_REVIEW_REQUIRED' in r['reason_codes'] for r in stale['review_required'])
    future=core.match_savings(catalog,300000,12,date(2026,10,29))
    assert future['matched_count']==0 and future['review_count']==4

@pytest.mark.parametrize('field',['minimum_monthly_payment','maximum_monthly_payment','min_months','max_months'])
def test_missing_essential_condition_is_review_not_match(catalog,field):
    candidate=changed(catalog,lambda d:d['products'][0].__setitem__(field,None))
    result=core.match_savings(candidate,300000,12,DAY)
    assert 'KAKAO-FREE-SAVINGS' not in ids(result)
    assert result['review_count']==1

def test_unknown_rate_is_not_zero_and_does_not_claim_interest(catalog):
    def mutate(d):
        d['products'][0]['rate_options'][1]['base_rate_percent']=None
        d['products'][0]['rate_options'][1]['max_total_rate_percent']=None
    result=core.match_savings(changed(catalog,mutate),300000,12,DAY)
    row=next(r for r in result['matches'] if r['product']['product_id']=='KAKAO-FREE-SAVINGS')
    assert row['selected_base_rate_percent'] is None and row['selected_max_rate_percent'] is None
    assert row['calculation'] is None and row['user_eligibility']=='NOT_EVALUATED'

def test_recorded_payment_step_and_publication_are_respected(catalog):
    data=changed(catalog,lambda d:d['products'][1].__setitem__('payment_step',1000))
    row=next(r for r in core.match_savings(data,1001,12,DAY)['excluded'] if r['product']['product_id']=='KBANK-CODEK-SAVINGS')
    assert 'PAYMENT_STEP_MISMATCH' in row['reason_codes']
    data=changed(catalog,lambda d:d['products'][0].__setitem__('publication_status','WITHDRAWN'))
    assert core.match_savings(data,300000,12,DAY)['review_count']==1

def test_no_input_mutation_no_rate_ranking_no_calculation(catalog):
    before=catalog.model_dump_json()
    first=core.match_savings(catalog,300000,12,DAY)
    assert first==core.match_savings(catalog,300000,12,DAY)
    assert catalog.model_dump_json()==before
    assert all(r['calculation'] is None and r['preferential_conditions_met']=='UNCONFIRMED' for r in first['matches'])
    assert [r['product']['institution'] for r in first['matches']]==sorted(r['product']['institution'] for r in first['matches'])

@pytest.mark.parametrize('mutate',[
    lambda d:d['sources'][0].__setitem__('official_url','https://www.kakaobank.com.evil.example/products/savings'),
    lambda d:d['sources'][0].__setitem__('official_url','http://www.kakaobank.com/products/savings'),
    lambda d:d['products'][0].__setitem__('source_id','TOSS-FREE-20261030'),
    lambda d:d['products'].append(d['products'][0]),
    lambda d:d['products'][1].__setitem__('allowed_months',[1,1]),
    lambda d:d['products'][0].__setitem__('minimum_monthly_payment',4000000),
    lambda d:d['sources'][0].__setitem__('verified_on','2026-02-30'),
])
def test_corrupted_or_cross_bank_data_rejected(catalog,mutate):
    with pytest.raises(ValidationError):changed(catalog,mutate)

def test_duplicate_keys_rejected(tmp_path):
    p=tmp_path/'bad.json';p.write_text('{"schema_version":"a","schema_version":"b"}',encoding='utf-8')
    with pytest.raises(core.MatchingCatalogError):core.load_matching_catalog(p)

def test_exact_official_rate_boundaries(catalog):
    expected={6:('3.70','2.90'),12:('3.85','3.25'),24:('3.20','2.50'),36:('3.20','2.50')}
    for months,(kakao,toss) in expected.items():
        result={r['product']['product_id']:r for r in core.match_savings(catalog,300000,months,DAY)['matches']}
        assert result['KAKAO-FREE-SAVINGS']['selected_base_rate_percent']==kakao
        assert result['TOSS-FREE-SAVINGS']['selected_base_rate_percent']==toss

@pytest.fixture(autouse=True)
def fixed_day(monkeypatch):monkeypatch.setattr(web,'today',lambda:DAY)

def post(**changes):return client.post('/api/financial-products/match',json=dict(profile=deepcopy(PROFILE),term_months=12)|changes)

def test_actual_endpoint_uses_cashflow_and_returns_no_store_no_ranking():
    response=post();assert response.status_code==200
    data=response.json();assert data['current']['monthly_amount']==300000 and data['current']['matched_count']==4
    assert data['actual_product_calculation_count']==0 and data['ranking'] is None and data['external_transmission'] is False
    assert response.headers['cache-control']=='no-store'

def test_before_after_matches_and_removed_product():
    after=PROFILE|dict(monthly_income=1800000,monthly_rent=550000,user_savings_capacity=500000)
    data=post(after_profile=after).json()
    assert data['current']['monthly_amount']==300000 and data['after']['monthly_amount']==500000
    assert data['after']['matched_count']==3 and data['changes']['removed']==['KBANK-CODEK-SAVINGS']

@pytest.mark.parametrize('changes,amount,count',[(dict(user_savings_capacity=None),500000,3),(dict(user_savings_capacity=0),0,0),(dict(monthly_income=100000),0,0)])
def test_unspecified_zero_and_deficit_use_existing_cashflow(changes,amount,count):
    data=post(profile=PROFILE|changes).json()
    assert data['current']['monthly_amount']==amount and data['current']['matched_count']==count

@pytest.mark.parametrize('changes',[dict(monthly_amount=1),dict(term_months='12'),dict(term_months=True),dict(term_months=0),dict(term_months=121),dict(ranking='rate')])
def test_endpoint_rejects_spoofed_or_invalid_fields(changes):
    assert post(**changes).status_code==422

def test_source_failure_is_error_not_empty_success(monkeypatch):
    def fail():raise core.MatchingCatalogError()
    monkeypatch.setattr(core,'load_matching_catalog',fail)
    response=post();assert response.status_code==503
    assert response.headers['cache-control']=='no-store'
