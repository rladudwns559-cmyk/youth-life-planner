import {useState} from 'react';
import {loadPolicyList} from './ontong-list';
import {snapshot,type SavedPolicy} from './ontong-saved';
import {routeLinks} from './portal-routing';
import './saved-link.css';

/**
 * Moving the saved list to another device without an account: the link carries only program and
 * policy numbers in the address. Nothing is sent anywhere; opening the link asks before merging.
 */
export type SavedIds={programs:string[];policies:string[]};
const MAX=100;
const ID=/^[A-Za-z0-9._-]{1,60}$/;

function toBase64Url(text:string){const bytes=new TextEncoder().encode(text);let bin='';for(const b of bytes)bin+=String.fromCharCode(b);return btoa(bin).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');}
function fromBase64Url(text:string){const bin=atob(text.replace(/-/g,'+').replace(/_/g,'/'));return new TextDecoder().decode(Uint8Array.from(bin,c=>c.charCodeAt(0)));}

export function encodeSaved(ids:SavedIds):string{return toBase64Url(JSON.stringify({p:ids.programs.slice(0,MAX),o:ids.policies.slice(0,MAX)}));}
export function decodeSaved(value:string|null):SavedIds|null{
  if(!value||value.length>8000)return null;
  try{
    const v=JSON.parse(fromBase64Url(value));
    const list=(a:unknown)=>Array.isArray(a)?[...new Set(a.filter((s):s is string=>typeof s==='string'&&ID.test(s)))].slice(0,MAX):[];
    const ids={programs:list(v?.p),policies:list(v?.o)};
    return ids.programs.length||ids.policies.length?ids:null;
  }catch{return null;}
}
export const savedFromHash=(hash:string)=>{const q=hash.split('?')[1];return q?decodeSaved(new URLSearchParams(q).get('saved')):null;};
export function savedLink(ids:SavedIds,base=window.location.href.split('#')[0]){return `${base}${routeLinks.catalog}?saved=${encodeSaved(ids)}`;}

/** Makes the link and copies it; the address is also shown for copying by hand. */
export function SavedLinkTools({ids}:{ids:SavedIds}){
  const [link,setLink]=useState('');
  const [message,setMessage]=useState('');
  const count=ids.programs.length+ids.policies.length;
  async function make(){
    const url=savedLink(ids);setLink(url);
    try{await navigator.clipboard.writeText(url);setMessage('링크를 복사했어요. 다른 기기에서 열면 관심 목록을 합칠지 물어봐요.');}
    catch{setMessage('자동 복사가 안 돼요. 아래 주소를 직접 복사해 주세요.');}
  }
  return <div className="saved-link">
    <button type="button" disabled={!count} onClick={make}>관심 목록 링크 만들기 ({count})</button>
    <small>{count?'다른 기기로 옮길 때 써요. 링크에는 사업·정책 번호만 들어가고, 조건이나 메모는 들어가지 않아요.':'관심 저장한 사업·정책이 있으면 다른 기기로 옮길 링크를 만들 수 있어요.'}</small>
    {link&&<input readOnly value={link} aria-label="관심 목록 링크" onFocus={e=>e.currentTarget.select()}/>}
    {message&&<p role="status">{message}</p>}
  </div>;
}

/** Shown when the page was opened from a saved-list link: merge only when the person says so. */
export function SavedImport({ids,knownPrograms,onMergePrograms,onMergePolicies,onDone,onDismiss,load=loadPolicyList}:{
  ids:SavedIds;knownPrograms:Set<string>;onMergePrograms:(ids:string[])=>void;onMergePolicies:(items:SavedPolicy[])=>void;onDone:()=>void;onDismiss:()=>void;
  load?:typeof loadPolicyList;
}){
  const [state,setState]=useState<'ask'|'working'|'done'>('ask');
  const [message,setMessage]=useState('');
  const programs=ids.programs.filter(id=>knownPrograms.has(id));
  async function merge(){
    setState('working');
    let found:SavedPolicy[]=[];let missing=0;
    if(ids.policies.length){
      try{const list=await load();const byId=new Map(list.policies.map(p=>[p.id,p]));found=ids.policies.flatMap(id=>{const p=byId.get(id);return p?[snapshot(p)]:[];});missing=ids.policies.length-found.length;}
      catch{missing=ids.policies.length;}
    }
    onMergePrograms(programs);onMergePolicies(found);
    setMessage(`사업 ${programs.length}개, 정책 ${found.length}개를 이 기기의 관심 목록에 합쳤어요.${missing?` 지금 목록에 없는 정책 ${missing}개는 빼었어요.`:''}${ids.programs.length>programs.length?` 지금 목록에 없는 사업 ${ids.programs.length-programs.length}개도 빼었어요.`:''}`);
    setState('done');onDone();
  }
  if(state==='done')return <div className="saved-import" role="status">{message}</div>;
  return <section className="saved-import" aria-labelledby="saved-import-title">
    <h3 id="saved-import-title">다른 기기에서 보낸 관심 목록이 있어요</h3>
    <p>사업 {ids.programs.length}개, 온통청년 정책 {ids.policies.length}개가 링크에 들어 있어요. 이 기기의 관심 목록에 합칠까요? 원래 저장한 것은 지우지 않아요.</p>
    <div className="saved-import-actions"><button type="button" className="finder-primary" disabled={state==='working'} onClick={merge}>{state==='working'?'합치는 중…':'이 기기에 합치기'}</button><button type="button" disabled={state==='working'} onClick={()=>{onDone();onDismiss();}}>합치지 않기</button></div>
  </section>;
}
