import base64,copy,json
from datetime import datetime,timedelta
from pathlib import Path
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from backend.asset_alerts.sources import KST,parse_notice,notice_status,content,links,validate_url
from backend.asset_alerts.runtime import Store,Monitor,matches,INTERVAL
from backend.asset_alerts.delivery import PushSender,validate_subscription,push_url,NoRedirect

NOW=datetime(2026,10,30,12,tzinfo=KST)
P=[dict(program_id='P1',title='희망두배 청년통장',regions=['서울'],aliases=['희망두배'])]
PREF=dict(regions=['서울'],programs=[],national=False,all_regions=False,inbox=True,browser=False)
URL='https://news.seoul.go.kr/welfare/archives/123'
def html(schedule='2026.10.30 09:00 ~ 2026.11.10 18:00',label='신청기간',title='2026년 희망두배 청년통장 참여자 모집'):
    return f'<html><head><title>{title}</title></head><body><div id="post_content"><p>공식 사업 모집 안내 및 가입조건은 별도 공고문 확인</p><p>{label}: {schedule}</p></div></body></html>'.encode()
def parsed(body=None,now=NOW):return parse_notice(body or html(),URL,'2026년 희망두배 청년통장 참여자 모집',P,now,'#post_content')
def subscription():
    key=ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    enc=lambda b:base64.urlsafe_b64encode(b).decode().rstrip('=')
    return dict(endpoint='https://fcm.googleapis.com/wp/synthetic-test-only-'+enc(key[:12]),keys=dict(p256dh=enc(key),auth=enc(b'1234567890abcdef')))

def test_explicit_date_time_exact_and_unknown_preserved():
    n=parsed();assert n['starts_at']=='2026-10-30T09:00:00+09:00';assert n['ends_at_exclusive']=='2026-11-10T18:00:00+09:00'
    assert n['eligibility_status']=='UNKNOWN' and n['financial_calculation_available'] is False
    assert n['regions']==['서울'] and n['scope']=='REGIONAL'
@pytest.mark.parametrize('text',['2026. 10. 30.(금) 09:00 ~ 2026. 11. 10.(화) 18:00','2026년 10월 30일 09:00 ~ 11월 10일 18:00','2026-10-30 09:00 ~ 2026-11-10 18:00','2026/10/30 09:00 ~ 11/10 18:00'])
def test_supported_official_date_forms(text):assert parsed(html(text)) is not None
def test_date_only_is_explicit_and_end_is_exclusive():
    n=parsed(html('10.30~11.10'));assert n['date_only'] and n['start_date_only'];assert n['ends_at_exclusive']=='2026-11-11T00:00:00+09:00'
def test_24_hour_boundary():assert parsed(html('2026.10.30 09:00~2026.11.10 24:00'))['ends_at_exclusive']=='2026-11-11T00:00:00+09:00'
@pytest.mark.parametrize('label',['선정기간','심사기간','계좌개설 기간','교육기간','생년월일'])
def test_other_dates_never_become_application_period(label):assert parsed(html(label=label)) is None
@pytest.mark.parametrize('text',['2026.10.40 ~ 2026.11.10','2026.11.10 ~ 2026.10.30','2026.10.30 오전 9:00 ~ 2026.11.10 오후 6:00','추후 안내','예정 2026.10.30~11.10','2026.10.30~2026.11.10 예정','2026.10.30 25:00~2026.11.10 18:00'])
def test_ambiguous_or_invalid_period_is_held(text):assert parsed(html(text)) is None
def test_two_conflicting_application_periods_are_held():assert parsed(html().replace(b'</div>','<p>신청기간: 2026.11.1~11.20</p></div>'.encode())) is None
def test_missing_year_does_not_use_current_year():assert parse_notice(html('10.30~11.10'),URL,'희망두배 청년통장 모집',P,NOW,'#post_content') is None
@pytest.mark.parametrize('title',['2026년 희망두배 청년통장 계좌개설 안내','2026년 희망두배 청년통장 모집 마감','2026년 희망두배 청년통장 교육 모집','2026년 희망두배 청년통장 미운영'])
def test_nonrecruitment_title_held(title):assert parse_notice(html(),URL,title,P,NOW) is None
def test_unknown_program_is_notice_only_and_region_unconfirmed():
    n=parse_notice(html(),URL,'2026년 청년 새희망적금 참여자 모집',P,NOW)
    assert n['program_id'].startswith('DISCOVERED-') and n['scope']=='UNCONFIRMED' and n['eligibility_status']=='UNKNOWN'
