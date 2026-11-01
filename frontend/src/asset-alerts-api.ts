export interface AlertPreferences {regions:string[];programs:string[];national:boolean;all_regions:boolean;inbox:boolean;browser:boolean;}
export interface OfficialNotice {notice_id:string;program_id:string;title:string;url:string;regions:string[];scope:string;starts_at:string;ends_at_exclusive:string;date_only:boolean;start_date_only:boolean;verified_at:string;status:string;note:string;eligibility_status:'UNKNOWN';}
export interface AlertStatus {schema_version:'asset-alerts-v1';hosting?:'cloud'|'local';interval_seconds:number;retention_days:number;monitor:null|{status:string;checked_at:string;next_check_at:string;source_count:number;successful:number;bootstrap:boolean};sources:{id:string;url:string;checked_at:string;last_success_at:string|null;status:string}[];notices:OfficialNotice[];push_public_key:string;email_available:false;worker_active:boolean;note:string;programs:{program_id:string;title:string;regions:string[]}[];}
export interface AlertItem {id:string;kind:string;title:string;body:string;url:string;created_at:string;is_read:boolean;push_state:string;}
export const storageKey='aix-asset-alert-token-v1';
export const initialPreferences:AlertPreferences={regions:[],programs:[],national:true,all_regions:false,inbox:true,browser:false};
export async function alertsApi<T>(path:string,token:string|null=null,method='GET',body?:unknown):Promise<T>{
  const controller=new AbortController(),timer=window.setTimeout(()=>controller.abort(),12000);
  try{
    const response=await fetch('/api/asset-alerts'+path,{method,cache:'no-store',signal:controller.signal,headers:{'X-AIX-Client':'asset-alerts-v1',...(token?{Authorization:'Bearer '+token}:{}),...(body!==undefined?{'Content-Type':'application/json'}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
    if(!response.ok){if(response.status===401)throw new Error('알림 설정이 만료되었거나 삭제됐습니다. 다시 등록해 주세요.');throw new Error(response.status===429?'테스트 알림은 1분에 한 번 보낼 수 있어요.':'알림 설정을 처리하지 못했습니다. 선택 항목과 연결 상태를 확인해 주세요.');}
    return await response.json() as T;
  }catch(error){
    if(controller.signal.aborted)throw new Error('알림 서버 응답 시간이 초과됐습니다. 잠시 후 다시 확인해 주세요.');
    if(error instanceof TypeError)throw new Error('알림 서버에 연결하지 못했습니다. 서버 실행 상태를 확인해 주세요.');
    throw error;
  }finally{window.clearTimeout(timer);}
}
export function pushSupported(){return typeof Notification!=='undefined'&&'serviceWorker' in navigator&&'PushManager' in window&&window.isSecureContext;}
function deadline<T>(promise:Promise<T>,ms=10000):Promise<T>{return new Promise((resolve,reject)=>{const timer=window.setTimeout(()=>reject(new Error('브라우저 푸시 연결 시간이 초과됐습니다. 기존 설정은 유지됩니다.')),ms);promise.then(v=>{window.clearTimeout(timer);resolve(v);},e=>{window.clearTimeout(timer);reject(e);});});}
export async function connectBrowser(publicKey:string):Promise<PushSubscriptionJSON>{
  try{
  if(!pushSupported())throw new Error('이 브라우저에서는 푸시를 지원하지 않습니다. Chrome 또는 Edge에서 이 사이트를 열어 주세요.');
  // Called only from the explicit save gesture, never on page load.
  const permission=Notification.permission==='granted'?'granted':await deadline(Notification.requestPermission(),30000);
  if(permission!=='granted')throw new Error('브라우저 알림이 허용되지 않았습니다. 사이트 권한에서 알림을 허용하거나 알림함만 선택해 주세요.');
  const registration=await deadline(navigator.serviceWorker.register('/asset-alerts-sw.js',{scope:'/'}));
  if(!registration.active)await deadline(navigator.serviceWorker.ready);
  const existing=await registration.pushManager.getSubscription();
  const decoded=atob(publicKey.replace(/-/g,'+').replace(/_/g,'/'));const key=new Uint8Array([...decoded].map(c=>c.charCodeAt(0)));
  const subscription=existing??await deadline(registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:key}));
  return subscription.toJSON();
  }catch(error){if(error instanceof Error&&/[가-힣]/.test(error.message))throw error;throw new Error('브라우저 푸시를 연결하지 못했습니다. Chrome/Edge의 알림 권한과 네트워크를 확인하거나 사이트 알림함을 선택해 주세요.');}
}
export async function disconnectBrowser(){
  if('serviceWorker' in navigator){const registration=await navigator.serviceWorker.getRegistration('/');const sub=await registration?.pushManager.getSubscription();if(sub)await sub.unsubscribe();}
}
export function notificationUrl(value:string){try{const u=new URL(value,window.location.origin);return u.origin===window.location.origin||u.protocol==='https:'?u.href:'#asset-alerts';}catch{return '#asset-alerts';}}
