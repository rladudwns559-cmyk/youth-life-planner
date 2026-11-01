"""Official discovery contracts; synthetic profiles/modified snapshots only."""
import copy,json
from datetime import datetime,timedelta,timezone
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.opportunities.catalog import Catalog,CatalogError,load_catalog
from backend.opportunities.matching import Supplement,discover,intake,province_for
from backend.opportunities.changes import diff_catalogs
from backend.web import asset_programs as web
from backend.web.app import app
from backend.web.schemas import SimulationInput

NOW=datetime.fromisoformat('2026-10-30T12:00:00+09:00')
PROFILE=dict(age=24,region='안산시',student_status=True,employment_status='employed',monthly_income=1500000,monthly_rent=450000,monthly_fixed_expenses=200000,other_monthly_expenses=350000,user_savings_capacity=300000)
@pytest.fixture
def catalog():return load_catalog()
def rec(c,extra=None,capacity=300000,**changes):return discover(c,NOW,SimulationInput(**(PROFILE|changes)),extra or Supplement(),capacity)
def row(result,identifier):return next(r for r in result['programs'] if r['program']['program_id']==identifier)
def program(c,identifier):return next(p for p in c.programs if p.program_id==identifier)
def revalidate(raw):return Catalog.model_validate_json(json.dumps(raw,ensure_ascii=False))
def raw(c):return c.model_dump(mode='json')
def checked(c,day):
    data=raw(c)
    for s in data['sources']:
        s['verified_on']=day
        if s['published_on'] and s['published_on']>day:s['published_on']=day  # Synthetic boundary fixture only.
    return revalidate(data)

def test_ten_distinct_draft_programs_twelve_official_sources(catalog):
    assert len(catalog.programs)==10 and len(catalog.sources)==12
    assert len({p.program_id for p in catalog.programs})==10
    assert all(p.data_status=='DRAFT' and p.coverage=='CONDITION_SLICE' and p.remaining_checks for p in catalog.programs)

def test_actual_october_statuses_do_not_invent_recruitment(catalog):
    result=discover(catalog,NOW)
    assert result['counts']==dict(OPEN=1,UPCOMING=0,CLOSED=8,NO_INTAKE=1,UNKNOWN=0,REVIEW_REQUIRED=0)
    assert row(result,'KR-YOUTH-FUTURE')['intake']['phase']=='기신청자 심사'
    assert row(result,'GG-YOUTH-WORKER')['intake']['status']=='NO_INTAKE'

def test_account_opening_is_not_new_applications(catalog):
    c=checked(catalog,'2026-11-20')
    state=intake(program(c,'KR-YOUTH-FUTURE'),c,datetime.fromisoformat('2026-11-20T12:00:00+09:00'))
    assert state['status']=='CLOSED' and state['phase']=='심사 통과자 계좌개설'

@pytest.mark.parametrize('moment,expected',[
    ('2026-09-28T09:59:59+09:00','UPCOMING'),('2026-09-28T10:00:00+09:00','OPEN'),
    ('2026-10-08T17:59:59+09:00','OPEN'),('2026-10-08T18:00:00+09:00','CLOSED')])
def test_exact_deadlines(catalog,moment,expected):
    c=checked(catalog,moment[:10])
    assert intake(program(c,'DAEJEON-FUTURE-DOUBLE'),c,datetime.fromisoformat(moment))['status']==expected

def test_official_twenty_four_hour_deadline(catalog):
    c=checked(catalog,'2026-08-19');p=program(c,'GN-MODADREAM')
    assert intake(p,c,datetime.fromisoformat('2026-08-19T23:59:59+09:00'))['status']=='OPEN'
    assert intake(p,c,datetime.fromisoformat('2026-08-20T00:00:00+09:00'))['status']=='CLOSED'

def test_kst_context_and_timezone_requirement(catalog):
    assert discover(catalog,NOW.astimezone(timezone.utc))==discover(catalog,NOW)
    with pytest.raises(ValueError):discover(catalog,NOW.replace(tzinfo=None))

