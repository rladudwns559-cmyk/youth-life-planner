import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import AssetAlerts from './AssetAlerts';
import * as api from './asset-alerts-api';
vi.mock('./asset-alerts-api',async original=>({...await original<typeof import('./asset-alerts-api')>(),connectBrowser:vi.fn(),disconnectBrowser:vi.fn(async()=>{}),pushSupported:vi.fn(()=>false)}));
const status={schema_version:'asset-alerts-v1',interval_seconds:21600,retention_days:90,monitor:{status:'OK',checked_at:'2026-10-30T12:00:00+09:00',next_check_at:'2026-10-30T18:00:00+09:00',source_count:19,successful:19,bootstrap:true},sources:[],notices:[],push_public_key:'test-public',email_available:false,worker_active:true,note:'등록한 공식 출처 확인',programs:[{program_id:'P1',title:'희망두배 청년통장',regions:['서울']},{program_id:'P2',title:'청년미래적금',regions:[]}]};
let prefs={...api.initialPreferences},items:api.AlertItem[],requests:{path:string;options?:RequestInit}[];
function response(data:unknown,code=200){return {ok:code>=200&&code<300,status:code,json:async()=>data} as Response;}
beforeEach(()=>{
  localStorage.clear();prefs={...api.initialPreferences};items=[];requests=[];
  vi.mocked(api.pushSupported).mockReturnValue(false);vi.mocked(api.connectBrowser).mockResolvedValue({endpoint:'synthetic',keys:{}});
  vi.stubGlobal('fetch',vi.fn(async(path:string,options?:RequestInit)=>{
    requests.push({path,options});
    if(path.endsWith('/status'))return response(status);
    if(path.endsWith('/subscriptions')){prefs=JSON.parse(options!.body as string).preferences;return response({token:'t'.repeat(43),preferences:prefs});}
    if(path.endsWith('/subscription')&&options?.method==='DELETE')return response({deleted:true});
    if(path.endsWith('/subscription'))return response({preferences:prefs,push_registered:prefs.browser});
    if(path.endsWith('/inbox'))return response({items});
    if(path.endsWith('/test')){items=[{id:'test1',kind:'TEST',title:'청년 지원사업 테스트 알림',body:'실제 신규 모집이 아닙니다.',url:'/#asset-alerts',created_at:'2026-10-30T12:00:00+09:00',is_read:false,push_state:'NOT_REQUESTED'}];return response({created:true,push_state:'NOT_REQUESTED'});}
    if(path.endsWith('/read')){items=items.map(i=>({...i,is_read:true}));return response({ok:true});}
    return response({},404);
  }));
});
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.clearAllMocks();});
async function settings(){render(<AssetAlerts/>);await screen.findByText(/자동 확인 실행 중/);fireEvent.click(screen.getByRole('button',{name:'관심 알림 설정'}));}
async function save(){fireEvent.click(screen.getByRole('button',{name:'관심 설정 저장'}));await screen.findByText(/관심 알림 설정을 저장/);}
describe('official recruitment alerts',()=>{
  it('loads public monitor state without permission requests or registration',async()=>{
    render(<AssetAlerts/>);await screen.findByText(/자동 확인 실행 중/);
    expect(screen.getByText(/아직 새 알림|관심 지역이나 사업을 선택/)).toBeInTheDocument();
    expect(api.connectBrowser).not.toHaveBeenCalled();expect(requests.every(r=>r.options?.method==='GET')).toBe(true);
    expect(screen.queryByLabelText(/이메일/)).not.toBeInTheDocument();
  });
  it('lets each user choose region, program and channel and stores no financial profile',async()=>{
    await settings();fireEvent.click(screen.getByLabelText('서울'));fireEvent.click(screen.getByLabelText('희망두배 청년통장'));await save();
    const body=JSON.parse(requests.find(r=>r.path.endsWith('/subscriptions'))!.options!.body as string);
    expect(body.preferences.regions).toEqual(['서울']);expect(body.preferences.programs).toEqual(['P1']);expect(body.preferences.inbox).toBe(true);expect(body.push).toBeNull();
    expect(localStorage.getItem(api.storageKey)).toHaveLength(43);expect(Object.keys(localStorage)).toEqual([api.storageKey]);
    expect(JSON.stringify(body)).not.toMatch(/income|rent|birth/);
  });
  it('disables browser push when unsupported with a clear alternative',async()=>{
    await settings();expect(screen.getByLabelText(/브라우저 푸시/)).toBeDisabled();expect(screen.getByText(/현재 브라우저 미지원/)).toBeInTheDocument();
    expect(screen.getByLabelText(/사이트 알림함/)).toBeEnabled();
  });
  it('subscribes browser only after an explicit save gesture',async()=>{
    vi.mocked(api.pushSupported).mockReturnValue(true);await settings();fireEvent.click(screen.getByLabelText(/브라우저 푸시/));expect(api.connectBrowser).not.toHaveBeenCalled();
    await save();expect(api.connectBrowser).toHaveBeenCalledWith('test-public');expect(prefs.browser).toBe(true);
  });
  it('does not silently save or downgrade denied browser permission',async()=>{
    vi.mocked(api.pushSupported).mockReturnValue(true);vi.mocked(api.connectBrowser).mockRejectedValueOnce(new Error('브라우저 알림이 허용되지 않았습니다.'));
    await settings();fireEvent.click(screen.getByLabelText(/브라우저 푸시/));fireEvent.click(screen.getByRole('button',{name:'관심 설정 저장'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('허용되지');expect(requests.some(r=>r.path.endsWith('/subscriptions'))).toBe(false);
  });
  it('shows actual test separately from real recruitment',async()=>{
    await settings();await save();fireEvent.click(screen.getByRole('button',{name:'테스트 알림 보내기'}));
    await screen.findByText(/연결 확인용 테스트/);expect(screen.getByText('실제 신규 모집이 아닙니다.')).toBeInTheDocument();
  });
  it('uses token authorization without exposing it in URLs',async()=>{
    await settings();await save();await waitFor(()=>expect(requests.some(r=>r.path.endsWith('/inbox'))).toBe(true));
    const request=requests.find(r=>r.path.endsWith('/inbox'))!;expect(request.path).not.toContain('tttt');expect((request.options!.headers as Record<string,string>).Authorization).toBe('Bearer '+'t'.repeat(43));
  });
  it('deletes the server subscription and browser identifier',async()=>{
    await settings();await save();fireEvent.click(screen.getByRole('button',{name:'구독·기록 삭제'}));
    await screen.findByText(/구독과 서버의 관심 설정/);expect(localStorage.getItem(api.storageKey)).toBeNull();expect(requests.some(r=>r.options?.method==='DELETE')).toBe(true);
  });
  it('restores previously saved preferences',async()=>{
    prefs={...prefs,regions:['경기'],programs:['P2']};localStorage.setItem(api.storageKey,'t'.repeat(43));render(<AssetAlerts/>);
    await screen.findByRole('button',{name:'알림 설정 변경'});fireEvent.click(screen.getByRole('button',{name:'알림 설정 변경'}));
    expect(screen.getByLabelText('경기')).toBeChecked();expect(screen.getByLabelText('청년미래적금')).toBeChecked();
  });
  it('reports server failure without claiming a saved subscription',async()=>{
    await settings();vi.stubGlobal('fetch',vi.fn(async()=>response({},503)));fireEvent.click(screen.getByRole('button',{name:'관심 설정 저장'}));
    await screen.findByRole('alert');expect(localStorage.getItem(api.storageKey)).toBeNull();
  });
  it('marks messages read through the protected route',async()=>{
    await settings();await save();fireEvent.click(screen.getByRole('button',{name:'테스트 알림 보내기'}));await screen.findByText(/연결 확인용 테스트/);
    fireEvent.click(screen.getByRole('button',{name:'모두 읽음'}));await waitFor(()=>expect(items[0].is_read).toBe(true));
  });
  it('renders only official typed notices and preserves UNKNOWN',async()=>{
    const notice={notice_id:'new',program_id:'P1',title:'2026년 희망두배 청년통장 추가 모집',url:'https://news.seoul.go.kr/welfare/archives/1',regions:['서울'],scope:'REGIONAL',starts_at:'2026-10-30T09:00:00+09:00',ends_at_exclusive:'2026-11-10T18:00:00+09:00',date_only:false,start_date_only:false,verified_at:'2026-10-30T12:00:00+09:00',status:'OPEN',note:'자격조건은 추가 확인이 필요합니다.',eligibility_status:'UNKNOWN'};
    vi.stubGlobal('fetch',vi.fn(async()=>response({...status,notices:[notice]})));render(<AssetAlerts/>);
    const link=await screen.findByRole('link',{name:/추가 모집/});expect(link).toHaveAttribute('href',notice.url);expect(screen.getByText('자격조건은 추가 확인이 필요합니다.')).toBeInTheDocument();
  });
  it('blocks executable notification URLs',()=>{
    expect(api.notificationUrl('javascript:alert(1)')).toBe('#asset-alerts');expect(api.notificationUrl('https://www.korea.kr/news')).toBe('https://www.korea.kr/news');
  });
});
