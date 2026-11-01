import {useEffect,useState} from 'react';

export type PlannerProgram={program_id:string;title:string;authority:string;benefit_summary:string;required_checks:string[];ends_on:string|null;intake_mode:string;schedule_note:string;sources:{url:string;verified_on:string}[]};
export const SUPPORT_SAVE_KEY='aix_support_planner_v1';
export function koreaDay(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
export function useKoreaDay(){
 const [day,setDay]=useState(koreaDay);
 useEffect(()=>{const refresh=()=>setDay(koreaDay());const timer=setInterval(refresh,60_000);window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);return()=>{clearInterval(timer);window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh);};},[]);
 return day;
}
export function checkKey(p:PlannerProgram,text:string){let h=2166136261;for(const c of text){h^=c.codePointAt(0)!;h=Math.imul(h,16777619);}return p.program_id+':'+(h>>>0).toString(16);}
type Saved={favorites:string[];checks:string[]};
export function readPlanner(programs:PlannerProgram[]):Saved{
 try{const raw=localStorage.getItem(SUPPORT_SAVE_KEY);if(!raw||raw.length>65536)return {favorites:[],checks:[]};const v=JSON.parse(raw);if(!v||typeof v!=='object')throw Error();const ids=new Set(programs.map(p=>p.program_id)),checks=new Set(programs.flatMap(p=>p.required_checks.map(t=>checkKey(p,t))));const list=(a:unknown,allowed:Set<string>)=>Array.isArray(a)?[...new Set(a.filter((s):s is string=>typeof s==='string'&&allowed.has(s)))]:[];return {favorites:list(v.favorites,ids),checks:list(v.checks,checks)};}catch{return {favorites:[],checks:[]};}
}
export function usePlanner(programs:PlannerProgram[]){
 const [saved,setSaved]=useState(()=>readPlanner(programs)),[error,setError]=useState('');
 function write(next:Saved){setSaved(next);try{if(next.favorites.length||next.checks.length)localStorage.setItem(SUPPORT_SAVE_KEY,JSON.stringify(next));else localStorage.removeItem(SUPPORT_SAVE_KEY);setError('');}catch{setError('이 브라우저에서는 저장할 수 없어 현재 화면에서만 유지합니다.');}}
 const toggle=(key:'favorites'|'checks',id:string)=>write({...saved,[key]:saved[key].includes(id)?saved[key].filter(v=>v!==id):[...saved[key],id]});
 return {...saved,error,toggleFavorite:(id:string)=>toggle('favorites',id),toggleCheck:(id:string)=>toggle('checks',id),clear:()=>write({favorites:[],checks:[]})};
}
const escapeICS=(s:string)=>s.replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,');
// RFC 5545 content lines fold at <=75 octets without splitting a UTF-8 character.
function fold(line:string){const enc=new TextEncoder();let out='',chunk='',size=0;for(const c of line){const n=enc.encode(c).length;if(size+n>75){out+=chunk+'\r\n';chunk=' ';size=1;}chunk+=c;size+=n;}return out+chunk;}
export function calendarText(p:PlannerProgram,asOf:string,stamp=new Date().toISOString()):string|null{
 const end=p.ends_on;if(p.intake_mode!=='WINDOW'||!end||!/^\d{4}-\d{2}-\d{2}$/.test(end)||end<asOf)return null;
 const d=new Date(end+'T00:00:00Z');if(Number.isNaN(d.valueOf())||d.toISOString().slice(0,10)!==end)return null;
 d.setUTCDate(d.getUTCDate()+1);const next=d.toISOString().slice(0,10).replace(/-/g,'');
 const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//AI+X//Support Planner//KO','CALSCALE:GREGORIAN','BEGIN:VEVENT',`UID:${p.program_id}@youth-life-planner.local`,`DTSTAMP:${stamp.replace(/[-:]/g,'').replace(/\.\d{3}Z$/,'Z')}`,`DTSTART;VALUE=DATE:${end.replace(/-/g,'')}`,`DTEND;VALUE=DATE:${next}`,`SUMMARY:${escapeICS(p.title+' · 공고 마감일 확인')}`,`DESCRIPTION:${escapeICS(p.schedule_note+'\n종일 확인 일정입니다. 실제 마감 시각·예산 소진·신청자격은 공식 안내에서 확인하세요. 신청 완료나 자동 알림 구독이 아닙니다.')}`,`URL:${p.sources[0].url}`,'STATUS:TENTATIVE','END:VEVENT','END:VCALENDAR'];
 return lines.map(fold).join('\r\n')+'\r\n';
}
export function ApplicationChecklist({program:p,checked,onCheck,asOf}:{program:PlannerProgram;checked:string[];onCheck:(key:string)=>void;asOf:string}){
 const [message,setMessage]=useState('');const calendar=calendarText(p,asOf);
 function download(){if(!calendar)return;try{const url=URL.createObjectURL(new Blob([calendar],{type:'text/calendar;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=p.program_id+'-deadline.ics';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setMessage('캘린더 파일을 내려받았습니다. 캘린더 앱에서 직접 추가하세요.');}catch{setMessage('캘린더 파일을 만들지 못했습니다. 공식 안내의 마감일을 직접 확인하세요.');}}
 return <details className="application-checklist"><summary>신청 전 확인 목록 · {p.required_checks.filter(t=>checked.includes(checkKey(p,t))).length}/{p.required_checks.length}</summary><p>직접 확인한 항목만 체크하세요. 체크는 개인 메모이며 자격 판정을 바꾸지 않습니다.</p><ul>{p.required_checks.map(t=><li key={t}><label><input type="checkbox" checked={checked.includes(checkKey(p,t))} onChange={()=>onCheck(checkKey(p,t))}/><span>{t}</span></label></li>)}</ul>{calendar&&<button type="button" onClick={download}>공고 마감일 캘린더 저장</button>}<p>사업 ID와 확인 항목 ID만 이 브라우저에 저장합니다. 실제 개인정보·소득·자산은 저장하지 않습니다.</p>{message&&<p role="status">{message}</p>}</details>;
}
export function SupportComparison({items,onClear}:{items:{program:PlannerProgram;status:string;match:string}[];onClear:()=>void}){
 if(!items.length)return null;
 return <section className="support-comparison" id="support-comparison" tabIndex={-1} aria-label="선택한 지원사업 비교"><header><div><p className="eyebrow">나의 선택지 비교</p><h3>비교하고, 확인할 것을 정리하세요.</h3></div><button type="button" onClick={onClear}>사업 비교 선택 지우기</button></header><div className="support-table-scroll" role="region" aria-label="지원사업 비교 표" tabIndex={0}><table><thead><tr><th scope="col">비교 항목</th>{items.map(i=><th scope="col" key={i.program.program_id}>{i.program.title}</th>)}</tr></thead><tbody>{(['모집 상태','조건 비교','지원 내용','신청 일정','추가 확인','자료 확인'] as const).map(label=><tr key={label}><th scope="row">{label}</th>{items.map(({program:p,status,match})=><td key={p.program_id}>{label==='모집 상태'?status:label==='조건 비교'?match:label==='지원 내용'?p.benefit_summary:label==='신청 일정'?p.schedule_note:label==='추가 확인'?p.required_checks.join(' · '):p.sources.map(s=>s.verified_on).sort()[0]}</td>)}</tr>)}<tr><th scope="row">공식 확인</th>{items.map(({program:p})=><td key={p.program_id}><a href={p.sources[0].url} target="_blank" rel="noopener noreferrer">{p.authority} 안내 ↗</a></td>)}</tr></tbody></table></div><p>모든 사업의 지원자격은 추가 확인입니다. 동시 수급·중복지원 가능 여부를 뜻하지 않습니다.</p></section>;
}
