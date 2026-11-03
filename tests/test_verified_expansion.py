"""Independent boundary and uncertainty checks for the Nov 3 reviewed snapshot."""
import json
from datetime import date
from pathlib import Path
import pytest
from backend.finance.discovery import load_catalog,decision,lookup
from backend.finance.recommendation import rank_products,select_rate
from backend.opportunities.regional_discovery import Program
from backend.opportunities.personal_discovery import Profile,Rule,personal_conditions
from backend.opportunities.current_discovery import current_intake,current_inputs

ROOT=Path(__file__).resolve().parents[1]
def read(rel):return json.loads((ROOT/rel).read_text(encoding='utf8'))
@pytest.fixture(scope='module')
def bank():
 catalog=load_catalog(ROOT/'data/financial-products/discovery-expanded-20261103.json')
 reviews={e['product_id']:e for e in read('data/financial-products/verified-basic-rates-20261103.json')['entries']}
 return catalog,reviews

def test_previous_153_products_are_preserved_byte_independent_records(bank):
 old=load_catalog(ROOT/'data/financial-products/discovery-recommended-20261102.json')
 products={p.product_id:p for p in bank[0].products}
 assert len(old.products)==153
 assert all(products[p.product_id].model_dump(mode='json')==p.model_dump(mode='json') for p in old.products)
 assert not any(p.institution=='KB국민은행' and p.product_name=='직장인우대적금' for p in bank[0].products)
 assert all(p.eligibility=='UNKNOWN' and p.calculation is None for p in bank[0].products)

@pytest.mark.parametrize('pid,amount,months,expected',[
 ('NOV3-SB-BULIM-TOK-SAVE',9999,12,'BUDGET'),
 ('NOV3-SB-BULIM-TOK-SAVE',10000,12,'FIT'),
 ('NOV3-SB-BULIM-TOK-SAVE',10001,12,'FIT'),
 ('NOV3-SB-MOA-E-SAVE',9999,12,'BUDGET'),
 ('NOV3-SB-MOA-E-SAVE',10000,12,'FIT'),
 ('NOV3-SB-MOA-E-SAVE',0,12,'BUDGET'),
 ('NOV3-SB-MOA-E-SAVE',None,12,'INPUT'),
 ('NOV3-SB-MOA-E-SAVE',300000,11,'TERM'),
 ('NOV3-SB-SMART-DEPOSIT',10000000,12,'MISSING'),
])
def test_new_reviewed_amount_boundaries(bank,pid,amount,months,expected):
 p=next(p for p in bank[0].products if p.product_id==pid)
 assert decision(p,amount,months,date(2026,11,3),bank[0].review_after_days)==expected

def test_new_rate_order_uses_basic_not_conditional_and_separates_deposits(bank):
 cat,reviews=bank
 rows=rank_products(cat,reviews,'SAVINGS',300000,12,date(2026,11,3))
 top=[r for r in rows if r['code'] in ('FIT','PARTIAL') and r['rate']][:3]
 assert [r['product_id'] for r in top]==['NOV3-SB-BULIM-TOK-SAVE','NOV3-SB-MOA-E-SAVE','KAKAO-FREE-SAVINGS']
 assert [r['rate']['base_rate_percent'] for r in top]==['4.20','4.00','3.85']
 deposits=rank_products(cat,reviews,'DEPOSIT',None,12,date(2026,11,3))
 assert not any(r['code'] in ('FIT','PARTIAL') for r in deposits)
 assert all(r['calculation'] is None and r['eligibility']=='UNKNOWN' for r in rows)

def test_published_new_lookup_matches_python_at_amount_and_period_edges(bank):
 cat,_=bank;prepared=read('frontend/src/public-data/product-expanded.json')
 old={p['product_id'] for p in read('data/financial-products/discovery-recommended-20261102.json')['products']}
 for p in cat.products:
  if p.product_id in old:continue
  values={0,1,10000,300000,10000000}
  if p.minimum is not None:values|={max(0,p.minimum-1),p.minimum,p.minimum+1}
  if p.maximum is not None:values|={p.maximum,min(10**12,p.maximum+1)}
  for months in (1,6,12,13,24,36,60):
   for amount in [None,*values]:
    assert lookup(prepared,p,amount,months)==decision(p,amount,months,date(2026,11,3),cat.review_after_days)
 assert prepared['valid_until']=='2026-11-06'

def test_future_expired_and_held_new_rate_is_never_usable(bank):
 cat,reviews=bank;p=next(p for p in cat.products if p.product_id=='NOV3-SB-MOA-E-SAVE')
 assert select_rate(p,12,reviews[p.product_id],date(2026,11,2)) is None
 assert select_rate(p,12,reviews[p.product_id],date(2026,11,11)) is None
 for pid,e in reviews.items():
  if pid.startswith('NOV3') and e.get('excluded_reason'):
   held=next(p for p in cat.products if p.product_id==pid)
   assert select_rate(held,12,e,date(2026,11,3)) is None

def test_national_guidance_does_not_become_confirmed_intake_or_income_approval():
 d=read('data/support-programs/verified-expansion-20261103.json')
 national=[p for p in d['programs'] if p['program_id'].startswith('EXPAND3-KR-')]
 assert len(national)==10
 for raw in national:
  p=Program.model_validate(raw)
  assert current_intake(p,date(2026,11,3),d['intake_verification'])!='VERIFIED_OPEN'
  rule=Rule.model_validate(next(r for r in d['rules'] if r['program_id']==p.program_id))
  assert set(personal_conditions(rule,Profile(age=25,employment='employed',rent='yes'),date(2026,11,3)).values())=={'UNKNOWN'}
  assert p.eligibility=='UNKNOWN' and p.benefit_applied_krw==0

def test_work24_rounds_are_grouped_deadline_is_not_course_date_and_scope_is_not_residence():
 d=read('data/support-programs/verified-expansion-20261103.json')
 courses=[p for p in d['programs'] if p['program_id'].startswith('EXPAND3-WORK24-')]
 assert len(courses)==21
 for raw in courses:
  p=Program.model_validate(raw);pid=p.program_id
  assert p.starts_on is None and p.city is None
  assert pid in d['alternative_region_ids']
  assert p.benefit_applied_krw==0 and p.eligibility=='UNKNOWN'
  assert current_intake(p,date(2026,11,2),d['intake_verification'])!='VERIFIED_OPEN'
  assert current_intake(p,date(2026,11,11),d['intake_verification'])!='VERIFIED_OPEN'
  state=current_intake(p,date(2026,11,3),d['intake_verification'])
  assert state==('WINDOW_GUIDANCE' if p.ends_on=='2026-11-03' else 'VERIFIED_OPEN')
 cat,_,e=current_inputs();nonlocal_jeju=read('frontend/src/public-data/current-support.json')['regions']['제주']
 indexes={p.program_id:i for i,p in enumerate(cat.programs)}
 assert all(nonlocal_jeju[indexes[p['program_id']]]=='UNKNOWN' for p in courses)
