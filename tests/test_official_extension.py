"""New official sources: independent amount, date, household and waitlist boundaries."""
import json
from pathlib import Path
from datetime import date
import pytest
from backend.finance.discovery import load_catalog,decision,lookup
from backend.finance.recommendation import select_rate,rank_products
from backend.opportunities.regional_discovery import Program
from backend.opportunities.personal_discovery import Rule,Profile,personal_conditions
from backend.opportunities.current_discovery import current_inputs,current_intake
ROOT=Path(__file__).resolve().parents[1]
DAY=date(2026,11,3)
def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
@pytest.fixture(scope='module')
def bank():
 c=load_catalog(ROOT/'data/financial-products/discovery-extended-20261103.json')
 d=read('data/financial-products/verified-basic-rates-extended-20261103.json')
 return c,{e['product_id']:e for e in d['entries']}
def test_preserves_all_original_256_records_and_holds_uncertain_eligibility(bank):
 old=load_catalog(ROOT/'data/financial-products/discovery-expanded-20261103.json')
 c,_=bank;products={p.product_id:p for p in c.products}
 assert len(c.products)==326 and len(old.products)==256
 assert all(products[p.product_id].model_dump(mode='json')==p.model_dump(mode='json') for p in old.products)
 assert all(p.eligibility=='UNKNOWN' and p.calculation is None for p in c.products)
 assert not any('현대자동차' in p.product_name for p in c.products)
@pytest.mark.parametrize('pid,amount,months,expected',[
 ('NOV3B-SB-HB-E-SAVE',9999,12,'BUDGET'),
 ('NOV3B-SB-HB-E-SAVE',10000,12,'FIT'),
 ('NOV3B-SB-HB-E-SAVE',1000000,12,'FIT'),
 ('NOV3B-SB-HB-E-SAVE',1000001,12,'PARTIAL'),
 ('NOV3B-SB-HB-E-SAVE',300000,37,'TERM'),
 ('NOV3B-SB-HB-E-SAVE',None,12,'INPUT'),
 ('NOV3B-SB-SNT-E-DEPOSIT',99999,12,'BUDGET'),
 ('NOV3B-SB-SNT-E-DEPOSIT',100000,12,'FIT'),
 ('NOV3B-SB-SNT-E-DEPOSIT',300000000,12,'FIT'),
 ('NOV3B-SB-SNT-E-DEPOSIT',300000001,12,'PARTIAL'),
 ('NOV3B-SB-DM-DREAM-SAVE',5000000,36,'FIT'),
 ('NOV3B-SB-DM-DREAM-SAVE',5000001,36,'PARTIAL'),
 ('NOV3X-BUSAN-0028',99,12,'BUDGET'),
 ('NOV3X-BUSAN-0028',100,12,'FIT'),
 ('NOV3X-BUSAN-0029',300000,12,'MISSING'),
 ('NOV3B-SB-SNT-SAVE',10000,12,'MISSING'),
])
def test_source_boundaries_not_guessed(bank,pid,amount,months,expected):
 c,_=bank;p=next(p for p in c.products if p.product_id==pid)
 assert decision(p,amount,months,DAY,c.review_after_days)==expected
def test_all_new_amount_edges_agree_with_published_table(bank):
 c,_=bank;d=read('frontend/src/public-data/product-expanded.json')
 old={p['product_id'] for p in read('data/financial-products/discovery-expanded-20261103.json')['products']}
 for p in c.products:
  if p.product_id in old:continue
  values={None,0,1,10000,300000,1000000,5000000,10000000}
  for n in [p.minimum,p.maximum]:
   if n is not None:values|={max(0,n-1),n,n+1}
  for m in [1,6,12,13,24,36,37,60,120]:
   for a in values:assert lookup(d,p,a,m)==decision(p,a,m,DAY,c.review_after_days)
 assert d['valid_until']=='2026-11-06'
def test_nominal_interest_and_special_conditions_are_not_invented(bank):
 c,reviews=bank;ps={p.product_id:p for p in c.products}
 nominal=select_rate(ps['NOV3B-SB-SNT-E-DEPOSIT'],12,reviews['NOV3B-SB-SNT-E-DEPOSIT'],DAY)
 assert nominal['base_rate_percent']=='3.74'  # compound annual average3.80 is not nominal
 for pid in ['NOV3X-BUSAN-0093','NOV3X-BUSAN-0160','NOV3X-BUSAN-0197','NOV3B-SB-HB-6M-ROTATE']:
  assert select_rate(ps[pid],12,reviews.get(pid),DAY) is None
 assert select_rate(ps['NOV3B-SB-HB-E-SAVE'],13,reviews.get('NOV3B-SB-HB-E-SAVE'),DAY) is None
 assert select_rate(ps['NOV3B-SB-HB-E-SAVE'],12,reviews.get('NOV3B-SB-HB-E-SAVE'),date(2026,11,11)) is None
