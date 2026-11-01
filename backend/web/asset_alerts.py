"""Anonymous, explicit-interest subscriptions. Tokens never enter URLs/logs."""
import asyncio,os,sys
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import APIRouter,Header,HTTPException,Request
from pydantic import Field
from backend.opportunities.catalog import Strict,Province
from backend.asset_alerts.runtime import get_monitor,run_worker

router=APIRouter(prefix='/api/asset-alerts',tags=['asset-alerts'])

class Preferences(Strict):
    regions:Annotated[list[Province],Field(max_length=17)]=[]
    programs:Annotated[list[str],Field(max_length=30)]=[]
    national:bool=True
    all_regions:bool=False
    inbox:bool=True
    browser:bool=False

class SubscriptionInput(Strict):
    preferences:Preferences
    push:dict|None=None

def credential(authorization):
    if not authorization or not authorization.startswith('Bearer '):raise HTTPException(401,detail='알림 설정을 다시 등록해 주세요.')
    token=authorization[7:]
    try:get_monitor().store.subscriber(token)
    except PermissionError:raise HTTPException(401,detail='알림 설정이 없거나 만료되었습니다.') from None
    return token

def mutation(request):
    origin=request.headers.get('origin')
    allowed={v.strip() for v in os.environ.get('ASSET_ALERTS_ORIGINS','http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8100,http://localhost:8100').split(',')}
    if request.headers.get('x-aix-client')!='asset-alerts-v1' or (origin and origin not in allowed):raise HTTPException(403,detail='이 사이트에서만 알림 설정을 변경할 수 있습니다.')

@router.get('/status')
def status():
    monitor=get_monitor();data=monitor.public()
    return data|dict(programs=[dict(program_id=p['program_id'],title=p['title'],regions=p['regions']) for p in monitor.config['programs']])

@router.post('/subscriptions')
def subscribe(data:SubscriptionInput,request:Request,authorization:Annotated[str|None,Header()]=None):
    mutation(request);monitor=get_monitor();prefs=data.preferences.model_dump(mode='json')
    known={p['program_id'] for p in monitor.config['programs']}
    if len(set(prefs['regions']))!=len(prefs['regions']) or len(set(prefs['programs']))!=len(prefs['programs']) or not set(prefs['programs'])<=known:raise HTTPException(422,detail='관심 지역과 사업을 다시 선택해 주세요.')
    if not any([prefs['regions'],prefs['programs'],prefs['national'],prefs['all_regions']]):raise HTTPException(422,detail='관심 지역이나 사업을 하나 이상 선택해 주세요.')
    if not prefs['inbox'] and not prefs['browser']:raise HTTPException(422,detail='알림함 또는 브라우저를 선택해 주세요. 모두 끄려면 구독 삭제를 이용하세요.')
    if prefs['browser']!=(data.push is not None):raise HTTPException(422,detail='브라우저 알림 권한과 연결을 먼저 확인해 주세요.')
    token=credential(authorization) if authorization else None
    try:return monitor.store.subscribe(prefs,data.push,token)
    except ValueError as error:
        code=str(error)
        raise HTTPException(409 if code=='PUSH_ALREADY_REGISTERED' else 422,detail='브라우저 구독을 확인하지 못했습니다. 기존 설정을 삭제한 뒤 다시 연결해 주세요.' if code=='PUSH_ALREADY_REGISTERED' else '브라우저 구독 형식과 관심 설정을 확인해 주세요.') from None

@router.get('/subscription')
def settings(authorization:Annotated[str|None,Header()]=None):return get_monitor().store.settings(credential(authorization))

@router.delete('/subscription')
def delete(request:Request,authorization:Annotated[str|None,Header()]=None):
    mutation(request);get_monitor().store.delete(credential(authorization));return {'deleted':True}

@router.get('/inbox')
def inbox(authorization:Annotated[str|None,Header()]=None):
    return {'items':get_monitor().store.inbox(credential(authorization))}

@router.post('/inbox/{identifier}/read')
def mark_read(identifier:str,request:Request,authorization:Annotated[str|None,Header()]=None):
    mutation(request);get_monitor().store.mark_read(credential(authorization),identifier);return {'ok':True}

@router.post('/test')
def test(request:Request,authorization:Annotated[str|None,Header()]=None):
    mutation(request);monitor=get_monitor();token=credential(authorization)
    try:key=monitor.store.test(token)
    except ValueError:raise HTTPException(429,detail='테스트 알림은 1분에 한 번 보낼 수 있습니다.') from None
    item=next(i for i in monitor.store.inbox(token) if i['kind']=='TEST')
    monitor.deliver(only_id=item['id'])
    item=next(i for i in monitor.store.inbox(token) if i['id']==item['id'])
    return dict(created=True,id=item['id'],push_state=item['push_state'],note='실제 모집이 아닌 연결 확인용 테스트입니다. PUSH_ACCEPTED는 푸시 서버 접수이며 화면 표시 확인은 별도입니다.')

@asynccontextmanager
async def lifespan(app):
    # Existing TestClient suites must not silently make public network calls.
    enabled=os.environ.get('ASSET_ALERTS_AUTO_REFRESH','0' if 'pytest' in sys.modules else '1')=='1'
    stop=asyncio.Event();task=asyncio.create_task(run_worker(stop)) if enabled else None
    try:yield
    finally:
        if task:
            stop.set()
            try:await asyncio.wait_for(asyncio.shield(task),timeout=160)
            except TimeoutError:task.cancel()