@pytest.mark.parametrize('days,expected',[(7,'OPEN'),(8,'REVIEW_REQUIRED'),(-1,'REVIEW_REQUIRED')])
def test_source_freshness(catalog,days,expected):
    assert intake(program(catalog,'KR-YOUTH-HOUSING'),catalog,NOW+timedelta(days=days))['status']==expected

def test_region_filter_and_no_complete_pass(catalog):
    r=rec(catalog)
    assert r['recommendation_counts']['CURRENT_CANDIDATE']==1
    assert r['recommendation_counts']['WATCHLIST']==3
    assert r['recommendation_counts']['NOT_MATCHED']==6
    assert all(x['assessment']['status'] in ('FAIL','UNKNOWN') for x in r['programs'])

@pytest.mark.parametrize('value,expected',[('안산시','경기'),('경기도 안산시','경기'),('서울특별시 강남구','서울'),('경남 창원시','경남'),('전북특별자치도','전북'),('중구',None),('부산동',None),(None,None),('안산동',None)])
def test_no_ambiguous_region_guess(value,expected):assert province_for(value)==expected

def test_explicit_region_supplement(catalog):
    r=rec(catalog,Supplement(province='서울'))
    assert r['province']=='서울' and row(r,'SEOUL-HOPE-DOUBLE')['bucket']=='WATCHLIST'
    assert row(r,'GG-YOUTH-WORKER')['bucket']=='NOT_MATCHED'

@pytest.mark.parametrize('identifier',['KR-YOUTH-FUTURE','BUSAN-JOY-DOUBLE','INCHEON-DREAM-FOR','GN-MODADREAM','DAEJEON-FUTURE-DOUBLE','JB-TOGETHER-DOUBLE'])
@pytest.mark.parametrize('edge',['minimum','maximum','too_young'])
def test_existing_birth_evaluator_boundaries(catalog,identifier,edge):
    p=program(catalog,identifier)
    birth=p.birth_from if edge=='minimum' else p.birth_to if edge=='maximum' else (datetime.fromisoformat(p.birth_to)+timedelta(days=1)).date().isoformat()
    c=next(x for x in row(rec(catalog,Supplement(birth_date=birth)),identifier)['assessment']['checks'] if x['key']=='age')
    assert c['status']==('FAIL' if edge=='too_young' else 'PASS')

def test_current_age_not_used_for_historical_reference(catalog):
    c=next(x for x in row(rec(catalog),'BUSAN-JOY-DOUBLE')['assessment']['checks'] if x['key']=='age')
    assert c['status']=='UNKNOWN'

def test_military_exception_not_silently_failed(catalog):
    c=next(x for x in row(rec(catalog,Supplement(birth_date='1990-01-01')),'KR-YOUTH-FUTURE')['assessment']['checks'] if x['key']=='age')
    assert c['status']=='UNKNOWN'

@pytest.mark.parametrize('age,expected',[(18,'FAIL'),(19,'PASS'),(34,'PASS'),(35,'UNKNOWN'),(None,'UNKNOWN')])
def test_continuous_current_age_rule(catalog,age,expected):
    c=next(x for x in row(rec(catalog,age=age),'KR-YOUTH-HOUSING')['assessment']['checks'] if x['key']=='age')
    assert c['status']==expected

@pytest.mark.parametrize('owns,expected',[(True,'FAIL'),(False,'PASS'),(None,'UNKNOWN')])
def test_home_ownership_not_assumed(catalog,owns,expected):
    c=next(x for x in row(rec(catalog,Supplement(owns_home=owns)),'KR-YOUTH-HOUSING')['assessment']['checks'] if x['key']=='home')
    assert c['status']==expected

@pytest.mark.parametrize('capacity,expected',[(0,'FAIL'),(19999,'FAIL'),(20000,'PASS'),(300000,'PASS'),(1000001,'PASS')])
def test_budget_is_distinct_from_eligibility(catalog,capacity,expected):
    r=row(rec(catalog,capacity=capacity),'KR-YOUTH-HOUSING')
    assert r['assessment']['budget']['status']==expected and r['assessment']['status']=='UNKNOWN'
    if capacity==1000001:assert r['assessment']['allocation_krw']==1000000 and r['assessment']['unallocated_capacity_krw']==1

