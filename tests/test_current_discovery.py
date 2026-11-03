from datetime import date
import json
import pytest
from backend.opportunities.current_discovery import current_inputs,current_intake,compile_current,ALTERNATIVE_REGION
from backend.opportunities.regional_discovery import ROOT
from backend.finance.discovery import load_catalog,decision,compile_tables,lookup

@pytest.fixture(scope='module')
def support():return current_inputs()

def test_official_status_dominates_annual_plan(support):
    c,_,e=support;p={p.program_id:p for p in c.programs}
    assert current_intake(p['GG-YOUTH-INTERVIEW-ALLOWANCE-2026'],date(2026,11,1),e)=='NO_INTAKE'
    assert current_intake(p['GYEONGNAM-JINJU-EXAM-FEE-2026'],date(2026,11,1),e)=='CLOSED'
    assert current_intake(p['SEOUL-YOUTH-CULTURE-PASS-2026'],date(2026,11,1),e)=='VERIFIED_OPEN'

@pytest.mark.parametrize('pid', ['JB-GUNSAN-YOUTH-INTERVIEW-FEE-2026','INCHEON-YEONGJONG-EXAM-FEE-2026','SEOUL-LIFE-PLANNING-STARTER-2026'])
def test_open_is_dated_not_permanent(support,pid):
    c,_,e=support;p=next(p for p in c.programs if p.program_id==pid)
    assert current_intake(p,date(2026,11,1),e)=='VERIFIED_OPEN'
    assert current_intake(p,date(2026,11,9),e)=='REVIEW_REQUIRED'
    assert current_intake(p,date(2027,1,1),e)=='CLOSED'

def test_future_round_is_not_open(support):
    c,_,e=support;p=next(p for p in c.programs if p.program_id=='GG-YOUTH-BASIC-INCOME-2026-Q4')
    assert current_intake(p,date(2026,11,1),e)=='UPCOMING'
    assert current_intake(p,date(2026,11,2),e)=='WINDOW_GUIDANCE'

def test_guidance_and_conflicting_display_are_not_open(support):
    c,_,e=support;p={p.program_id:p for p in c.programs}
    assert current_intake(p['INCHEON-GYEYANG-YOUTH-CHALLENGE-2026'],date(2026,11,1),e)=='CONTINUOUS_GUIDANCE'
    assert current_intake(p['SEOUL-YOUNGTECH-COUNSELING-2026'],date(2026,11,1),e)=='UNKNOWN'

def test_current_snapshot_preserves_uncertainty_and_alternative_residence():
    d=json.loads((ROOT/'frontend/src/public-data/current-support.json').read_text(encoding='utf-8'))
    assert len(d['programs'])==344
    for i,p in enumerate(d['programs']):
        assert p['eligibility']=='UNKNOWN' and p['benefit_applied_krw']==0
        if p['program_id'] in ALTERNATIVE_REGION:assert d['regions']['제주'][i]!='FAIL'
    assert len(d['schedules'])==366
    assert d['schedules']['2026-11-01'].count('VERIFIED_OPEN')==181
    assert sum(state=='VERIFIED_OPEN' for p,state in zip(d['programs'],d['schedules']['2026-11-09']) if all(src['verified_on']<'2026-11-03' for src in p['sources']))==8
    assert d['schedules']['2026-11-11'].count('VERIFIED_OPEN')==0

@pytest.fixture(scope='module')
def bank():return load_catalog(ROOT/'data/financial-products/discovery-expanded-20261101.json')

def test_expansion_keeps_old_snapshot_and_removes_discontinued(bank):
    assert len(load_catalog().products)==74
    assert len(bank.products)==113
    assert not {'KB-ONE','KB-PET'}&{p.product_id for p in bank.products}
    assert all(p.calculation is None and p.eligibility=='UNKNOWN' for p in bank.products)

@pytest.mark.parametrize('pid,amount,months,expected',[
 ('HANA-DOUBLE-UP-SAVINGS',50000,12,'FIT'),('HANA-DOUBLE-UP-SAVINGS',49999,12,'BUDGET'),
 ('HANA-DOUBLE-UP-SAVINGS',200001,12,'PARTIAL'),('HANA-DOUBLE-UP-SAVINGS',100000,13,'TERM'),
 ('HANA-RUNNING-SAVINGS',300000,12,'FIT'),('HANA-RUNNING-SAVINGS',300001,12,'PARTIAL'),
 ('HANA-PENSION-COMPOUND-SAVINGS',100000,12,'SCHEDULE'),
 ('HANWHA-MYMO-SAVINGS',100000,12,'REVIEW'),
 ('PEPPER-6M-ROTATING-DEPOSIT',100000,6,'TERM'),('PEPPER-6M-ROTATING-DEPOSIT',100000,24,'FIT')])
def test_expanded_product_boundaries(bank,pid,amount,months,expected):
    p=next(p for p in bank.products if p.product_id==pid)
    assert decision(p,amount,months,date(2026,11,1),bank.review_after_days)==expected

def test_published_product_lookup_equals_python_at_every_boundary(bank):
    d=json.loads((ROOT/'frontend/src/public-data/product-expanded.json').read_text(encoding='utf-8'))
    for p in bank.products:
        samples={0,1,p.minimum or 0,(p.minimum or 0)+1,p.maximum or 0,(p.maximum or 0)+1}
        for m in {1,6,12,13,24,36,60,120}:
            for a in [*samples,None]:
                assert lookup(d,p,a,m)==decision(p,a,m,date(2026,11,1),bank.review_after_days)


def test_new_birth_range_uses_the_official_dates(support):
    from backend.opportunities.personal_discovery import age_match
    _,r,_=support
    rule=next(x for x in r.rules if x.program_id=='SEOUL-LIFE-PLANNING-STARTER-2026')
    assert age_match(rule.age,23,date(2026,11,1))=='PASS'
    assert age_match(rule.age,24,date(2026,11,1))=='UNKNOWN'
    assert age_match(rule.age,25,date(2026,11,1))=='FAIL'
