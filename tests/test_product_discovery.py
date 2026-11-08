from copy import deepcopy
from datetime import date,timedelta
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.finance.discovery import Catalog,Product,Source,load_catalog,decision,search,compile_tables,lookup
from backend.web.app import app

DAY=date(2026,11,1)
@pytest.fixture(scope='module')
def catalog():return load_catalog()
@pytest.fixture(scope='module')
def compiled(catalog):return compile_tables(catalog,DAY)
def named(catalog,name):return next(p for p in catalog.products if p.product_id==name)

def test_expanded_catalog_preserves_original_twenty_and_explicit_scope(catalog):
    assert len(catalog.products)==74 and len({p.institution for p in catalog.products})==18
    previous=load_catalog(Path(__file__).resolve().parents[1]/'data/financial-products/discovery-20261031.json')
    assert {p.product_id for p in previous.products}.issubset({p.product_id for p in catalog.products})
    assert '전수 수집한 목록이 아니' in catalog.coverage_note
    assert all(p.calculation is None and p.eligibility=='UNKNOWN' and p.sources for p in catalog.products)

@pytest.mark.parametrize('amount,months,expected',[(0,12,'BUDGET'),(9999,12,'BUDGET'),(10000,12,'FIT'),(1000000,12,'FIT'),(1000001,12,'PARTIAL'),(300000,6,'TERM'),(300000,24,'FIT'),(300000,25,'TERM')])
def test_exact_money_and_discrete_term_boundaries(catalog,amount,months,expected):
    assert decision(named(catalog,'KB-CLEAR-SKY'),amount,months,DAY,7)==expected

def test_partial_is_explicit_allocation_not_silent_amount_replacement(catalog):
    result=search(catalog,500000,12,None,DAY)
    row=next(r for r in result['rows'] if r['product_id']=='KBANK-CODEK-SAVINGS')
    assert row['code']=='PARTIAL' and row['allocation']==300000 and row['unallocated']==200000
    assert row['eligibility']=='UNKNOWN' and row['calculation'] is None

def test_lump_sum_never_uses_monthly_income_or_saving_amount(catalog):
    p=named(catalog,'KAKAO-DEPOSIT')
    assert decision(p,None,12,DAY,7)=='INPUT'
    assert decision(p,999999,12,DAY,7)=='BUDGET'
    assert decision(p,1000000,12,DAY,7)=='FIT'
    assert next(r for r in search(catalog,10000000,12,None,DAY)['rows'] if r['product_id']==p.product_id)['code']=='INPUT'

def test_reference_document_is_not_promoted_to_current_recommendation(catalog):
    for pid in ('SHINHAN-SOL','KB-PET','IBK-CARBON'):
        p=named(catalog,pid);assert p.reference_only and p.reference_reason and decision(p,100000,12,DAY,7)=='REVIEW'

def test_quarterly_weekly_daily_and_date_schedules_are_never_monthly_caps(catalog):
    for pid,months in [('HANA-SALARY',12),('HANA-PRIMARY',12),('KAKAO-26W',6),('IBK-DDAY',12)]:
        assert decision(named(catalog,pid),100000,months,DAY,7)=='SCHEDULE'
    assert decision(named(catalog,'KAKAO-31D'),100000,1,DAY,7)=='MISSING'

def test_missing_upper_bound_is_not_invented_as_unlimited(catalog):
    assert decision(named(catalog,'HANA-DEPOSIT'),5000000,12,DAY,7)=='MISSING'
    assert decision(named(catalog,'KB-STAR-DEPOSIT'),5000000,12,DAY,7)=='MISSING'

@pytest.mark.parametrize('amount',[-1,True,1.5,'300000',10**12+1])
def test_invalid_amounts_rejected_even_for_unverified_product(catalog,amount):
    with pytest.raises(ValueError):search(catalog,amount,12,None,DAY)

@pytest.mark.parametrize('months',[0,121,True,1.5])
def test_invalid_period_not_silently_coerced(catalog,months):
    with pytest.raises(ValueError):search(catalog,100000,months,None,DAY)