def test_income_never_repurposed(catalog):
    a=rec(catalog,monthly_income=1500000);b=rec(catalog,monthly_income=9000000)
    assert [r['assessment']['remaining_checks'] for r in a['programs']]==[r['assessment']['remaining_checks'] for r in b['programs']]
    assert all(c['status']=='UNKNOWN' for r in b['programs'] for c in r['assessment']['remaining_checks'])

def test_pending_housing_income_change_stays_unknown(catalog):
    p=program(catalog,'KR-YOUTH-HOUSING')
    assert '시행' in p.income_note and '5천' in p.income_note and '7천' in p.income_note
    assert row(rec(catalog,Supplement(owns_home=False,birth_date='2002-01-01')),'KR-YOUTH-HOUSING')['assessment']['status']=='UNKNOWN'

def test_unknown_minimum_does_not_become_zero(catalog):
    r=row(rec(catalog),'KR-YOUTH-FUTURE')
    assert r['assessment']['budget']['status']=='UNKNOWN' and r['assessment']['allocation_krw'] is None

def test_goal_mismatch_visible_without_altering_term(catalog):
    r=row(discover(catalog,NOW,SimulationInput(**PROFILE),Supplement(province='부산'),300000,12),'BUSAN-JOY-DOUBLE')
    assert r['assessment']['goal_matches'] is False and r['program']['term_months']==[24,36]

def test_input_immutability_and_reproducibility(catalog):
    p=SimulationInput(**PROFILE);s=Supplement(birth_date='2002-01-01')
    original=(catalog.model_dump_json(),p.model_dump_json(),s.model_dump_json())
    assert discover(catalog,NOW,p,s,300000)==discover(catalog,NOW,p,s,300000)
    assert original==(catalog.model_dump_json(),p.model_dump_json(),s.model_dump_json())

@pytest.mark.parametrize('birth',['2026-10-31','1800-01-01'])
def test_birth_context_rejected(catalog,birth):
    with pytest.raises(ValueError):rec(catalog,Supplement(birth_date=birth))

@pytest.mark.parametrize('birth',['2000-02-30','2000/01/01','20000101'])
def test_strict_birth_dates(birth):
    with pytest.raises(ValidationError):Supplement(birth_date=birth)

def test_public_results_and_notification_boundary(catalog):
    r=discover(catalog,NOW)
    assert not r['personalized'] and r['monthly_capacity'] is None
    assert all(x['assessment'] is None and x['calculation'] is None and x['benefit_applied_krw']==0 for x in r['programs'])
    assert r['notifications']['delivery_enabled'] is False and r['notifications']['subscriptions_stored'] is False

@pytest.mark.parametrize('mutation',['url','duplicate','missing_source','full_coverage','time','range','unknown_window'])
def test_corrupt_catalog_rejected(catalog,mutation):
    d=raw(catalog)
    if mutation=='url':d['sources'][0]['url']='https://www.korea.kr@evil.example/policy'
    elif mutation=='duplicate':d['programs'].append(copy.deepcopy(d['programs'][0]))
    elif mutation=='missing_source':d['programs'][0]['source_ids']=['not-found']
    elif mutation=='full_coverage':d['programs'][0]['remaining_checks']=[]
    elif mutation=='time':d['programs'][0]['windows'][0]['starts_at']='2026-10-07T00:00:00'
    elif mutation=='range':d['programs'][0]['birth_to']='1800-01-01'
    else:d['programs'][0]['schedule_kind']='UNKNOWN'
    with pytest.raises(ValidationError):revalidate(d)

def test_bad_loader_files(tmp_path):
    p=tmp_path/'bad.json';p.write_text('{"schema_version":1,"schema_version":2}')
    with pytest.raises(CatalogError):load_catalog(p)
    with pytest.raises(CatalogError):load_catalog(tmp_path/'missing')

