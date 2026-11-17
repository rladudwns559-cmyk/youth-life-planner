import {useEffect,useState} from 'react';
import {regionText,type OntongPolicy} from './ontong-policies';
import type {PlannerProgram} from './SupportPlanner';

/**
 * 온통청년 policies the person starred, kept in this browser only. Each entry is a small copy
 * (title, deadline, links) so the schedule, calendar file and consultation memo work without
 * loading the full policy list, and a saved policy stays visible after it leaves the daily list.
 */
export type SavedPolicy={id:string;title:string;org:string;place:string;summary:string;start:string|null;end:string|null;always:boolean;url:string;apply_url:string|null};
export const ONTONG_SAVE_KEY='aix_ontong_saved_v1';
const CHANGED='aix-ontong-saved-changed';
const MAX=60;

export function snapshot(p:OntongPolicy):SavedPolicy{
  return {id:p.id,title:p.title,org:p.org,place:regionText(p),summary:p.summary,
    start:p.apply.mode==='PERIOD'?p.apply.start:null,end:p.apply.mode==='PERIOD'?p.apply.end:null,always:p.apply.mode==='ALWAYS',url:p.url,apply_url:p.apply_url};
}

const text=(v:unknown,max=300)=>typeof v==='string'&&v.length<=max?v:null;
const day=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)?v:null;
const link=(v:unknown)=>typeof v==='string'&&/^https:\/\/[^\s]+$/.test(v)&&v.length<=600?v:null;

export function readSaved():SavedPolicy[]{
  try{
    const raw=localStorage.getItem(ONTONG_SAVE_KEY);if(!raw||raw.length>200_000)return [];
    const list=JSON.parse(raw);if(!Array.isArray(list))return [];
    const seen=new Set<string>();const out:SavedPolicy[]=[];
    for(const v of list.slice(0,MAX)){
      if(!v||typeof v!=='object')continue;
      const id=text(v.id,40),title=text(v.title,200),url=link(v.url);
      if(!id||!title||!url||seen.has(id))continue;seen.add(id);
      out.push({id,title,org:text(v.org,80)??'',place:text(v.place,80)??'',summary:text(v.summary)??'',start:day(v.start),end:day(v.end),always:v.always===true,url,apply_url:typeof v.apply_url==='string'&&/^https?:\/\/[^\s]+$/.test(v.apply_url)&&v.apply_url.length<=600?v.apply_url:null});
    }
    return out;
  }catch{return [];}
}

/** Shared by every part of the page that shows saved policies, so a star anywhere updates all. */
export function useOntongSaved(){
  const [saved,setSaved]=useState(readSaved);
  const [error,setError]=useState('');
  useEffect(()=>{
    const sync=()=>setSaved(readSaved());
    const onStorage=(e:StorageEvent)=>{if(e.key===ONTONG_SAVE_KEY)sync();};
    window.addEventListener(CHANGED,sync);window.addEventListener('storage',onStorage);
    return()=>{window.removeEventListener(CHANGED,sync);window.removeEventListener('storage',onStorage);};
  },[]);
  function write(next:SavedPolicy[]){
    setSaved(next);
    try{if(next.length)localStorage.setItem(ONTONG_SAVE_KEY,JSON.stringify(next));else localStorage.removeItem(ONTONG_SAVE_KEY);setError('');window.dispatchEvent(new Event(CHANGED));}
    catch{setError('이 브라우저에서는 저장할 수 없어 현재 화면에서만 유지합니다.');}
  }
  return {saved,error,
    has:(id:string)=>saved.some(s=>s.id===id),
    toggle:(p:OntongPolicy)=>{const cur=readSaved();write(cur.some(s=>s.id===p.id)?cur.filter(s=>s.id!==p.id):[snapshot(p),...cur].slice(0,MAX));},
    remove:(id:string)=>write(readSaved().filter(s=>s.id!==id)),
    /** Adds several at once (from a shared link), keeping the ones already saved. */
    addMany:(items:SavedPolicy[])=>{const cur=readSaved();const have=new Set(cur.map(s=>s.id));write([...cur,...items.filter(s=>!have.has(s.id))].slice(0,MAX));},
    clear:()=>write([])};
}

/** A saved policy in the shape the deadline calendar file already understands. */
export function asPlannerProgram(s:SavedPolicy):PlannerProgram{
  return {program_id:'ontong-'+s.id,title:s.title,authority:s.org,benefit_summary:s.summary,required_checks:[],ends_on:s.end,intake_mode:s.end?'WINDOW':'CONTINUOUS',
    schedule_note:`온통청년 등록 정책 · ${s.place}${s.end?` · 신청 기간 ~${s.end}`:''}`,sources:[{url:s.url,verified_on:''}]};
}