def test_stale_and_future_dates_do_not_return_positive_comparison(catalog):
    p=catalog.products[0];d=date.fromisoformat(p.sources[0].reviewed_on)
    assert decision(p,100000,12,d+timedelta(days=7),7)=='FIT'
    assert decision(p,100000,12,d+timedelta(days=8),7)=='STALE'
    assert decision(p,100000,12,d-timedelta(days=1),7)=='STALE'

def test_compiled_public_table_matches_python_at_all_boundaries_and_intervals(catalog,compiled):
    for p in catalog.products:
        bounds=compiled['tables'][p.kind]['boundaries']
        amounts={0,1,300000,500000,1000000,5000000,10**12,*bounds,*[n-1 for n in bounds if n],*[n+1 for n in bounds if n<10**12]}
        for months in (1,6,12,13,24,36,60,120):
            for amount in [None,*amounts]:assert lookup(compiled,p,amount,months)==decision(p,amount,months,DAY,7)

def test_compilation_is_deterministic_and_cannot_renew_source_dates(catalog,compiled):
    before=catalog.model_dump(mode='json');assert compile_tables(catalog,DAY)==compiled
    rebuilt=compile_tables(catalog,DAY+timedelta(days=20))
    assert rebuilt['valid_until']==compiled['valid_until'] and catalog.model_dump(mode='json')==before

def test_committed_static_artifact_is_exact_python_output(catalog,compiled):
    path=Path(__file__).resolve().parents[1]/'frontend/src/public-data/product-discovery.json'
    assert json.loads(path.read_text(encoding='utf-8'))==compiled
    assert compiled['paid_service'] is False and compiled['automatic_refresh'] is False

@pytest.mark.parametrize('url',['http://www.kakaobank.com/products/savings','https://www.kakaobank.com.attacker.test/products/savings','https://user:pw@www.kakaobank.com/products/savings','https://www.kakaobank.com:444/products/savings'])
def test_nonofficial_or_credentialed_source_not_accepted(catalog,url):
    s=catalog.products[0].sources[0].model_dump();s['url']=url
    with pytest.raises(ValidationError):Source.model_validate(s)

def test_duplicate_product_and_impossible_limits_fail_closed(catalog):
    d=catalog.model_dump(mode='json');d['products'].append(deepcopy(d['products'][0]))
    with pytest.raises(ValidationError):Catalog.model_validate(d)
    d=catalog.products[0].model_dump();d.update(minimum=500,maximum=100)
    with pytest.raises(ValidationError):Product.model_validate(d)

def test_http_search_preserves_unknown_no_maturity_and_no_grant(catalog):
    with TestClient(app) as c:
        r=c.post('/api/product-discovery/search',json={'monthly_amount':500000,'term_months':12,'lump_sum':2000000})
        assert r.status_code==200
        data=r.json();assert len(data['rows'])==len(catalog.products) and data['actual_product_calculation_count']==0 and data['policy_benefit_applied_krw']==0 and data['ranked_by_yield'] is False
        assert all(r['eligibility']=='UNKNOWN' and r['calculation'] is None for r in data['rows'])
        assert c.post('/api/product-discovery/search',json={'monthly_amount':True,'term_months':12}).status_code==422


def test_deposit_only_http_does_not_invent_monthly_budget(monkeypatch):
    # The endpoint reads the wall clock and the catalog's evidence expires after 7 days, so this test began failing
    # on 2026-11-08 (KAKAO-DEPOSIT became STALE) although the logic under test is unrelated to freshness.
    # Pin the clock inside the catalog's review window; assertions are unchanged.
    import datetime as dt
    class PinnedDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 3, 12, 0, tzinfo=tz)
    monkeypatch.setattr('backend.web.product_discovery.datetime', PinnedDatetime)
    with TestClient(app) as c:
        r=c.post('/api/product-discovery/search',json={'term_months':12,'lump_sum':2000000})
        assert r.status_code==200
        rows={r['product_id']:r for r in r.json()['rows']}
        assert rows['KAKAO-DEPOSIT']['code']=='FIT' and rows['KB-MY-SAVING']['code']=='INPUT'
        assert c.post('/api/product-discovery/search',json={'term_months':12}).status_code==422
