"""M3.3 실제 원문 검증/계산 거부와 합성 호환 계약의 계산 연결을 구분한다."""
import hashlib,json
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.finance import products,recurring
from backend.web import products as web_products
from backend.web.app import app

client=TestClient(app)
TODAY=date(2026,10,25)
PROFILE=dict(age=24,region='안산시',student_status=True,employment_status='unemployed',monthly_income=1500000,monthly_rent=450000,monthly_fixed_expenses=200000,other_monthly_expenses=350000,user_savings_capacity=300000)
IDS=['IBK-WORKER-SAVINGS','IBK-DDAY-SAVINGS','IBK-MOUGI-SAVINGS']

@pytest.fixture(autouse=True)
def fixed_day(monkeypatch):monkeypatch.setattr(web_products,'today',lambda:TODAY)

def post(**changes):
    return client.post('/api/financial-products/compare',json=dict(profile=deepcopy(PROFILE),monthly_payment=200000,term_months=12,product_ids=IDS,**{})|changes)

def data():return json.loads(products.CATALOG_PATH.read_text(encoding='utf-8'))

def validate(value):return products.Catalog.model_validate_json(json.dumps(value,ensure_ascii=False))

def compatible(**changes):
    # 아래는 합성 호환 계약 시험 전용이다. 실제 상품에 이 가정을 부여하지 않는다.
    product=products.load_catalog().products[0].model_copy(update=dict(product_id='SYNTHETIC-COMPATIBILITY-TEST',product_name='합성 호환 계약 시험 전용',
      basis_date='2026-10-25',collected_on='2026-10-25',verified_on='2026-10-25',key_fields_status='VERIFIED',subscription_status='OPEN_AS_OF_SOURCE',
      accumulation_method='FIXED_MONTHLY',rate_type='FIXED',interest_method='SIMPLE',deposit_timing='BEGINNING_OF_MONTH',date_basis='INTEGER_MONTHS',rounding_method='TOTAL_INTEREST_KRW_HALF_UP',
      calculation_evidence_locator='합성 계약 시험 전용; 실제 공식 근거 아님',unknown_fields=(),rate_options=(products.RateBand(min_months=12,max_months=12,base_rate_percent='3',max_total_rate_percent='8',evidence_locator='합성 시험'),)))
    return product.model_copy(update=changes)

def test_real_three_snapshots_and_original_integrity():
    catalog=products.load_catalog()
    assert [p.product_id for p in catalog.products]==IDS
    assert len(catalog.products)==3 and catalog.schema_version=='m3.3'
    assert all(p.basis_date=='2025-12-31' and p.verified_on=='2026-10-25' and p.snapshot_version=='1.0.0' for p in catalog.products)
    assert all(p.accumulation_method=='FLEXIBLE' and p.key_fields_status=='PARTIAL' for p in catalog.products)
    source=catalog.sources[0]
    assert source.reuse_status=='UNRESTRICTED'
    assert hashlib.sha256((products.CATALOG_PATH.parent/'sources'/source.raw_filename).read_bytes()).hexdigest()==source.raw_sha256
    assert source.raw_sha256=='bc2e9bad92cb2effaf23296e49ff1eae385848c4198f6929057c4af094d26113'

def test_real_source_cell_rates_and_limits():
    worker,dday,mougi=products.load_catalog().products
    assert worker.rate_options[0].base_rate_percent=='2.50' and worker.rate_options[0].max_total_rate_percent=='4.70'
    assert [(b.min_months,b.max_months,b.base_rate_percent) for b in dday.rate_options]==[(1,5,'2.45'),(6,11,'2.65'),(12,12,'2.85')]
    assert mougi.rate_options[1].base_rate_percent=='2.55'
    assert [p.maximum_monthly_payment for p in (worker,dday,mougi)]==[1000000,200000,3000000]
    assert [p.max_preferential_bonus_percentage_points for p in (worker,dday,mougi)]==['2.20','1.50','0.20']
    assert mougi.product_detail_url is None

def test_duplicate_product_and_source_ids():
    for key in ('products','sources'):
        value=data();value[key].append(deepcopy(value[key][0]))
        with pytest.raises(ValueError):validate(value)

@pytest.mark.parametrize('field',['product_id','product_name','institution','basis_date','verified_on','source_id','evidence_locator','rate_options','unknown_fields','rounding_method','snapshot_version'])
def test_required_fields(field):
    value=data();del value['products'][0][field]
    with pytest.raises(ValueError):validate(value)

@pytest.mark.parametrize('field,value',[('basis_date','2025-02-30'),('basis_date','20251231'),('basis_date','2026-10-26'),('snapshot_version','latest'),('source_id','MISSING'),('minimum_monthly_payment',-1),('maximum_monthly_payment',True),('product_detail_url','http://www.ibk.co.kr/product'),('product_detail_url','https://www.ibk.co.kr.evil.test/product'),('product_detail_url','https://user:pass@www.ibk.co.kr/product'),('product_detail_url','https://www.ibk.co.kr/'),('unapproved',True)])
def test_invalid_snapshot(field,value):
    record=data();record['products'][0][field]=value
    with pytest.raises(ValueError):validate(record)

