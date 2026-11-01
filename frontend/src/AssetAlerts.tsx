import {useEffect,useRef,useState} from 'react';
import {alertsApi,connectBrowser,disconnectBrowser,initialPreferences,notificationUrl,pushSupported,storageKey,type AlertPreferences,type AlertStatus,type AlertItem} from './asset-alerts-api';
import './asset-alerts.css';

const regions=['서울','부산','대구','인천','광주','대전','울산','세종','경기','강원','충북','충남','전북','전남','경북','경남','제주'];
const dateOnly=(value:string)=>new Date(value).toLocaleDateString('ko-KR',{timeZone:'Asia/Seoul'});
const dateTime=(value:string)=>new Date(value).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'});
const statusNames:Record<string,string>={OPEN:'모집 중',UPCOMING:'모집 예정',CLOSED:'신청 마감',REVIEW_REQUIRED:'재확인 필요'};
const deliveryNames:Record<string,string>={PUSH_ACCEPTED:'푸시 서버 접수',FAILED:'푸시 전송 실패',EXPIRED:'브라우저 구독 만료',PENDING:'푸시 전송 대기',NOT_REQUESTED:'알림함',DISABLED:'브라우저 알림 해제'};
function savedToken(){try{return localStorage.getItem(storageKey);}catch{return null;}}