def test_whole_budget_priority_and_basic_rate_sort_remain_deterministic(bank):
 c,r=bank;rows=rank_products(c,r,'SAVINGS',1000001,12,DAY)
 ids=[x['product_id'] for x in rows]
 full=[x for x in rows if x['code']=='FIT' and x['rate']]
 partial=[x for x in rows if x['code']=='PARTIAL' and x['rate']]
 assert all(ids.index(x['product_id'])<ids.index(y['product_id']) for x in full for y in partial)
 from decimal import Decimal
 rates=[Decimal(x['rate']['base_rate_percent']) for x in full]
 assert rates==sorted(rates,reverse=True)
 assert all(x['calculation'] is None and x['eligibility']=='UNKNOWN' for x in rows)
@pytest.fixture(scope='module')
def support():return read('data/support-programs/verified-extension-20261103.json')
def test_household_or_spouse_age_is_not_own_age_failure(support):
 for pid in ['EXT3-GG-12349','EXT3-GG-12348']:
  rule=Rule.model_validate(next(r for r in support['rules'] if r['program_id']==pid))
  for age in [17,25,50]:
   result=personal_conditions(rule,Profile(age=age,employment='employed',rent='no'),DAY)
   assert result['age']=='UNKNOWN' and result['rent']=='UNKNOWN'
def test_explicit_current_age_and_conflicting_birth_dates_remain_separate(support):
 y=Rule.model_validate(next(r for r in support['rules'] if r['program_id']=='EXT3-GG-12382'))
 for a,want in [(17,'FAIL'),(18,'PASS'),(39,'PASS'),(40,'FAIL')]:
  assert personal_conditions(y,Profile(age=a),DAY)['age']==want
 conflict=Rule.model_validate(next(r for r in support['rules'] if r['program_id']=='EXT3-GG-12391'))
 assert all(personal_conditions(conflict,Profile(age=a),DAY)['age']=='UNKNOWN' for a in [18,19,34,35,40])
def test_full_capacity_does_not_become_open_recommendation(support):
 ps={p['program_id']:Program.model_validate(p) for p in support['programs']}
 for pid in ['EXPAND4-IC-2229','EXPAND4-IC-2230','EXPAND4-IC-2262']:
  assert current_intake(ps[pid],DAY,support['intake_verification'])=='WINDOW_GUIDANCE'
  assert any('대기' in v for v in ps[pid].required_checks)
def test_official_current_and_guidance_are_dated_without_benefit_payment(support):
 ps=[Program.model_validate(p) for p in support['programs']]
 assert len(ps)==72
 for p in ps:
  assert p.eligibility=='UNKNOWN' and p.benefit_applied_krw==0
  assert current_intake(p,date(2026,11,2),support['intake_verification'])!='VERIFIED_OPEN'
  assert current_intake(p,date(2026,11,11),support['intake_verification'])!='VERIFIED_OPEN'
 for pid in ['EXT3-GG-12349','EXT3-GG-12348','EXT3-GG-12344']:
  p=next(p for p in ps if p.program_id==pid)
  assert current_intake(p,DAY,support['intake_verification'])=='VERIFIED_OPEN'
 for pid in ['EXT3-GG-12402','EXT3-GG-12376','EXT3-GG-12394','EXT3-GG-12390']:
  p=next(p for p in ps if p.program_id==pid)
  assert current_intake(p,DAY,support['intake_verification'])=='WINDOW_GUIDANCE'
def test_new_table_preserves_old_programs_and_nonresidential_routes(support):
 old=read('data/support-programs/verified-expansion-20261103.json')
 c,_,_=current_inputs();public=read('frontend/src/public-data/current-support.json')
 assert len(c.programs)==416
 # Automated rechecks only add AUTOMATED_PAGE_MATCH sources; the reviewed record must be unchanged.
 reviewed=lambda p:{**p,'sources':[s for s in p['sources'] if s['evidence']!='AUTOMATED_PAGE_MATCH']}
 byid={p['program_id']:reviewed(p) for p in public['programs']}
 assert all(byid[p['program_id']]==p for p in old['programs'])
 ids={p['program_id']:i for i,p in enumerate(public['programs'])}
 for pid in support['alternative_region_ids']:
  assert public['regions']['제주'][ids[pid]]=='UNKNOWN'