@pytest.mark.parametrize('now,expected',[(NOW.replace(hour=8),'UPCOMING'),(NOW.replace(hour=9),'OPEN'),(datetime(2026,11,10,18,tzinfo=KST),'CLOSED')])
def test_status_respects_source_freshness(now,expected):assert notice_status(parsed(),now)==expected
def test_end_exact_boundary_and_stale_source():
    n=parsed();n['verified_at']='2026-11-10T12:00:00+09:00'
    assert notice_status(n,datetime(2026,11,10,17,59,tzinfo=KST))=='OPEN'
    assert notice_status(n,datetime(2026,11,10,18,tzinfo=KST))=='CLOSED'
def test_semantic_hash_ignores_scripts_not_material_images():
    assert content(html()+b'<script>random123</script>','#post_content')[0]==content(html(),'#post_content')[0]
    assert content(html().replace(b'</div>',b'<img src="new.png"></div>'),'#post_content')[0]!=content(html(),'#post_content')[0]
def test_missing_selector_is_not_success():
    with pytest.raises(ValueError):content(html(),'#missing')
@pytest.mark.parametrize('url',['http://news.seoul.go.kr/a','https://news.seoul.go.kr.evil.example/a','https://news.seoul.go.kr@127.0.0.1/a','https://127.0.0.1/','https://news.seoul.go.kr:444/a','https://news.seoul.go.kr/a#fragment'])
def test_source_url_allowlist(url):
    with pytest.raises(ValueError):validate_url(url,{'news.seoul.go.kr'})
def test_listing_does_not_follow_arbitrary_links():
    page='<a href="https://evil.test/1">2026 청년 적금 모집</a><a href="/welfare/archives/12">2026 청년 적금 모집</a><a href="/login">2026 청년 통장 모집</a>'.encode()
    assert links(page,URL,P,{'news.seoul.go.kr'})==[('https://news.seoul.go.kr/welfare/archives/12','2026 청년 적금 모집')]

@pytest.mark.parametrize('prefs,expected',[(PREF,True),(PREF|{'regions':['경기']},False),(PREF|{'regions':[],'programs':['P1']},True),(PREF|{'regions':[],'all_regions':True},True),(PREF|{'regions':[],'national':True},False)])
def test_interest_matching_union(prefs,expected):assert matches(prefs,parsed()) is expected
def test_national_interest_and_unknown_scope():
    n=parsed();n['regions']=[];n['scope']='NATIONAL';assert matches(PREF|{'national':True},n)
    n['scope']='UNCONFIRMED';assert not matches(PREF|{'national':True},n)
def test_token_privacy_persistence_isolation_and_delete(tmp_path):
    store=Store(tmp_path/'state.sqlite3');a=store.subscribe(PREF);b=store.subscribe(PREF)
    assert len(a['token'])==43 and a['token']!=b['token']
    store.publish(parsed(),'NEW_RECRUITMENT',NOW.replace(year=2027))
    # Test timestamps use real request time for subscription expiry.
    store.test(a['token']);assert len(store.inbox(a['token']))==1 and not store.inbox(b['token'])
    store.mark_read(a['token'],'all');assert store.inbox(a['token'])[0]['is_read']
    assert a['token'] not in (tmp_path/'state.sqlite3').read_bytes().decode('latin1')
    store.delete(a['token'])
    with pytest.raises(PermissionError):store.settings(a['token'])
    assert Store(tmp_path/'state.sqlite3').settings(b['token'])['preferences']==PREF