@pytest.mark.parametrize('rate',[3.1,3,'NaN','Infinity','3e0','-1','100.0001','0.00001'])
def test_decimal_rate_input_is_not_float_or_invalid(rate):
    value=data();value['products'][0]['rate_options'][0]['base_rate_percent']=rate
    with pytest.raises(ValueError):validate(value)

def test_unknown_rate_not_zero_and_zero_preserved():
    for rate in (None,'0'):
        p=compatible(rate_options=(products.RateBand(min_months=12,max_months=12,base_rate_percent=rate,max_total_rate_percent=None,evidence_locator='합성 시험'),))
        result=products.evaluate_product(p,200000,12,TODAY)
        assert result['selected_base_rate_percent']==rate
        if rate is None:assert result['calculation'] is None and 'BASE_RATE_UNKNOWN' in result['reason_codes']
        else:assert result['calculation']['estimated_interest_before_tax_krw']==0

@pytest.mark.parametrize('field,value',[('official_url','https://example.com/source'),('raw_filename','../secret.xlsx'),('raw_sha256','bad'),('license_label','All rights reserved'),('reuse_status','UNKNOWN'),('source_date','2025-11-30')])
def test_invalid_source_and_date_link(field,value):
    record=data();record['sources'][0][field]=value
    with pytest.raises(ValueError):validate(record)

def test_source_hash_missing_and_duplicate_json_rejected(tmp_path):
    path=tmp_path/'catalog.json';path.write_text(products.CATALOG_PATH.read_text(encoding='utf-8'),encoding='utf-8')
    with pytest.raises(products.CatalogError):products.load_catalog(path)
    (tmp_path/'sources').mkdir();source=products.load_catalog().sources[0]
    (tmp_path/'sources'/source.raw_filename).write_bytes(b'changed')
    with pytest.raises(products.CatalogError):products.load_catalog(path)
    path.write_text('{"schema_version":"m3.3","schema_version":"m3.3"}',encoding='utf-8')
    with pytest.raises(products.CatalogError):products.load_catalog(path)

def test_real_products_never_call_calculator(monkeypatch):
    def forbidden(*args):raise AssertionError('real incompatible snapshot must not calculate')
    monkeypatch.setattr(recurring,'calculate_recurring_savings',forbidden)
    for p in products.load_catalog().products:
        result=products.evaluate_product(p,200000,12,TODAY)
        assert result['calculation'] is None and result['calculation_supported'] is False
        assert {'ACCUMULATION_UNSUPPORTED','STALE_SNAPSHOT','SUBSCRIPTION_UNCONFIRMED'}<=set(result['reason_codes'])

def test_synthetic_compatible_contract_calls_existing_decimal_once(monkeypatch):
    original=recurring.calculate_recurring_savings;calls=[]
    def spy(value):calls.append(value);return original(value)
    monkeypatch.setattr(recurring,'calculate_recurring_savings',spy)
    result=products.evaluate_product(compatible(),200000,12,TODAY)
    assert len(calls)==1 and calls[0].annual_base_rate_percent==Decimal('3')
    assert result['calculation']['estimated_maturity_before_tax_krw']==2439000
    assert result['preferential_conditions_met']=='UNCONFIRMED'
    assert result['rate_basis']=='BASE_RATE_ONLY' and result['user_eligibility']=='NOT_EVALUATED'

@pytest.mark.parametrize('field,value,code',[
 ('official_material_status','UNCONFIRMED','OFFICIAL_UNCONFIRMED'),('key_fields_status','PARTIAL','FIELDS_UNVERIFIED'),('key_fields_status','CONFLICT','SOURCE_CONFLICT'),
 ('subscription_status','UNCONFIRMED','SUBSCRIPTION_UNCONFIRMED'),('subscription_status','CLOSED_AS_OF_SOURCE','SUBSCRIPTION_CLOSED'),
 ('accumulation_method','FLEXIBLE','ACCUMULATION_UNSUPPORTED'),('rate_type','VARIABLE','RATE_TYPE_UNVERIFIED'),('interest_method','COMPOUND','INTEREST_UNSUPPORTED'),
 ('deposit_timing','ACTUAL_DATE','TIMING_UNSUPPORTED'),('date_basis','ACTUAL_DAYS','DAY_BASIS_UNSUPPORTED'),('rounding_method','OTHER','ROUNDING_UNVERIFIED'),
 ('calculation_evidence_locator',None,'CALCULATION_EVIDENCE_MISSING'),('maximum_monthly_payment',None,'LIMITS_UNKNOWN'),('verified_on','2026-10-26','FUTURE_DATE')])
def test_each_mandatory_assumption_blocks(field,value,code):
    out=products.evaluate_product(compatible(**{field:value}),200000,12,TODAY)
    assert code in out['reason_codes'] and out['calculation'] is None

