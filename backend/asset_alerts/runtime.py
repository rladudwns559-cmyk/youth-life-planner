"""Local persistent subscriptions, source checks, inbox and bounded delivery.

No income, rent, birthday or policy decisions are stored here. Runtime data is
private and excluded from source/evidence exports. No OS startup registration.
"""
import json,os,secrets,sqlite3,threading,time
from contextlib import contextmanager
from datetime import datetime,timedelta
from pathlib import Path
from .sources import stamp,sha,KST,fetch,content,links,parse_notice,notice_status
from .delivery import PushSender,validate_subscription

PROJECT=Path(__file__).resolve().parents[2]
DEFAULT_STATE=PROJECT/'tmp/asset-alerts-runtime'
CONFIG_PATH=PROJECT/'data/asset-programs/monitor-sources.json'
INTERVAL=21600

class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        with self.db() as db:db.executescript('''
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS notices(id TEXT PRIMARY KEY,payload TEXT NOT NULL,last_status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS subscribers(id TEXT PRIMARY KEY,token_hash TEXT UNIQUE NOT NULL,prefs TEXT NOT NULL,push TEXT,created_at TEXT NOT NULL,expires_at TEXT NOT NULL,last_test TEXT);
            CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY,subscriber TEXT NOT NULL,event_key TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL,is_read INTEGER NOT NULL DEFAULT 0,push_state TEXT NOT NULL DEFAULT 'NOT_REQUESTED',attempts INTEGER NOT NULL DEFAULT 0,UNIQUE(subscriber,event_key));
            CREATE INDEX IF NOT EXISTS inbox_owner ON inbox(subscriber,created_at);
        ''')
    @contextmanager
    def db(self):
        with self.lock:
            db=sqlite3.connect(self.path,timeout=5)
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA secure_delete=ON')
            try:
                with db:yield db
            finally:db.close()
    def meta(self,key):
        with self.db() as db:
            row=db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
            return json.loads(row[0]) if row else None
    def set_meta(self,key,value):
        with self.db() as db:db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',(key,json.dumps(value)))
    def subscriber(self,token,now=None):
        if not isinstance(token,str) or len(token)!=43:raise PermissionError('SUBSCRIPTION_NOT_FOUND')
        with self.db() as db:
            row=db.execute('SELECT * FROM subscribers WHERE token_hash=?',(sha(token),)).fetchone()
            if row is None or row['expires_at']<=(now or stamp()):raise PermissionError('SUBSCRIPTION_NOT_FOUND')
            return dict(row)
    def subscribe(self,prefs,push=None,token=None):
        now=datetime.now(KST);expiry=(now+timedelta(days=90)).isoformat()
        if push is not None:push=validate_subscription(push)
        with self.db() as db:
            old=self.subscriber(token) if token else None
            if push:
                # Endpoint ownership cannot silently move between anonymous tokens.
                rows=db.execute('SELECT id,push FROM subscribers WHERE push IS NOT NULL').fetchall()
                if any(r['id']!=(old or {}).get('id') and json.loads(r['push'])['endpoint']==push['endpoint'] for r in rows):raise ValueError('PUSH_ALREADY_REGISTERED')
            if old:
                identifier=old['id']
                db.execute('UPDATE subscribers SET prefs=?,push=?,expires_at=? WHERE id=?',(json.dumps(prefs),json.dumps(push) if push else None,expiry,identifier))
                if not prefs['browser']:db.execute("UPDATE inbox SET push_state='DISABLED' WHERE subscriber=? AND push_state IN ('PENDING','FAILED')",(identifier,))
            else:
                if db.execute('SELECT count(*) FROM subscribers').fetchone()[0]>=5000:raise ValueError('SUBSCRIPTION_CAPACITY')
                token=secrets.token_urlsafe(32);identifier=secrets.token_hex(16)
                db.execute('INSERT INTO subscribers(id,token_hash,prefs,push,created_at,expires_at) VALUES(?,?,?,?,?,?)',(identifier,sha(token),json.dumps(prefs),json.dumps(push) if push else None,now.isoformat(),expiry))
        return dict(token=token,preferences=prefs,push_registered=push is not None,expires_at=expiry)
    def settings(self,token):
        row=self.subscriber(token)
        return dict(preferences=json.loads(row['prefs']),push_registered=row['push'] is not None,expires_at=row['expires_at'])
    def delete(self,token):
        row=self.subscriber(token)
        with self.db() as db:
            db.execute('DELETE FROM inbox WHERE subscriber=?',(row['id'],))
            db.execute('DELETE FROM subscribers WHERE id=?',(row['id'],))
    def inbox(self,token):
        row=self.subscriber(token)
        with self.db() as db:
            rows=db.execute('SELECT id,payload,created_at,is_read,push_state FROM inbox WHERE subscriber=? ORDER BY created_at DESC,id DESC LIMIT 100',(row['id'],)).fetchall()
        return [dict(json.loads(r['payload']),id=r['id'],created_at=r['created_at'],is_read=bool(r['is_read']),push_state=r['push_state']) for r in rows]
    def mark_read(self,token,identifier):
        row=self.subscriber(token)
        with self.db() as db:
            if identifier=='all':db.execute('UPDATE inbox SET is_read=1 WHERE subscriber=?',(row['id'],))
            else:db.execute('UPDATE inbox SET is_read=1 WHERE subscriber=? AND id=?',(row['id'],identifier))
    def test(self,token,now=None):
        row=self.subscriber(token);now=now or datetime.now(KST)
        with self.db() as db:
            if row['last_test'] and now-datetime.fromisoformat(row['last_test'])<timedelta(seconds=60):raise ValueError('TEST_RATE_LIMIT')
            db.execute('UPDATE subscribers SET last_test=? WHERE id=?',(now.isoformat(),row['id']))
            key='TEST-'+secrets.token_hex(12)
            self._add(db,row,key,dict(kind='TEST',title='청년 지원사업 테스트 알림',body='알림 연결 확인용입니다. 실제 신규 모집 공고가 아닙니다.',url='/#asset-alerts',program_id=None),now)
        return key
    def _add(self,db,row,key,payload,now):
        prefs=json.loads(row['prefs']);state='PENDING' if prefs['browser'] and row['push'] else 'FOREGROUND' if prefs['browser'] else 'NOT_REQUESTED'
        if not prefs['inbox'] and not prefs['browser']:return
        db.execute('INSERT OR IGNORE INTO inbox(id,subscriber,event_key,payload,created_at,push_state) VALUES(?,?,?,?,?,?)',(secrets.token_hex(16),row['id'],key,json.dumps(payload,ensure_ascii=False),now.isoformat(),state))
    def publish(self,notice,kind,now):
        event_key=notice['notice_id']+'|'+kind+('|'+notice['content_sha256'] if kind=='NOTICE_RECHECK_REQUIRED' else '')
        body='새 모집 공고가 확인됐어요. 신청 일정과 자격조건은 공식 공고에서 확인해 주세요.' if kind=='NEW_RECRUITMENT' else '공식 공고에 안내된 신청 시작일이 됐어요. 당일 접수시각과 마감 조건은 공식 공고를 확인해 주세요.'
        if kind=='NOTICE_RECHECK_REQUIRED':body='이전에 확인한 모집 공고 내용이 바뀌어 일정 재확인이 필요합니다. 공식 원문을 다시 확인해 주세요.'
        payload=dict(kind=kind,title=notice['title'],body=body,url=notice['url'],program_id=notice['program_id'])
        with self.db() as db:
            for row in db.execute('SELECT * FROM subscribers WHERE expires_at>?',(now.isoformat(),)).fetchall():
                if matches(json.loads(row['prefs']),notice):self._add(db,row,event_key,payload,now)
    def purge(self,now):
        cutoff=(now-timedelta(days=90)).isoformat()
        with self.db() as db:
            db.execute('DELETE FROM inbox WHERE created_at<? OR subscriber IN (SELECT id FROM subscribers WHERE expires_at<=?)',(cutoff,now.isoformat()))
            db.execute('DELETE FROM subscribers WHERE expires_at<=?',(now.isoformat(),))
            db.execute("PRAGMA secure_delete=ON")