def test_duplicate_event_and_unsubscribe(tmp_path):
    store=Store(tmp_path/'s.db');a=store.subscribe(PREF);now=datetime.now(KST)
    store.publish(parsed(),'NEW_RECRUITMENT',now);store.publish(parsed(),'NEW_RECRUITMENT',now)
    assert len(store.inbox(a['token']))==1
    store.delete(a['token']);store.publish(parsed(),'RECRUITMENT_STARTED',now)
    with store.db() as db:assert db.execute('SELECT count(*) FROM inbox').fetchone()[0]==0
def test_subscription_update_does_not_make_new_identity(tmp_path):
    store=Store(tmp_path/'s.db');a=store.subscribe(PREF);store.subscribe(PREF|{'regions':['경기']},token=a['token'])
    assert store.settings(a['token'])['preferences']['regions']==['경기']
def test_test_rate_limit(tmp_path):
    store=Store(tmp_path/'s.db');a=store.subscribe(PREF);store.test(a['token'])
    with pytest.raises(ValueError,match='TEST_RATE_LIMIT'):store.test(a['token'])
def test_expired_subscriptions_and_records_are_removed(tmp_path):
    store=Store(tmp_path/'s.db');a=store.subscribe(PREF);store.test(a['token']);store.purge(datetime.now(KST)+timedelta(days=91))
    with store.db() as db:assert db.execute('SELECT count(*) FROM subscribers').fetchone()[0]==0 and db.execute('SELECT count(*) FROM inbox').fetchone()[0]==0
@pytest.mark.parametrize('url',['https://127.0.0.1/push','http://fcm.googleapis.com/wp/a','https://fcm.googleapis.com.evil.example/a','https://fcm.googleapis.com:444/a','https://fcm.googleapis.com@localhost/a','https://fcm.googleapis.com/wp/a#x'])
def test_push_endpoint_allowlist(url):
    with pytest.raises(ValueError):push_url(url)
def test_valid_keys_and_duplicate_endpoint_ownership(tmp_path):
    sub=subscription();assert validate_subscription(sub)['endpoint']==sub['endpoint']
    store=Store(tmp_path/'s.db');store.subscribe(PREF|{'browser':True},sub)
    with pytest.raises(ValueError,match='PUSH_ALREADY_REGISTERED'):store.subscribe(PREF|{'browser':True},sub)
@pytest.mark.parametrize('mutate',[lambda s:s.update(keys={}),lambda s:s['keys'].update(auth='invalid'),lambda s:s.update(endpoint='https://localhost/'),lambda s:s.update(secret='extra')])
def test_invalid_push_subscription(mutate):
    sub=subscription();mutate(sub)
    with pytest.raises(ValueError):validate_subscription(sub)
def test_real_webpush_encryption_without_network(tmp_path,monkeypatch):
    captured={}
    class Response:status_code=201;text='';headers={}
    def post(self,url,**kwargs):captured.update(kwargs);return Response()
    monkeypatch.setattr(NoRedirect,'post',post)
    sender=PushSender(tmp_path/'private.pem');payload={'title':'synthetic encrypted TEST','body':'no personal profile','id':'test'}
    assert sender.send(subscription(),payload)=='PUSH_ACCEPTED'
    assert isinstance(captured['data'],bytes) and b'synthetic encrypted TEST' not in captured['data']
    assert 'authorization' in {k.lower() for k in captured['headers']}
    assert PushSender(tmp_path/'private.pem').public_key==sender.public_key

class FakeSender:
    public_key='test-public-key'
    def __init__(self):self.calls=[]
    def send(self,sub,payload):self.calls.append(payload);return 'PUSH_ACCEPTED'
def monitor(tmp_path,page=None):
    original=html('2026.10.1~10.2');pages={'body':page or original}
    config=dict(hosts=['news.seoul.go.kr'],programs=P,sources=[dict(id='test',url=URL,title='2026년 희망두배 청년통장 모집',selector='#post_content',reference_sha256=content(original,'#post_content')[0])])
    def fetcher(url,hosts):return pages['body'],'text/html'
    return Monitor(tmp_path,config,fetcher,FakeSender()),pages