@pytest.mark.parametrize('age,stale',[(90,False),(91,True)])
def test_review_boundary(age,stale):
    from datetime import timedelta
    p=compatible(basis_date=(TODAY-timedelta(days=age)).isoformat())
    assert ('STALE_SNAPSHOT' in products.compatibility_reasons(p,TODAY)) is stale

@pytest.mark.parametrize('payment,months,code',[(9999,12,'BELOW_MINIMUM'),(1000001,12,'ABOVE_MAXIMUM'),(10001,12,'PAYMENT_STEP_MISMATCH'),(200000,11,'TERM_MISMATCH')])
def test_amount_and_term_boundaries(payment,months,code):
    result=products.evaluate_product(compatible(),payment,months,TODAY)
    assert code in result['reason_codes'] and result['calculation'] is None

@pytest.mark.parametrize('payment',[10000,1000000])
def test_inclusive_limit_bounds(payment):
    assert products.evaluate_product(compatible(),payment,12,TODAY)['calculation_supported'] is True

def test_real_get_and_compare_http():
    response=client.get('/api/financial-products');assert response.status_code==200 and response.headers['cache-control']=='no-store'
    catalog=response.json();assert catalog['information_count']==3 and catalog['compatible_count']==0
    assert all(p['freshness']=='STALE' and p['user_eligibility']=='NOT_EVALUATED' for p in catalog['products'])
    out=post().json();assert len(out['results'])==3 and out['calculated_count']==0
    assert out['ranking'] is None and out['direct_maturity_comparison_supported'] is False
    assert all(item['calculation'] is None for item in out['results'])
    assert out['budget']['policy_benefit_applied']==0 and out['budget']['savable_amount_krw']==300000
    assert out['after_budget'] is None and out['assumptions']['rate_basis']=='BASE_RATE_ONLY'

def test_no_partial_call_on_invalid_id(monkeypatch):
    def forbidden(*args):raise AssertionError('invalid IDs must not evaluate budget')
    monkeypatch.setattr(web_products,'budget',forbidden)
    response=post(product_ids=[IDS[0],'MISSING'])
    assert response.status_code==422

def test_corrupt_catalog_503_not_empty_success(monkeypatch):
    def broken():raise products.CatalogError('private path must not be sent')
    monkeypatch.setattr(products,'load_catalog',broken)
    for response in (client.get('/api/financial-products'),post()):
        assert response.status_code==503 and 'private path' not in response.text

@pytest.mark.parametrize('capacity,mode,cap',[(None,'UNSPECIFIED',500000),(0,'EXPLICIT_ZERO',0),(300000,'EXPLICIT_LIMIT',300000)])
def test_budget_cap_none_zero_and_excess(capacity,mode,cap):
    out=post(profile=PROFILE|dict(user_savings_capacity=capacity),monthly_payment=400000).json()
    assert out['budget']['savings_capacity_mode']==mode and out['budget']['savable_amount_krw']==cap
    assert out['budget']['excess_krw']==max(0,400000-cap) and out['monthly_payment']==400000

def test_whatif_reuses_existing_adapter_two_calls_and_preserves_inputs(monkeypatch):
    original=web_products.service.simulate;calls=[]
    def spy(profile):calls.append(profile);return original(profile)
    monkeypatch.setattr(web_products.service,'simulate',spy)
    after=PROFILE|dict(monthly_income=1800000,monthly_rent=550000,user_savings_capacity=500000,employment_status='employed')
    before=deepcopy(PROFILE);out=post(after_profile=after,monthly_payment=400000).json()
    assert len(calls)==2 and PROFILE==before
    assert out['budget']['exceeds_budget_cap'] is True and out['after_budget']['exceeds_budget_cap'] is False
    assert out['after_budget']['savable_amount_krw']==500000
    assert out['budget']['policy_benefit_applied']==out['after_budget']['policy_benefit_applied']==0

def test_deficit_kept_and_no_zero_maturity():
    out=post(profile=PROFILE|dict(monthly_income=0,user_savings_capacity=None)).json()
    assert out['budget']['has_deficit'] is True and out['budget']['savable_amount_krw']==0
    assert all(item['calculation'] is None for item in out['results'])

@pytest.mark.parametrize('field,value',[('monthly_payment',-1),('monthly_payment',True),('monthly_payment','200000'),('monthly_payment',1000000000001),('term_months',0),('term_months',121),('term_months',1.5),('term_months','12'),('product_ids',[]),('product_ids',IDS+IDS),('product_ids',[1]),('product_ids',['../x']),('annual_base_rate_percent','99'),('as_of','2025-12-31'),('savable_amount',99999999),('monthly_policy_cash_benefit',100000)])
def test_strict_compare_input(field,value):
    assert post(**{field:value}).status_code==422

def test_profile_sensitive_input_not_echoed_in_validation_response():
    response=post(profile=PROFILE|dict(household_income=987654321))
    assert response.status_code==422 and '987654321' not in response.text