export default function AssetAlerts(){
  const [status,setStatus]=useState<AlertStatus|null>(null),[token,setToken]=useState<string|null>(savedToken);
  const [draft,setDraft]=useState<AlertPreferences>({...initialPreferences}),[items,setItems]=useState<AlertItem[]>([]),[registered,setRegistered]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[showSettings,setShowSettings]=useState(false),[showAll,setShowAll]=useState(false);
  const [saved,setSaved]=useState<AlertPreferences>({...initialPreferences});
  const previousCheck=useRef<string|null>(null),mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  useEffect(()=>{
    let active=true,working=false;
    async function poll(){
      if(working)return;working=true;
      try{
        const result=await alertsApi<AlertStatus>('/status');
        if(!active)return;
        if(result.schema_version!=='asset-alerts-v1'||!Array.isArray(result.notices)||!Array.isArray(result.programs))throw new Error('알림 정보를 확인하지 못했습니다.');
        setStatus(result);
        const check=result.monitor?.checked_at??null;
        if(previousCheck.current&&check!==previousCheck.current)window.dispatchEvent(new Event('asset-official-updated'));
        previousCheck.current=check;
        if(token){
          const inbox=await alertsApi<{items:AlertItem[]}>('/inbox',token);
          if(active)setItems(inbox.items);
        }
      }catch(cause){if(active)setError(cause instanceof Error?cause.message:'알림 서버에 연결하지 못했습니다.');}
      finally{working=false;}
    }
    void poll();const timer=window.setInterval(()=>{if(document.visibilityState!=='hidden')void poll();},30000);
    const focus=()=>void poll();window.addEventListener('focus',focus);
    return()=>{active=false;window.clearInterval(timer);window.removeEventListener('focus',focus);};
  },[token]);
  useEffect(()=>{if(!token)return;let active=true;
    void alertsApi<{preferences:AlertPreferences}>('/subscription',token).then(r=>{if(active){setDraft(r.preferences);setSaved(r.preferences);setRegistered(true);}}).catch(cause=>{if(active){setError(cause instanceof Error?cause.message:'구독을 확인하지 못했습니다.');if(cause instanceof Error&&cause.message.includes('만료')){try{localStorage.removeItem(storageKey);}catch{}setToken(null);setRegistered(false);setItems([]);}}});
    return()=>{active=false;};
  },[token]);
  const toggle=(kind:'regions'|'programs',value:string)=>setDraft(d=>({...d,[kind]:d[kind].includes(value)?d[kind].filter(v=>v!==value):[...d[kind],value]}));
  async function refreshInbox(value=token){if(value){const r=await alertsApi<{items:AlertItem[]}>('/inbox',value);if(mounted.current)setItems(r.items);}}
  async function save(event:React.FormEvent){
    event.preventDefault();if(!status)return;setBusy(true);setError('');setMessage('');
    try{
      const push=draft.browser?await connectBrowser(status.push_public_key):null;
      const r=await alertsApi<{token:string;preferences:AlertPreferences}>('/subscriptions',token,'POST',{preferences:draft,push});
      try{localStorage.setItem(storageKey,r.token);}catch{if(!token)await alertsApi('/subscription',r.token,'DELETE');throw new Error('이 브라우저에서 설정 저장이 차단됐습니다. 저장 허용 후 다시 등록해 주세요.');}
      if(!draft.browser)await disconnectBrowser().catch(()=>{});
      if(mounted.current){setToken(r.token);setSaved(r.preferences);setRegistered(true);setMessage('관심 알림 설정을 저장했어요. 기존 모집을 새 공고로 다시 보내지 않아요.');}
    }catch(cause){if(mounted.current)setError(cause instanceof Error?cause.message:'설정을 저장하지 못했습니다.');}
    finally{if(mounted.current)setBusy(false);}
  }
  async function remove(){if(!token)return;setBusy(true);setError('');
    try{await alertsApi('/subscription',token,'DELETE');try{localStorage.removeItem(storageKey);}catch{}await disconnectBrowser().catch(()=>{});if(mounted.current){setToken(null);setRegistered(false);setItems([]);setDraft({...initialPreferences});setMessage('구독과 서버의 관심 설정·알림 기록을 삭제했어요.');}}
    catch(cause){if(mounted.current)setError(cause instanceof Error?cause.message:'삭제하지 못했습니다.');}
    finally{if(mounted.current)setBusy(false);}
  }
  async function test(){if(!token)return;setBusy(true);setError('');setMessage('');
    try{const r=await alertsApi<{push_state:string}>('/test',token,'POST');await refreshInbox();if(mounted.current)setMessage(r.push_state==='PUSH_ACCEPTED'?'테스트 알림을 푸시 서버에 보냈어요. 기기에 표시되는지 확인해 주세요.':'테스트 알림을 알림함에 기록했어요.'+(r.push_state==='FAILED'?' 브라우저 푸시는 전송에 실패했어요.':''));}
    catch(cause){if(mounted.current)setError(cause instanceof Error?cause.message:'테스트 알림을 보내지 못했습니다.');}
    finally{if(mounted.current)setBusy(false);}
  }
  async function read(id:string){if(!token)return;try{await alertsApi(`/inbox/${id}/read`,token,'POST');await refreshInbox();}catch{setError('읽음 상태를 저장하지 못했습니다.');}}
  const notices=(status?.notices??[]).filter(n=>n.status!=='CLOSED').filter(n=>!registered||saved.all_regions||saved.programs.includes(n.program_id)||(n.scope==='NATIONAL'&&saved.national)||n.regions.some(r=>saved.regions.includes(r)));
  const unread=items.filter(i=>!i.is_read).length;
  return <section className="asset-alerts" id="asset-alerts" aria-labelledby="asset-alerts-heading">
    <div className="alerts-header"><div><p className="eyebrow">관심 지역 · 관심 사업 알림</p><h2 id="asset-alerts-heading">새 모집 소식, 내 관심에 맞춰.</h2><p>공식 공고를 주기적으로 확인하고 관심 있는 소식을 모아드려요.</p></div><button type="button" className="alerts-settings-button" onClick={()=>setShowSettings(v=>!v)} aria-expanded={showSettings}>{registered?'알림 설정 변경':'관심 알림 설정'} <span aria-hidden="true">↗</span></button></div>
    <div className="alerts-monitor"><span className={`alerts-dot ${status?.worker_active?'active':''}`} aria-hidden="true"/><span>{status?.worker_active?'자동 확인 실행 중 · 6시간 간격':'자동 확인 서버 상태 확인 필요'}</span>{status?.monitor&&<><span>최근 {dateTime(status.monitor.checked_at)}</span><span>다음 {dateTime(status.monitor.next_check_at)}</span><span>{status.monitor.successful}/{status.monitor.source_count} 출처 확인{status.monitor.status!=='OK'?' · 일부 재확인 필요':''}</span></>}</div>
    {error&&<p role="alert" className="alerts-error">{error}</p>}{message&&<p role="status" className="alerts-message">{message}</p>}
    {showSettings&&<form className="alerts-settings" onSubmit={save}>
      <fieldset disabled={busy}><legend>1. 받고 싶은 지역</legend><div className="alerts-options"><label><input type="checkbox" checked={draft.national} onChange={e=>setDraft({...draft,national:e.target.checked})}/>전국 대상 사업</label><label><input type="checkbox" checked={draft.all_regions} onChange={e=>setDraft({...draft,all_regions:e.target.checked})}/>모든 지역 소식</label></div><div className="alerts-region-grid">{regions.map(r=><label key={r}><input type="checkbox" checked={draft.regions.includes(r)} onChange={()=>toggle('regions',r)}/>{r}</label>)}</div></fieldset>
      <fieldset disabled={busy}><legend>2. 따로 관심 있는 사업 · 선택</legend><p className="hint">선택한 지역 소식 또는 관심 사업의 새 모집을 알려드려요. 관심 선택은 가입 자격 판정이 아닙니다.</p><div className="alerts-program-grid">{status?.programs.map(p=><label key={p.program_id}><input type="checkbox" checked={draft.programs.includes(p.program_id)} onChange={()=>toggle('programs',p.program_id)}/>{p.title}</label>)}</div></fieldset>
      <fieldset disabled={busy}><legend>3. 받을 방법</legend><div className="alerts-channel-grid"><label><input type="checkbox" checked={draft.inbox} onChange={e=>setDraft({...draft,inbox:e.target.checked})}/><span><strong>사이트 알림함</strong><small>이 브라우저에서 다시 열어 확인해요.</small></span></label><label><input type="checkbox" checked={draft.browser} onChange={e=>setDraft({...draft,browser:e.target.checked})} disabled={!pushSupported()}/><span><strong>브라우저 푸시</strong><small>{pushSupported()?'저장할 때 알림 권한을 요청해요.':'현재 브라우저 미지원 · Chrome/Edge에서 열어 주세요.'}</small></span></label></div></fieldset>
      <p className="alerts-privacy">저장을 누르면 관심 지역·사업·알림 수신 설정과 필요한 브라우저 구독만 보관합니다. 구독은 90일 후 만료되며 만료 기록은 서버 실행 중 정기적으로 삭제됩니다. 소득·월세·생년월일은 저장하지 않습니다. 이 브라우저에 비공개 구독 식별자가 저장되며 구독 삭제로 서버 기록도 지울 수 있어요.</p>
      <div className="alerts-actions"><button type="submit" disabled={busy||!status}>{busy?'처리 중…':'관심 설정 저장'}</button>{registered&&<button type="button" className="alerts-secondary" onClick={remove} disabled={busy}>구독·기록 삭제</button>}</div>
    </form>}
    <div className="alerts-content"><div className="alerts-inbox"><div className="alerts-inbox-title"><h3>{saved.inbox?'내 알림함':'브라우저 알림 전송 기록'} <span>{unread}</span></h3>{registered&&<button type="button" onClick={test} disabled={busy}>테스트 알림 보내기</button>}</div>
      {!registered?<p className="alerts-empty">관심 지역이나 사업을 선택하면 새 공고를 여기서 확인할 수 있어요.</p>:items.length===0?<p className="alerts-empty">아직 새 알림이 없어요. 최초 등록 때 과거 공고를 새 모집으로 보내지 않습니다.</p>:<><button type="button" className="alerts-read" onClick={()=>void read('all')}>모두 읽음</button><ol className="alerts-items">{(showAll?items:items.slice(0,5)).map(item=><li key={item.id} className={item.is_read?'':'unread'}><small>{item.kind==='TEST'?'연결 확인용 테스트':'공식 모집 소식'} · {dateTime(item.created_at)}</small><a href={notificationUrl(item.url)} target={item.url.startsWith('/')?undefined:'_blank'} rel="noopener noreferrer" onClick={()=>void read(item.id)}>{item.title}</a><p>{item.body}</p><span>{deliveryNames[item.push_state]??'전송 상태 확인 필요'}</span></li>)}</ol>{items.length>5&&<button type="button" className="alerts-read" onClick={()=>setShowAll(v=>!v)}>{showAll?'접기':`알림 ${items.length}개 보기`}</button>}</>}
    </div><div className="alerts-live"><h3>자동 확인한 모집 공고</h3>{notices.length===0?<p className="alerts-empty">현재 자동 확인된 새 모집 공고가 없어요. 기존 공식 사업 정보는 아래 목록에서 확인할 수 있습니다.</p>:<ul>{notices.slice(0,6).map(n=><li key={n.notice_id}><span className="alerts-notice-status">{statusNames[n.status]??'확인 필요'}</span><a href={notificationUrl(n.url)} target="_blank" rel="noopener noreferrer">{n.title} ↗</a><p>신청 {n.start_date_only?dateOnly(n.starts_at):dateTime(n.starts_at)} ~ {n.date_only?dateOnly(new Date(new Date(n.ends_at_exclusive).getTime()-1).toISOString()):dateTime(n.ends_at_exclusive)} · 확인 {dateTime(n.verified_at)}</p><small>{n.note}</small></li>)}</ul>}</div></div>
    <details className="alerts-coverage"><summary>자동 확인 범위와 알림 이용 조건</summary><p>{status?.note??'등록한 공식 출처의 모집 공고를 확인합니다.'}</p><p>브라우저 알림은 권한 허용과 네트워크 연결이 필요하고, 기기 절전·브라우저 종료 설정에 따라 늦어질 수 있어요. {status?.hosting==='cloud'?'클라우드 서버에서 주기적으로 실행합니다. 서버 장애 때에는 확인·알림이 지연될 수 있습니다.':'현재는 이 PC의 서버가 실행 중일 때 동작합니다.'} 연중 상시 운영이나 전국 모든 공고 수집을 보장하지 않습니다. 이메일은 이번 범위에서 제외했습니다.</p><p>명확한 신청기간이 없는 공고·이미지/PDF만 있는 신규 일정·서로 충돌하는 일정은 자동 모집 알림에서 제외합니다. 자격 판정·지원금·만기금액은 자동 변경하지 않습니다.</p>{status?.sources.length? <ul>{status.sources.map(s=><li key={s.id}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.id}</a> · {s.status==='UNCHANGED_VERIFIED'?'기존 내용 동일 확인':s.status==='LIST_CHECKED'?'공고 목록 확인':s.status==='FETCH_OR_PARSE_FAILED'?'연결·형식 재확인 필요':s.status==='CHANGED_REVIEW_REQUIRED'?'본문 변경·조건 검토 필요':'공고 확인'}</li>)}</ul>:null}</details>
  </section>;
}