def test_monitor_bootstrap_new_notice_exactly_once_and_wrong_region(tmp_path):
    m,pages=monitor(tmp_path);first=m.cycle(NOW,force=True);assert first['bootstrap']
    a=m.store.subscribe(PREF);b=m.store.subscribe(PREF|{'regions':['경기']})
    pages['body']=html();m.cycle(NOW+timedelta(hours=1),force=True)
    assert len(m.store.inbox(a['token']))==1 and not m.store.inbox(b['token'])
    m.cycle(NOW+timedelta(hours=2),force=True);assert len(m.store.inbox(a['token']))==1
def test_monitor_first_run_does_not_spam_current_recruitment(tmp_path):
    m,_=monitor(tmp_path,html());a=m.store.subscribe(PREF);m.cycle(NOW,force=True);assert not m.store.inbox(a['token'])
def test_scheduled_start_and_failure_are_separate(tmp_path):
    m,pages=monitor(tmp_path,html('2026.10.31 09:00~2026.11.10 18:00'));m.cycle(NOW,force=True);a=m.store.subscribe(PREF)
    m.cycle(NOW+timedelta(days=1),force=True);assert m.store.inbox(a['token'])[0]['kind']=='RECRUITMENT_STARTED'
    before=len(m.store.inbox(a['token']));pages['body']=html('추후 안내');m.cycle(NOW+timedelta(days=2),force=True)
    assert len(m.store.inbox(a['token']))==before+1 and m.store.inbox(a['token'])[0]['kind']=='NOTICE_RECHECK_REQUIRED'
def test_not_due_and_existing_lease_are_respected(tmp_path):
    m,_=monitor(tmp_path);m.cycle(NOW);assert m.cycle(NOW+timedelta(minutes=1))['status']=='NOT_DUE'
    lease=(NOW+timedelta(minutes=30)).isoformat();m.store.set_meta('lease',lease)
    assert m.cycle(NOW,force=True)['status']=='ALREADY_RUNNING' and m.store.meta('lease')==lease
def test_source_failure_cannot_renew_verification_or_notify(tmp_path):
    m,_=monitor(tmp_path);m.cycle(NOW,force=True)
    m.fetcher=lambda *a:(_ for _ in ()).throw(OSError('synthetic outage'))
    result=m.cycle(NOW+timedelta(hours=6),force=True)
    assert result['status']=='FAILED' and not m.verified_sources()['test']['reference_verified']
def test_webpush_delivery_dedup_delete_and_bounded_retry(tmp_path):
    m,_=monitor(tmp_path);a=m.store.subscribe(PREF|{'browser':True},subscription());m.store.test(a['token']);m.deliver();m.deliver()
    assert len(m.sender.calls)==1 and m.store.inbox(a['token'])[0]['push_state']=='PUSH_ACCEPTED'
    m.store.delete(a['token']);assert not m.deliver()

@pytest.fixture
def client(tmp_path,monkeypatch):
    import backend.web.asset_alerts as web
    from backend.web.app import app
    m,_=monitor(tmp_path);monkeypatch.setattr(web,'get_monitor',lambda:m);monkeypatch.setenv('ASSET_ALERTS_AUTO_REFRESH','0')
    with TestClient(app) as client:yield client,m
def req_headers(token=None,origin='http://127.0.0.1:5173'):
    return {'X-AIX-Client':'asset-alerts-v1','Origin':origin}|({'Authorization':'Bearer '+token} if token else {})
def register(client,prefs=PREF):
    r=client.post('/api/asset-alerts/subscriptions',headers=req_headers(),json={'preferences':prefs,'push':None});assert r.status_code==200;return r.json()['token']
def test_status_is_public_and_never_exposes_subscriber_or_key(client):
    c,m=client;token=register(c);data=c.get('/api/asset-alerts/status').json()
    assert data['schema_version']=='asset-alerts-v1' and token not in json.dumps(data)
    assert 'private' not in json.dumps(data) and data['email_available'] is False