def test_identical_snapshot_emits_nothing(catalog):assert diff_catalogs(catalog,catalog,previous_at=NOW,current_at=NOW)==()

def test_retrieval_changes_are_not_policy_events(catalog):
    d=raw(catalog)
    for s in d['sources']:s['verified_on']='2026-10-31';s['capture_sha256']='f'*64
    assert diff_catalogs(catalog,revalidate(d),previous_at=NOW,current_at=NOW+timedelta(days=1))==()

@pytest.mark.parametrize('kind',['PROGRAM_ADDED','PROGRAM_REMOVED','PROGRAM_UPDATED'])
def test_stable_public_change_events_not_sent(catalog,kind):
    d=raw(catalog)
    if kind=='PROGRAM_ADDED':d['programs'].append(d['programs'][0]|dict(program_id='SYNTHETIC-ADDED'))
    elif kind=='PROGRAM_REMOVED':d['programs'].pop()
    else:d['programs'][0]['benefit_summary']='합성 변경 시험'
    c=revalidate(d);events=diff_catalogs(catalog,c,previous_at=NOW,current_at=NOW)
    assert len(events)==1 and events[0]['kind']==kind and events[0]['delivery_status']=='NOT_SENT'
    assert events==diff_catalogs(catalog,c,previous_at=NOW,current_at=NOW)
    assert 'profile' not in events[0] and len(events[0]['event_id'])==64

def test_deadline_change_event(catalog):
    c=checked(catalog,'2026-10-08')
    before=datetime.fromisoformat('2026-10-08T17:59:59+09:00')
    e=next(x for x in diff_catalogs(c,c,previous_at=before,current_at=before+timedelta(seconds=1)) if x['program_id']=='DAEJEON-FUTURE-DOUBLE')
    assert e['kind']=='INTAKE_STATUS_CHANGED' and e['previous_status']=='OPEN' and e['current_status']=='CLOSED'

def test_event_time_must_be_monotonic(catalog):
    with pytest.raises(ValueError):diff_catalogs(catalog,catalog,previous_at=NOW,current_at=NOW-timedelta(seconds=1))

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(web,'now',lambda:NOW)
    return TestClient(app)

def test_public_and_personal_api_no_store(client):
    r=client.get('/api/asset-programs')
    assert r.status_code==200 and r.headers['cache-control']=='no-store' and r.json()['program_count']==10
    r=client.post('/api/asset-programs/recommendations',json=dict(profile=PROFILE,goal_months=12))
    assert r.status_code==200 and r.headers['cache-control']=='no-store'
    assert r.json()['monthly_capacity']==300000 and r.json()['policy_benefit_applied_krw']==0 and 'input_summary' not in r.json()

def test_after_region_change_clears_before_override(client):
    r=client.post('/api/asset-programs/recommendations',json=dict(profile=PROFILE,after_profile=PROFILE|dict(region='서울특별시',user_savings_capacity=0),supplement=dict(province='경기'))).json()
    assert r['province']=='경기' and r['after']['province']=='서울' and r['after']['monthly_capacity']==0

@pytest.mark.parametrize('extra',[{'capacity':999},{'policy_benefit_applied_krw':100000},{'goal_months':True},{'supplement':{'household_income':100}}])
def test_no_client_amount_or_wrong_income_basis(client,extra):
    r=client.post('/api/asset-programs/recommendations',json=dict(profile=PROFILE)|extra)
    assert r.status_code==422 and '1500000' not in r.text

def test_catalog_outage_is_not_no_matches(client,monkeypatch):
    monkeypatch.setattr(web,'load_catalog',lambda:(_ for _ in ()).throw(CatalogError()))
    r=client.get('/api/asset-programs')
    assert r.status_code==503 and r.headers['cache-control']=='no-store'

def test_error_does_not_echo_birth(client):
    r=client.post('/api/asset-programs/recommendations',json=dict(profile=PROFILE,supplement=dict(birth_date='2030-01-01')))
    assert r.status_code==422 and '2030-01-01' not in r.text

