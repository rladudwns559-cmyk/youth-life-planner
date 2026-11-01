from copy import deepcopy
from datetime import date
import json
import pytest
from pydantic import ValidationError
from backend.opportunities.regional_discovery import load_catalog,region_match,evaluate,recruitment,compile_public,Catalog,ROOT
from backend.opportunities.catalog import REGIONS

DAY=date(2026,11,1)
@pytest.fixture(scope='module')
def catalog():return load_catalog()
def named(c,pid):return next(p for p in c.programs if p.program_id==pid)

def test_national_rent_is_one_program_with_ansan_implementation(catalog):
 p=named(catalog,'KR-YOUTH-RENT-2026')
 assert not p.provinces and p.city is None and len(p.sources)==2
 assert 'NATIONAL-YOUTH-RENT-2026-ANSAN-ENTRY' not in [x.program_id for x in catalog.programs]
 assert len(catalog.programs)==38 and {p.category for p in catalog.programs}=={'ASSET','HOUSING','EMPLOYMENT','EDUCATION','LIVING','CULTURE'}

def test_ansan_receives_national_province_city_but_not_seoul(catalog):
 assert region_match(named(catalog,'KR-YOUTH-RENT-2026'),'경기','안산시',DAY)=='PASS'
 assert region_match(named(catalog,'GG-YOUTH-INTERVIEW-ALLOWANCE-2026'),'경기','안산시',DAY)=='PASS'
 assert region_match(named(catalog,'ANSAN-YOUTH-MOVE-FEE-2026'),'경기','안산시',DAY)=='PASS'
 assert region_match(named(catalog,'SEOUL-YOUTH-RENT-2026'),'경기','안산시',DAY)=='FAIL'

def test_province_does_not_prove_city_or_registered_residence(catalog):
 p=named(catalog,'ANSAN-YOUTH-EXAM-FEE-2026')
 assert region_match(p,'경기',None,DAY)=='UNKNOWN'
 assert region_match(p,None,None,DAY)=='UNKNOWN'
 assert region_match(p,'경기','__OTHER__',DAY)=='FAIL'
 assert region_match(p,'경기','안산시',DAY)=='PASS'
 assert evaluate(p,'경기','안산시',DAY)['overall']=='UNKNOWN'

def test_same_district_name_does_not_match_another_province(catalog):
 p=named(catalog,'DAEGU-DALSEO-EXAM-FEE-2026')
 assert region_match(p,'대구','달서구',DAY)=='PASS'
 assert region_match(p,'서울','달서구',DAY)=='FAIL'

@pytest.mark.parametrize('province',REGIONS)
def test_every_region_retains_national_support_and_never_approves_full_eligibility(catalog,province):
 p=named(catalog,'KR-YOUTH-RENT-2026');r=evaluate(p,province,None,DAY)
 assert r['region']=='PASS' and r['overall']=='UNKNOWN' and r['benefit_applied_krw']==0

def test_latest_cancellation_and_early_closure_dominate_calendar(catalog):
 gg=named(catalog,'GG-YOUTH-INTERVIEW-ALLOWANCE-2026')
 inc=named(catalog,'INCHEON-DREAM-NARAE-2026')
 assert recruitment(gg,DAY)=='CLOSED' and '미운영' in gg.schedule_note
 assert inc.ends_on is None and recruitment(inc,DAY)=='CLOSED'

def test_budget_uncertainty_and_conflicting_sources_never_become_open(catalog):
 for pid in ('ANSAN-YOUTH-EXAM-FEE-2026','JEJU-TAMRA-YOUTH-ARRIVAL-2026','GB-POHANG-YOUTH-JOB-PACKAGE-2026'):
  p=named(catalog,pid);assert recruitment(p,DAY)=='UNKNOWN';assert p.required_checks

def test_day_boundary_and_stale_source_behavior(catalog):
 p=named(catalog,'KR-YOUTH-RENT-2026').model_copy(update={'intake_mode':'WINDOW','starts_on':'2026-11-02','ends_on':'2026-11-03'})
 assert recruitment(p,DAY)=='UPCOMING'
 assert recruitment(p,date(2026,11,2))=='WINDOW_GUIDANCE'
 assert recruitment(p,date(2026,11,3))=='WINDOW_GUIDANCE'
 assert recruitment(p,date(2026,11,4))=='CLOSED'
 card=named(catalog,'KR-NATIONAL-LEARNING-CARD')
 assert recruitment(card,date(2026,11,8))=='CONTINUOUS_GUIDANCE'
 assert recruitment(card,date(2026,11,9))=='REVIEW_REQUIRED'
 assert recruitment(card,date(2026,10,31))=='REVIEW_REQUIRED'

def test_public_region_and_date_tables_equal_engine_results(catalog):
 public=compile_public(catalog)
 saved=json.loads((ROOT/'frontend/src/public-data/regional-programs.json').read_text(encoding='utf-8'))
 assert public==saved
 for key,province,city in (('*',None,None),('경기','경기',None),('경기|안산시','경기','안산시'),('경기|__OTHER__','경기','__OTHER__')):
  assert public['regions'][key]==[evaluate(p,province,city,DAY)['region'] for p in catalog.programs]
 assert public['schedules']['2026-11-01']==[evaluate(p,None,None,DAY)['recruitment'] for p in catalog.programs]

@pytest.mark.parametrize('mutation', ['duplicate','city','province','source','no_checks','eligibility','credit'])
def test_malformed_or_overclaiming_catalog_is_rejected(catalog,mutation):
 d=deepcopy(catalog.model_dump(mode='json'));p=d['programs'][0]
 if mutation=='duplicate':d['programs'].append(deepcopy(p))
 elif mutation=='city':p.update(city='안산시',provinces=[])
 elif mutation=='province':p['provinces']=['서울시로추정']
 elif mutation=='source':p['sources'][0]['url']='https://attacker.invalid/example'
 elif mutation=='no_checks':p['required_checks']=[]
 elif mutation=='eligibility':p['eligibility']='PASS'
 elif mutation=='credit':p['benefit_applied_krw']=200000
 with pytest.raises(ValidationError):Catalog.model_validate(d)