def test_api_real_storage_test_read_and_delete(client):
    c,m=client;t=register(c);h=req_headers(t)
    assert c.get('/api/asset-alerts/subscription',headers=h).json()['preferences']==PREF
    assert c.post('/api/asset-alerts/test',headers=h).status_code==200
    assert c.post('/api/asset-alerts/test',headers=h).status_code==429
    rows=c.get('/api/asset-alerts/inbox',headers=h).json()['items'];assert len(rows)==1 and rows[0]['kind']=='TEST'
    c.post('/api/asset-alerts/inbox/all/read',headers=h);assert c.get('/api/asset-alerts/inbox',headers=h).json()['items'][0]['is_read']
    assert c.delete('/api/asset-alerts/subscription',headers=h).status_code==200
    assert c.get('/api/asset-alerts/inbox',headers=h).status_code==401
@pytest.mark.parametrize('path,method',[('/inbox','GET'),('/subscription','GET'),('/subscription','DELETE'),('/test','POST')])
def test_api_auth_required(client,path,method):
    c,m=client;assert c.request(method,'/api/asset-alerts'+path,headers=req_headers()).status_code==401
def test_cross_origin_mutations_rejected(client):
    c,m=client;assert c.post('/api/asset-alerts/subscriptions',headers=req_headers(origin='https://evil.example'),json={'preferences':PREF}).status_code==403
    assert c.post('/api/asset-alerts/subscriptions',json={'preferences':PREF}).status_code==403
@pytest.mark.parametrize('prefs',[PREF|{'regions':['없는지역']},PREF|{'programs':['UNKNOWN']},PREF|{'regions':[]},PREF|{'inbox':False},PREF|{'browser':True},PREF|{'regions':['서울','서울']}])
def test_invalid_preferences_do_not_create_subscribers(client,prefs):
    c,m=client;assert c.post('/api/asset-alerts/subscriptions',headers=req_headers(),json={'preferences':prefs,'push':None}).status_code==422
def test_profile_input_cannot_be_persisted_by_subscription_api(client):
    c,m=client;r=c.post('/api/asset-alerts/subscriptions',headers=req_headers(),json={'preferences':PREF,'monthly_income':1234567})
    assert r.status_code==422 and '1234567' not in r.text
def test_two_api_users_cannot_read_each_others_items(client):
    c,m=client;a=register(c);b=register(c);c.post('/api/asset-alerts/test',headers=req_headers(a))
    assert not c.get('/api/asset-alerts/inbox',headers=req_headers(b)).json()['items']

@pytest.mark.parametrize('value',[None,1,{},[],True])
def test_push_endpoint_type_is_rejected(value):
    with pytest.raises(ValueError):push_url(value)
def test_next_cycle_runs_after_six_hours_and_survives_restart(tmp_path):
    m,_=monitor(tmp_path);m.cycle(NOW)
    restarted,_=monitor(tmp_path)
    assert restarted.cycle(NOW+timedelta(seconds=INTERVAL-1))['status']=='NOT_DUE'
    assert restarted.cycle(NOW+timedelta(seconds=INTERVAL))['status']=='OK'
def test_notice_withdrawal_invalidates_old_schedule_once(tmp_path):
    m,pages=monitor(tmp_path,html());m.cycle(NOW,force=True);a=m.store.subscribe(PREF)
    pages['body']=html('추후 안내');m.cycle(NOW+timedelta(hours=1),force=True)
    assert m.public(NOW+timedelta(hours=1))['notices'][0]['status']=='REVIEW_REQUIRED'
    assert m.store.inbox(a['token'])[0]['kind']=='NOTICE_RECHECK_REQUIRED'
    m.cycle(NOW+timedelta(hours=2),force=True);assert len(m.store.inbox(a['token']))==1
def test_push_expiration_disables_dead_endpoint(tmp_path):
    m,_=monitor(tmp_path);a=m.store.subscribe(PREF|{'browser':True},subscription());m.store.test(a['token'])
    m.sender.send=lambda *args:'EXPIRED';m.deliver()
    assert m.store.settings(a['token'])['push_registered'] is False
    assert m.store.inbox(a['token'])[0]['push_state']=='EXPIRED';assert not m.deliver()