def matches(prefs,notice):
    return notice['program_id'] in prefs['programs'] or prefs['all_regions'] or (notice['scope']=='NATIONAL' and prefs['national']) or bool(set(notice['regions'])&set(prefs['regions']))

class Monitor:
    def __init__(self,state=DEFAULT_STATE,config=None,fetcher=fetch,sender=None):
        self.state=Path(state);self.store=Store(self.state/'state.sqlite3')
        self.config=config or json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        self.fetcher=fetcher;self.sender=sender or PushSender(self.state/'vapid-private.pem')
        self.hosts=set(self.config['hosts']);self.round_lock=threading.Lock()
    def cycle(self,now=None,force=False):
        now=now or datetime.now(KST)
        if not self.round_lock.acquire(blocking=False):return {'status':'ALREADY_RUNNING'}
        lease_owned=False
        try:
            with self.store.db() as db:
                db.execute('BEGIN IMMEDIATE')
                meta=db.execute("SELECT value FROM meta WHERE key='lease'").fetchone()
                if meta and datetime.fromisoformat(json.loads(meta[0]))>now:return {'status':'ALREADY_RUNNING'}
                last=self.store.meta('last_run')
                if not force and last and now<datetime.fromisoformat(last['next_check_at']):return {'status':'NOT_DUE'}
                db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',('lease',json.dumps((now+timedelta(minutes=10)).isoformat())))
                lease_owned=True
            bootstrap=not self.store.meta('initialized')
            queue=[dict(s) for s in self.config['sources']]
            seen={s['url'] for s in queue};detail_budget=16
            results=[];notices=0
            deadline=time.monotonic()+120
            for spec in queue:
                if time.monotonic()>=deadline:break
                url=spec['url'];sid=spec['id']
                try:
                    body,media=self.fetcher(url,self.hosts)
                    if 'pdf' in media:
                        fingerprint,text,soup=sha(body),'',None
                    else:fingerprint,text,soup=content(body,spec.get('selector'))
                    reference=spec.get('reference_sha256')
                    status='UNCHANGED_VERIFIED' if reference==fingerprint else 'CHANGED_REVIEW_REQUIRED' if reference else 'LIST_CHECKED' if spec.get('listing') else 'NOTICE_CHECKED'
                    record=dict(id=sid,url=url,checked_at=now.isoformat(),last_success_at=now.isoformat(),status=status,content_sha256=fingerprint,reference_verified=bool(reference and reference==fingerprint))
                    if spec.get('listing'):
                        selected=0
                        for target,title in links(body,url,self.config['programs'],self.hosts):
                            import re
                            years=re.findall(r'20\d{2}',title)
                            if years and max(map(int,years))<now.year:continue
                            if selected>=2:break
                            if target not in seen and detail_budget:
                                from urllib.parse import urlsplit
                                selector={'news.seoul.go.kr':'#post_content','www.korea.kr':'.view_cont','m.korea.kr':'.view_cont'}.get(urlsplit(target).hostname)
                                queue.append(dict(id='detail-'+sha(target)[:20],url=target,title=title,selector=selector));seen.add(target);detail_budget-=1;selected+=1
                    title=spec.get('title')
                    if not title and soup and soup.title:title=soup.title.get_text(' ',strip=True).split(' - ')[0]
                    notice=parse_notice(body,url,title or '',self.config['programs'],now,spec.get('selector')) if soup is not None and not spec.get('listing') else None
                    rechecks=[]
                    with self.store.db() as db:
                        older=[json.loads(r[0]) for r in db.execute('SELECT payload FROM notices').fetchall()]
                        for previous in older:
                            if previous['url']==url and (notice is None or previous['notice_id']!=notice['notice_id']):
                                if previous.get('invalidated') and previous['content_sha256']==fingerprint:continue
                                prior=previous.get('invalidated_from_status',notice_status(previous,now))
                                was_current=prior in ('OPEN','UPCOMING')
                                previous['invalidated_from_status']=prior
                                previous['invalidated']=True;previous['content_sha256']=fingerprint
                                db.execute('UPDATE notices SET payload=?,last_status=? WHERE id=?',(json.dumps(previous,ensure_ascii=False),'REVIEW_REQUIRED',previous['notice_id']))
                                if not bootstrap and was_current:rechecks.append(previous)
                    for previous in rechecks:self.store.publish(previous,'NOTICE_RECHECK_REQUIRED',now)
                    if notice:
                        notices+=1;status_now=notice_status(notice,now)
                        with self.store.db() as db:
                            old=db.execute('SELECT payload,last_status FROM notices WHERE id=?',(notice['notice_id'],)).fetchone()
                            db.execute('INSERT OR REPLACE INTO notices VALUES(?,?,?)',(notice['notice_id'],json.dumps(notice,ensure_ascii=False),status_now))
                        recent=datetime.fromisoformat(notice['starts_at'])>=now-timedelta(days=7)
                        if not bootstrap and old is None and status_now in ('OPEN','UPCOMING') and recent:self.store.publish(notice,'NEW_RECRUITMENT',now)
                        elif not bootstrap and old and old['last_status']=='UPCOMING' and status_now=='OPEN':self.store.publish(notice,'RECRUITMENT_STARTED',now)
                    # Never renew a notice merely because its parent listing returned 200.
                    with self.store.db() as db:db.execute('INSERT OR REPLACE INTO sources VALUES(?,?)',(sid,json.dumps(record)))
                    results.append(record)
                except Exception as error:
                    # A fetch/layout failure cannot become verified data or a recruitment alert.
                    with self.store.db() as db:
                        old=db.execute('SELECT payload FROM sources WHERE id=?',(sid,)).fetchone()
                        record=json.loads(old[0]) if old else dict(id=sid,url=url)
                        record.update(checked_at=now.isoformat(),status='FETCH_OR_PARSE_FAILED',error_type=type(error).__name__,reference_verified=False)
                        db.execute('INSERT OR REPLACE INTO sources VALUES(?,?)',(sid,json.dumps(record)))
                    results.append(record)
            successful=sum(r['status']!='FETCH_OR_PARSE_FAILED' for r in results)
            if successful:self.store.set_meta('initialized',True)
            result=dict(status='OK' if successful==len(queue) else 'PARTIAL' if successful else 'FAILED',checked_at=now.isoformat(),next_check_at=(now+timedelta(seconds=INTERVAL)).isoformat(),source_count=len(queue),successful=successful,parsed_notices=notices,bootstrap=bootstrap,not_checked=len(queue)-len(results))
            self.store.set_meta('last_run',result);self.store.purge(now)
            self.deliver(now)
            return result
        finally:
            if lease_owned:self.store.set_meta('lease',now.isoformat())
            self.round_lock.release()
    def deliver(self,now=None,only_id=None):
        now=now or datetime.now(KST);results=[]
        # Serialize deletion/unsubscribe with sends. No sends after delete returns.
        with self.store.db() as db:
            rows=db.execute("SELECT i.id,i.payload,i.attempts,s.push,s.prefs FROM inbox i JOIN subscribers s ON s.id=i.subscriber WHERE i.push_state IN ('PENDING','FAILED') AND i.attempts<3 AND s.expires_at>? AND (? IS NULL OR i.id=?) ORDER BY i.created_at LIMIT 20",(now.isoformat(),only_id,only_id)).fetchall()
            deadline=time.monotonic()+20
            for row in rows:
                if time.monotonic()>=deadline:break
                if not row['push'] or not json.loads(row['prefs'])['browser']:continue
                payload=json.loads(row['payload']);payload['id']=row['id']
                state=self.sender.send(json.loads(row['push']),payload)
                db.execute('UPDATE inbox SET push_state=?,attempts=attempts+1 WHERE id=?',(state,row['id']))
                if state=='EXPIRED':
                    db.execute('UPDATE subscribers SET push=NULL WHERE id=(SELECT subscriber FROM inbox WHERE id=?)',(row['id'],))
                results.append(dict(id=row['id'],status=state))
        return results
    def public(self,now=None):
        now=now or datetime.now(KST)
        with self.store.db() as db:
            notices=[json.loads(r[0]) for r in db.execute('SELECT payload FROM notices').fetchall()]
            sources=[json.loads(r[0]) for r in db.execute('SELECT payload FROM sources').fetchall()]
        for row in notices:row['status']=notice_status(row,now)
        notices.sort(key=lambda n:(n['status']!='OPEN',n['starts_at']),reverse=False)
        return dict(schema_version='asset-alerts-v1',hosting='cloud' if os.environ.get('AIX_ENV')=='production' else 'local',interval_seconds=INTERVAL,retention_days=90,monitor=self.store.meta('last_run'),
            sources=[{k:r.get(k) for k in ['id','url','checked_at','last_success_at','status']} for r in sources if not r['id'].startswith('detail-')],
            notices=notices[:100],push_public_key=self.sender.public_key,email_available=False,
            worker_active=self.worker_active(),note='서버가 실행 중일 때 6시간마다 공식 출처를 확인합니다. 모든 지역의 모든 공고를 보장하지 않으며, 날짜가 불명확한 자료는 자동 모집 알림에서 제외합니다.')
    def worker_active(self):
        heartbeat=self.store.meta('worker_heartbeat')
        return bool(heartbeat and datetime.now(KST)-datetime.fromisoformat(heartbeat)<timedelta(minutes=3))
    def verified_sources(self):
        with self.store.db() as db:return {r['id']:json.loads(r['payload']) for r in db.execute('SELECT id,payload FROM sources')}

_monitor=None
def get_monitor():
    global _monitor
    if _monitor is None:_monitor=Monitor(Path(os.environ.get('ASSET_ALERTS_STATE_DIR',str(DEFAULT_STATE))))
    return _monitor

async def run_worker(stop):
    import asyncio
    monitor=get_monitor()
    while not stop.is_set():
        monitor.store.set_meta('worker_heartbeat',stamp())
        try:await asyncio.to_thread(monitor.cycle)
        except Exception:monitor.store.set_meta('worker_error',dict(at=stamp(),status='CHECK_FAILED'))
        try:await asyncio.wait_for(stop.wait(),timeout=60)
        except TimeoutError:pass