def test_failed_deliveries_are_bounded(tmp_path):
    m,_=monitor(tmp_path);a=m.store.subscribe(PREF|{'browser':True},subscription());m.store.test(a['token']);count=[]
    def fail(*args):count.append(1);return 'FAILED'
    m.sender.send=fail
    for _ in range(5):m.deliver()
    assert len(count)==3 and m.store.inbox(a['token'])[0]['push_state']=='FAILED'
def test_test_delivery_only_targets_the_requested_message(tmp_path):
    m,_=monitor(tmp_path);a=m.store.subscribe(PREF|{'browser':True},subscription());b=m.store.subscribe(PREF|{'browser':True},subscription())
    m.store.test(a['token']);m.store.test(b['token']);target=m.store.inbox(b['token'])[0]['id']
    m.deliver(only_id=target);assert len(m.sender.calls)==1
    assert m.store.inbox(a['token'])[0]['push_state']=='PENDING'
def test_push_requests_do_not_follow_redirects(monkeypatch):
    import requests
    seen={}
    def request(self,*args,**kwargs):seen.update(kwargs);return object()
    monkeypatch.setattr(requests.Session,'request',request)
    NoRedirect().request('POST','https://fcm.googleapis.com/wp/test',allow_redirects=True)
    assert seen['allow_redirects'] is False
def test_verified_source_overlay_never_changes_financial_or_eligibility_rules(monkeypatch):
    from backend.opportunities.catalog import load_catalog
    from backend.asset_alerts import catalog_view
    c=load_catalog();monkeypatch.setattr(catalog_view,'states',lambda:{'future':dict(reference_verified=True,last_success_at='2026-10-31T12:00:00+09:00')})
    updated=catalog_view.current_catalog(c)
    assert updated.programs==c.programs and next(s for s in updated.sources if s.source_id=='future').verified_on=='2026-10-31'
def test_changed_official_terms_remove_current_recommendation_without_changing_money(monkeypatch):
    from backend.opportunities.catalog import load_catalog
    from backend.opportunities.matching import discover
    from backend.asset_alerts import catalog_view
    c=load_catalog();d=discover(c,NOW)
    monkeypatch.setattr(catalog_view,'states',lambda:{'housing-bank':dict(status='CHANGED_REVIEW_REQUIRED',reference_verified=False)})
    updated=catalog_view.live_response(d)
    row=next(r for r in updated['programs'] if r['program']['program_id']=='KR-YOUTH-HOUSING')
    assert row['intake']['status']=='REVIEW_REQUIRED' and updated['counts']['OPEN']==0
    assert row['calculation'] is None and row['benefit_applied_krw']==0
def test_worker_heartbeat_and_exit_without_external_scheduler(tmp_path,monkeypatch):
    import asyncio
    import backend.asset_alerts.runtime as runtime
    m,_=monitor(tmp_path);monkeypatch.setattr(runtime,'get_monitor',lambda:m)
    async def run():
        loop=asyncio.get_running_loop();stop=asyncio.Event();calls=[]
        def cycle():calls.append(1);loop.call_soon_threadsafe(stop.set)
        m.cycle=cycle;await runtime.run_worker(stop)
        assert len(calls)==1 and m.store.meta('worker_heartbeat')
    asyncio.run(run())
def test_all_product_tabs_are_fingerprinted_while_navigation_is_excluded():
    a=b'<html><body><nav>counter1</nav><div id="one">Basic official product conditions and income</div><div id="two">Full official terms, payments and eligibility</div></body></html>'
    original=content(a,'#one,#two')[0]
    assert content(a.replace(b'counter1',b'counter2'),'#one,#two')[0]==original
    assert content(a.replace(b'payments',b'payments CHANGED'),'#one,#two')[0]!=original
def test_missing_any_required_product_tab_is_layout_failure():
    with pytest.raises(ValueError,match='SOURCE_LAYOUT_CHANGED'):content(html(),'#post_content,#missing')
