import GroupedInput from './GroupedInput';
import {useMemo,useState} from 'react';
import prepared from './public-data/current-support-web.json';
import './regional-programs.css';
import {routeLinks} from './portal-routing';
import FinderDialog from './FinderDialog';
import ConditionPrompt from './ConditionPrompt';
import YouthCenterHelp from './YouthCenterHelp';
import LocalNotice from './LocalNotice';
import DataFreshness from './DataFreshness';
import {deadlineOrder} from './support-order';
import directory from './public-data/nationwide-districts.json';
import {useKoreaDay,usePlanner,ApplicationChecklist,SupportComparison,DeadlineAction,deadlineOf,deadlineLabel,calendarTextMany,downloadCalendar} from './SupportPlanner';

import {intakeLabels,readRegionalDecision,locationText,programIndex,koreaToday as day,type RegionStatus,type Intake} from './support-status';
export {intakeLabels,readRegionalDecision,locationText};
type Program=typeof prepared.programs[number];
export const categories:Record<string,string>={ALL:'전체 분야',HOUSING:'월세·주거',EMPLOYMENT:'취업·면접',EDUCATION:'교육·응시료',LIVING:'생활·복지',CULTURE:'문화',ASSET:'청년통장·자산형성'};
const labels=intakeLabels;
const tables=prepared as unknown as {cities:Record<string,string[]>};
export type PersonalInput={age:string;employment:string;rent:string};
type PersonalSummary={candidate_status:'REVIEW'|'DIFFERENT';matched_count:number;eligibility:'UNKNOWN';benefit_applied_krw:0};
type MatchRule={age:{note:string};employment_note:string;rent_note:string;sources:Program['sources']};
const personal=prepared.personal as unknown as {
 age_pool:string[];age_calendar:Record<string,number>;age_vectors:number[][];age_valid_until:string;
 employment:Record<string,RegionStatus[]>;rent:Record<string,RegionStatus[]>;
 combinations:Record<string,PersonalSummary>;rules:(MatchRule|null)[];
};
export function validAge(value:string){return value===''||(/^\d{1,3}$/.test(value)&&Number(value)<=120);}
export function readPersonalDecision(id:string,regionKey:string,input:PersonalInput,asOf=day()){
 const i=programIndex.get(id)??-1;
 const region=regionKey==='*'?'UNKNOWN':readRegionalDecision(id,regionKey,asOf).region;
 const index=personal.age_vectors[personal.age_calendar[asOf]]?.[i];
 const code=i>=0&&index!==undefined&&input.age!==''&&validAge(input.age)?personal.age_pool[index]?.[Number(input.age)]:'U';
 const age:RegionStatus=code==='P'?'PASS':code==='F'?'FAIL':'UNKNOWN';
 const employment:RegionStatus=personal.employment[input.employment]?.[i]??'UNKNOWN';
 const rent:RegionStatus=personal.rent[input.rent]?.[i]??'UNKNOWN';
 const summary=personal.combinations[[region,age,employment,rent].join('|')]??{candidate_status:'REVIEW',matched_count:0,eligibility:'UNKNOWN',benefit_applied_krw:0};
 return {region,age,employment,rent,summary,rule:personal.rules[i]??null};
}
const matchWords={PASS:'입력 조건 일치',FAIL:'현재 입력과 다름',UNKNOWN:'추가 확인'};
const employmentNames:Record<string,string>={employed:'근로 중',unemployed:'현재 일하지 않음',self_employed:'자영업·프리랜서'};
const rentNames:Record<string,string>={yes:'월세 거주',no:'월세 외 거주(전세·자가 등)'};
export type ConditionGap={key:'region'|'age'|'employment'|'rent';label:string;text:string};
/** Why a program differs from the input and what would have to change. Built only from the same tables that produced FAIL. */
export function conditionGaps(id:string,regionKey:string,input:PersonalInput,asOf=day()):ConditionGap[]{
 const i=programIndex.get(id)??-1;if(i<0)return [];
 const p=prepared.programs[i];const m=readPersonalDecision(id,regionKey,input,asOf);const gaps:ConditionGap[]=[];
 if(m.region==='FAIL')gaps.push({key:'region',label:'지역',text:`${locationText(p)} 대상 사업이에요. 선택한 지역과 달라요. 근무지·학교 지역도 인정하는지는 공고에서 확인하세요.`});
 if(m.age==='FAIL'){
  const codes=personal.age_pool[personal.age_vectors[personal.age_calendar[asOf]]?.[i]]??'';
  const pass=[...codes].flatMap((c,n)=>c==='P'?[n]:[]);const a=Number(input.age);
  if(!pass.length)gaps.push({key:'age',label:'나이',text:`입력한 만 ${a}세는 이 사업의 연령 기준과 달라요. 기준: ${p.age_note}`});
  else{const lo=pass[0],hi=pass[pass.length-1];
   gaps.push({key:'age',label:'나이',text:a<lo?`비교 기준은 만 ${lo}~${hi}세예요. 입력한 만 ${a}세보다 ${lo-a}살 많아야 해요. 다음 모집 때 다시 확인해 보세요.`:a>hi?`비교 기준은 만 ${lo}~${hi}세예요. 입력한 만 ${a}세가 상한보다 ${a-hi}살 많아요. 병역 기간 등 연령 예외가 있는지는 공고에서 확인하세요.`:`비교 기준(만 ${lo}~${hi}세) 안에서도 이 나이는 제외돼요. 기준: ${p.age_note}`});}
 }
 if(m.employment==='FAIL'){
  const by=(v:RegionStatus)=>Object.keys(employmentNames).filter(k=>personal.employment[k]?.[i]===v).map(k=>employmentNames[k]);
  const ok=by('PASS'),maybe=by('UNKNOWN');
  gaps.push({key:'employment',label:'취업 상태',text:`입력한 '${employmentNames[input.employment]??input.employment}' 상태는 대상이 아니에요.${ok.length?` 대상: ${ok.join(', ')}.`:''}${maybe.length?` ${maybe.join(', ')}는 공고에서 추가 확인이 필요해요.`:''}`});
 }
 if(m.rent==='FAIL'){
  const ok=Object.keys(rentNames).filter(k=>personal.rent[k]?.[i]==='PASS').map(k=>rentNames[k]);
  gaps.push({key:'rent',label:'주거',text:`입력한 '${rentNames[input.rent]??input.rent}'는 대상이 아니에요.${ok.length?` 대상: ${ok.join(', ')}.`:''}`});
 }
 return gaps;
}
function GapList({gaps}:{gaps:ConditionGap[]}){
 if(!gaps.length)return null;
 return <div className="condition-gaps"><h4>무엇이 달라서 맞지 않나요?</h4><ul>{gaps.map(g=><li key={g.key}><b>{g.label}</b><span>{g.text}</span></li>)}</ul><p>공고 기준과 입력값을 비교한 결과예요. 예외 규정이나 최신 공고에 따라 달라질 수 있어요.</p></div>;
}
function Card({p,regionKey,selected,profile,hasProfile,asOf,favorite,onFavorite,compared,onCompare,full,checks,onCheck}:{p:Program;regionKey:string;selected:boolean;profile:PersonalInput;hasProfile:boolean;asOf:string;favorite:boolean;onFavorite:()=>void;compared:boolean;onCompare:()=>void;full:boolean;checks:string[];onCheck:(key:string)=>void}){
 const result=readRegionalDecision(p.program_id,regionKey,asOf);
 const match=readPersonalDecision(p.program_id,regionKey,profile,asOf);
 return <article className="support-card" data-support-id={p.program_id}>
  <div className="support-card-top"><span className={'support-intake state-'+result.intake.toLowerCase()}>{labels[result.intake]}</span><span>{locationText(p)}</span></div>
  <div className="support-card-actions"><label><input type="checkbox" aria-label={p.title+' 사업 비교 선택'} checked={compared} disabled={!compared&&full} onChange={onCompare}/>비교</label><button type="button" aria-label={p.title+' 관심사업'} aria-pressed={favorite} onClick={onFavorite}>{favorite?'★ 저장됨':'☆ 관심 저장'}</button></div>
  <p className="support-category">{categories[p.category]} · {p.authority}</p><h3>{p.title}</h3><p className="support-benefit">{p.benefit_summary}</p>
  <p className="support-region">{!selected?'지역을 선택해 관련 사업을 좁혀 보세요.':result.region==='PASS'?(p.provinces.length?'선택한 지역의 검토 후보':'전국 대상이라 함께 살펴볼 후보'):result.region==='FAIL'?'선택한 지역과 다른 사업':'거주지·직장·학교 등 세부 지역 확인'}</p>
  {hasProfile&&<div className="support-match" aria-label="내 조건 비교 결과"><strong>{match.summary.candidate_status==='DIFFERENT'?'현재 입력과 다른 조건이 있어요':`입력 조건 ${match.summary.matched_count}개 일치 · 나머지 확인`}</strong><ul>{([['age','나이'],['employment','취업 상태'],['rent','월세 거주']] as const).map(([key,label])=><li key={key} className={'match-'+match[key].toLowerCase()}><span>{label}</span><b>{matchWords[match[key]]}</b></li>)}</ul></div>}
  {hasProfile&&<GapList gaps={conditionGaps(p.program_id,regionKey,profile,asOf)}/>}
  <DeadlineAction program={p} asOf={asOf}/>
  <p className="support-unknown"><strong>지원자격 추가 확인 필요</strong> · 가구소득·재산·거주기간·증빙·중복 지원·선정은 추가 확인합니다. 표시한 일치는 입력 범위의 비교이며 신청·수급 가능 확정이 아닙니다.</p>
  <details><summary>지원 조건·신청 일정·공식 근거</summary>
   <dl><div><dt>연령·대상</dt><dd>{p.age_note}</dd></div><div><dt>소득 기준</dt><dd>{p.income_note}</dd></div><div><dt>모집 안내</dt><dd>{p.schedule_note}</dd></div></dl>
   {hasProfile&&<div className="support-match-reasons"><h4>왜 이렇게 비교했나요?</h4><p><b>나이:</b> {match.rule?.age.note??'연령 기준일·예외를 구조화하지 못해 추가 확인으로 남겼습니다.'} 현재 만 나이만으로 생일을 확정할 수 없는 경계는 추가 확인입니다.</p><p><b>취업:</b> {match.rule?.employment_note??'현재 고용상태로 이 사업의 근로·소득 조건을 확정할 수 없습니다.'}</p><p><b>주거:</b> {match.rule?.rent_note??'월세 필수 조건을 확인하지 않아 월세가 없다는 이유로 제외하지 않습니다.'}</p><p>현재 입력을 공고 대상과 비교합니다. 과거 신청일·응시일의 고용·주거 상태를 증명하지 않습니다.</p>{match.rule?.sources.map((source,i)=><a key={i} href={source.url} target="_blank" rel="noopener noreferrer">조건 비교 근거 {i+1}: {source.title} ↗</a>)}</div>}
   <h4>아직 확인해야 할 항목</h4><ul>{p.required_checks.map((v,i)=><li key={i}>{v}</li>)}</ul>
   <p>현재 관심·거주지역을 바탕으로 한 정보 탐색입니다. 공고 기준일 주민등록·거주기간을 충족했다고 간주하지 않으며 지원금을 생활비·저축액에 더하지 않습니다.</p>
   {p.sources.map((s,i)=><div className="support-source" key={i}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.title} ↗</a><small>자료 기준 {s.basis_date??'게시일 미표시'} · 확인 {s.verified_on} · {s.evidence==='PREVIOUS_VERIFIED_SNAPSHOT'?'기존 공식 스냅샷':s.evidence==='OFFICIAL_INDEXED_PAGE'?'공식 페이지 검색색인 · 원문 추가 확인':'공식 페이지·공고'}</small><p>{s.locator}</p></div>)}
  </details>
  <ApplicationChecklist program={p} checked={checks} onCheck={onCheck} asOf={asOf}/>
  <div className="support-card-bottom"><span>{p.edition} · 자료 확인 {p.sources.map(s=>s.verified_on).sort()[0]}</span><a href={p.sources[0].url} target="_blank" rel="noopener noreferrer" aria-label={p.title+' 공식 안내'}>공식 안내 ↗</a></div>
 </article>;
}
function FavoriteCalendar({programs,asOf}:{programs:Program[];asOf:string}){
 const [message,setMessage]=useState('');
 const dated=programs.filter(p=>deadlineOf(p,asOf));
 if(!programs.length)return null;
 return <span className="favorite-calendar"><button type="button" disabled={!dated.length} onClick={()=>{const text=calendarTextMany(dated,asOf);if(text)setMessage(downloadCalendar(text,'youth-support-deadlines.ics'));}}>관심 사업 마감일 한꺼번에 캘린더 저장 ({dated.length})</button>{!dated.length&&<small>관심 사업 중 마감일이 정해진 공고가 없어요.</small>}{message&&<small role="status">{message}</small>}</span>;
}
export default function RegionalPrograms({browse=true,listPage=false}:{browse?:boolean;listPage?:boolean}={}){
 const [province,setProvince]=useState(''),[city,setCity]=useState(''),[category,setCategory]=useState('ALL'),[query,setQuery]=useState(''),[intake,setIntake]=useState('CURRENT'),[otherRegions,setOtherRegions]=useState(false),[visible,setVisible]=useState(12);
 const [age,setAge]=useState(''),[employment,setEmployment]=useState('unknown'),[rent,setRent]=useState('unknown'),[different,setDifferent]=useState(false);
 const [sort,setSort]=useState('MATCH');
 const asOf=useKoreaDay();const planner=usePlanner(prepared.programs);const [savedOnly,setSavedOnly]=useState(false),[comparison,setComparison]=useState<string[]>([]);
 const profile={age,employment,rent};const hasProfile=age!==''||employment!=='unknown'||rent!=='unknown';
 const [conditionPrompt,setConditionPrompt]=useState(false);
 function openResults(){if(!province&&!hasProfile){setConditionPrompt(true);return;}setSort('MATCH');setFinder('programs');}
 function closeConditionPrompt(edit:boolean){setConditionPrompt(false);if(edit)requestAnimationFrame(()=>document.getElementById('support-province')?.focus());}
 const [finder,setFinder]=useState<'programs'|'compare'|null>(null);
 const districtOptions=(directory.cities as Record<string,string[]>)[province]??[];
 const tableCity=(directory.parent as Record<string,string>)[province+'|'+city]??city;
 const matchedCity=tables.cities[province]?.includes(city)?city:tableCity;
 const regionKey=!province?'*':!city?province:province+'|'+(tables.cities[province]?.includes(matchedCity)?matchedCity:'__OTHER__');
 const toggleComparison=(id:string)=>setComparison(old=>old.includes(id)?old.filter(value=>value!==id):old.length<3?[...old,id]:old);
 const displayProvince=(key:string)=>key==='광주'?'전남광주통합특별시 · 광주 권역':key==='전남'?'전남광주통합특별시 · 전남 권역':key;
 const {ranked:results,excluded}=useMemo(()=>{
  const ranked=[];const excluded:Program[]=[];
  const terms=query.normalize('NFKC').toLocaleLowerCase('ko-KR').trim().split(/\s+/);
  const priority:Record<Intake,number>={VERIFIED_OPEN:0,WINDOW_GUIDANCE:1,CONTINUOUS_GUIDANCE:2,UPCOMING:3,UNKNOWN:4,REVIEW_REQUIRED:5,CLOSED:6,NO_INTAKE:7};
  for(const p of prepared.programs){
    const d=readRegionalDecision(p.program_id,regionKey,asOf);
    const m=readPersonalDecision(p.program_id,regionKey,{age,employment,rent},asOf);
    const mismatch=[m.age,m.employment,m.rent].includes('FAIL');
    const order=priority[d.intake];
    if(browse&&savedOnly&&!planner.favorites.includes(p.program_id))continue;
    if(browse&&category!=='ALL'&&p.category!==category)continue;
    if(province&&(!browse||!otherRegions)&&d.region==='FAIL')continue;
    if(intake==='CURRENT'&&order>=6)continue;
    if(intake==='OPEN'&&order!==0)continue;
    if(intake==='ACTIVE'&&order>2)continue;
    if(intake==='CLOSED'&&order<6)continue;
    if(intake==='REVIEW'&&(order<3||order>5))continue;
    const text=[p.title,p.authority,p.benefit_summary,p.age_note,...p.provinces,p.city??'',...p.aliases].join(' ').normalize('NFKC').toLocaleLowerCase('ko-KR');
    if(!terms.every(t=>text.includes(t)))continue;
    if((!browse||!different)&&mismatch){excluded.push(p);continue;}
    const sameProvince=p.provinces.some(area=>area===province);
    const local=Boolean(city&&city!=='__OTHER__'&&sameProvince&&p.city&&(p.city===city||p.city===tableCity));
    const outside=Boolean(province&&p.provinces.length&&(!sameProvince||(city&&p.city&&!local)));
    ranked.push({p,order,local,mismatch,outside,matchCount:m.summary.matched_count,region:d.region});
  }
  return {excluded,ranked:ranked.sort((a,b)=>
    Number(a.outside)-Number(b.outside)||
    Number(a.order>=6)-Number(b.order>=6)||
    Number(a.mismatch)-Number(b.mismatch)||
    (sort==='DEADLINE'?(deadlineOrder(a.p,asOf)-deadlineOrder(b.p,asOf)||0):0)||
    a.order-b.order||
    Number(b.local)-Number(a.local)||
    (hasProfile?b.matchCount-a.matchCount:0)||
    (province?Number(a.region!=='PASS')-Number(b.region!=='PASS'):0)||
    a.p.title.localeCompare(b.p.title,'ko'))};
 },[regionKey,province,category,query,intake,otherRegions,age,employment,rent,different,hasProfile,asOf,savedOnly,planner.favorites,city,tableCity,browse,sort]);
 const specificCity=Boolean(city&&city!=='__OTHER__');
 const rows=results.filter(row=>!specificCity||otherRegions||!row.outside).map(row=>row.p);
 const wide=results.filter(row=>!row.outside&&!row.p.city&&!row.mismatch&&row.region==='PASS').length;
 const outsideCandidates=results.filter(row=>row.outside).length;
 const scopeTools=specificCity?<div className="support-scope-tools">
  <p><strong>{province==='경기'?'경기도':displayProvince(province)}·전국 대상 {wide}건</strong> · 현재 필터에서 입력 조건과 충돌하지 않는 광역·전국 사업입니다.</p>
  {intake==='OPEN'&&wide===0&&<button type="button" onClick={()=>{setIntake('ACTIVE');setVisible(12);}}>공고상 신청기간·상시 안내까지 보기</button>}
  {(!browse&&outsideCandidates>0)&&<label><input type="checkbox" checked={otherRegions} onChange={e=>setOtherRegions(e.target.checked)}/> 근무지·학교 등 확인이 필요한 다른 지역 사업 {outsideCandidates}건도 보기</label>}
 </div>:null;
 const localRows=results.filter(row=>row.local);
 const localOpen=localRows.filter(row=>row.order===0&&!row.mismatch).length;
 const localNotice=city&&city!=='__OTHER__'
   ? {city,total:localRows.length,open:localOpen} : null;
 const scoped=useMemo(()=>prepared.programs.filter(p=>readRegionalDecision(p.program_id,regionKey,asOf).region!=='FAIL'),[regionKey,asOf]);
 const regionalProvinces=new Set(prepared.programs.flatMap(p=>p.provinces));
 function reset(){setProvince('');setCity('');setCategory('ALL');setQuery('');setIntake('CURRENT');setOtherRegions(false);setAge('');setEmployment('unknown');setRent('unknown');setDifferent(false);setSavedOnly(false);setVisible(12);setSort('MATCH');}
 const comparisonPanel=(<SupportComparison items={prepared.programs.filter(p=>comparison.includes(p.program_id)).map(p=>({program:p,status:labels[readRegionalDecision(p.program_id,regionKey,asOf).intake],match:readPersonalDecision(p.program_id,regionKey,profile,asOf).summary.candidate_status==='DIFFERENT'?'현재 입력과 다른 조건 있음':`입력 조건 ${readPersonalDecision(p.program_id,regionKey,profile,asOf).summary.matched_count}개 일치 · 추가 확인`}))} onClear={()=>setComparison([])}/>);
 return <section className="regional-programs" aria-labelledby="support-discovery-title">
  {conditionPrompt&&<ConditionPrompt onClose={closeConditionPrompt}/>}
  {listPage?<div className="support-browse-heading"><div><h2 id="support-discovery-title">분야별 지원사업</h2><p>{[displayProvince(province)||'전체 지역',city==='__OTHER__'?'기타 지역':city,age&&('만 '+age+'세'),({employed:'근로 중',unemployed:'현재 일하지 않음',self_employed:'자영업·프리랜서'} as Record<string,string>)[employment],rent==='yes'?'월세 거주':rent==='no'?'월세 외 거주':'',query&&('검색어: '+query),intake!=='CURRENT'&&'모집 필터 적용'].filter(Boolean).join(' · ')}</p></div><a href={routeLinks.programs}>지역·조건 변경 →</a></div>:<><div className="support-heading"><p className="eyebrow">나의 조건에서 시작하는 생활 지원</p><h2 id="support-discovery-title">내 조건에 맞는 지원을 찾아보세요.</h2><p>지역·나이·취업·월세 조건을 고른 뒤 ‘내 조건으로 찾기’를 눌러주세요. 모르는 항목은 비워두셔도 괜찮아요.</p>
    <div className="finder-shortcuts"><button type="button" disabled={!validAge(age)} onClick={openResults}>추천 결과 열기 ↗</button><button type="button" onClick={()=>setFinder('compare')}>비교함 열기 ({comparison.length})</button></div></div>
  {!browse&&<a className="home-feature feature-programs support-catalog-entry" href={routeLinks.catalog} aria-label="청년지원사업 보기"><span className="feature-icon" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><path d="M5 7h8l3 3h11v15H5zM10 16h12m-12 4h8"/></svg></span><span><strong>청년지원사업 보기</strong><small>월세·주거부터 취업·교육까지, 분야별 공고 둘러보기</small></span><span className="feature-arrow" aria-hidden="true">→</span></a>}
  <div className="support-filters">
   <div><label htmlFor="support-province">관심·거주 광역지역</label><select id="support-province" value={province} onChange={e=>{setProvince(e.target.value);setOtherRegions(false);setCity('');setVisible(12);}}><option value="">전체 지역에서 살펴보기</option>{prepared.provinces.map(r=><option key={r} value={r}>{displayProvince(r)}</option>)}</select></div>
   <div><label htmlFor="support-city">시·군·구</label><select id="support-city" value={city} disabled={!province||districtOptions.length===0} onChange={e=>{setCity(e.target.value);setOtherRegions(false);setVisible(12);}}><option value="">{province==='세종'?'세종시 전체':'미선택 · 세부지역 추가 확인'}</option>{districtOptions.map(c=><option key={c}>{c}</option>)}<option value="__OTHER__">목록에 없는 시·군·구</option></select></div>
   <div><label htmlFor="support-intake">모집 상태</label><select id="support-intake" value={intake} onChange={e=>{setIntake(e.target.value);setVisible(12);}}><option value="CURRENT">모집·확인할 사업 우선</option><option value="OPEN">공식 접수중 확인</option><option value="ALL">마감 포함 전체</option><option value="ACTIVE">공고상 접수 안내</option><option value="CLOSED">마감·미운영</option><option value="REVIEW">일정·접수 확인 필요</option></select></div>
   <div><label htmlFor="support-age">현재 만 나이</label><input id="support-age" type="number" inputMode="numeric" min="0" max="120" step="1" value={age} aria-invalid={!validAge(age)} aria-describedby="support-profile-help" placeholder="예: 25 · 미입력 가능" onChange={e=>{setAge(e.target.value);setVisible(12);}}/></div>
   <div><label htmlFor="support-employment">현재 취업 상태</label><select id="support-employment" value={employment} onChange={e=>{setEmployment(e.target.value);setVisible(12);}}><option value="unknown">모름·선택하지 않음</option><option value="employed">근로 중 · 정규/단기/아르바이트</option><option value="unemployed">현재 일하지 않음</option><option value="self_employed">자영업·프리랜서</option></select></div>
   <div><label htmlFor="support-rent">현재 월세 거주 여부</label><select id="support-rent" value={rent} onChange={e=>{setRent(e.target.value);setVisible(12);}}><option value="unknown">모름·선택하지 않음</option><option value="yes">월세에 거주해요</option><option value="no">월세가 아니에요 · 전세/자가 등</option></select></div>
   {!validAge(age)&&<p role="alert">만 나이는0~120의 정수로 입력해 주세요. 올바르게 입력할 때까지 나이는 추가 확인으로 남깁니다.</p>}
   <p id="support-profile-help">학생이어도 일한다면 ‘근로 중’을 선택하세요. 현재 상태와 과거 공고 기준일의 상태는 다를 수 있습니다. 소득·재산은 추정하지 않아요.</p>
   <div className="support-search"><label htmlFor="support-query">사업·지원내용 검색</label><GroupedInput id="support-query" type="search" mode="search" value={query} placeholder="월세, 면접, 응시료, 이사비…" onChange={e=>{setQuery(e.target.value);setVisible(12);}}/></div>
   <p>상세 주소·소득·계좌정보를 받지 않습니다. 선택값은 이 화면의 메모리에서만 사용하며 외부 전송·영구 저장하지 않습니다.</p>
   <div className="finder-actions">
    <button type="button" className="finder-primary" disabled={!validAge(age)} onClick={openResults}>내 조건으로 찾기 →</button>
    <button type="button" onClick={()=>setFinder('compare')}>사업 비교하기 ({comparison.length}/3)</button>
    <small>결과 창에서 최대 3개 사업을 비교할 수 있어요.</small>
    <details className="finder-coverage"><summary>전국 지역 선택과 공고 범위</summary><p>현행 16개 광역지역의 시·군·구와 일반구 등 268개 선택지를 제공합니다. 세종은 광역 단위로 찾고, 전남광주통합특별시는 공고의 대상 범위에 따라 두 권역으로 조회합니다. 특정 시·군·구의 공고가 부족하면 전국·광역 대상 사업도 함께 살펴보세요.</p><a href={directory.source.url} target="_blank" rel="noopener noreferrer">행정안전부 지역 코드 · 2026.10.30 기준 ↗</a></details>
   </div>
  </div>
  </>}
  {listPage&&<form role="search" aria-label="지원사업 검색" className="support-catalog-search" onSubmit={e=>e.preventDefault()}>
   <label htmlFor="support-query">사업·지원내용 검색</label>
   <div><GroupedInput id="support-query" type="search" mode="search" value={query} aria-describedby="support-search-help" placeholder="사업명, 지역, 월세·면접·응시료 등으로 검색" onChange={e=>{setQuery(e.target.value);setVisible(12);}}/>{query&&<button type="button" onClick={()=>{setQuery('');setVisible(12);document.getElementById('support-query')?.focus();}}>검색어 지우기</button>}</div>
   <p id="support-search-help">사업명·지역·지원내용에서 검색합니다. 선택한 지역과 분야 조건이 함께 적용돼요.</p>
  </form>}
  {browse&&<><div className="support-categories" aria-label="지원 분야">{Object.entries(categories).map(([k,v])=><button type="button" key={k} aria-pressed={category===k} onClick={()=>{setCategory(k);setVisible(12);}}>{v}</button>)}</div>
  {listPage&&<div className="support-catalog-controls"><div><label htmlFor="support-list-intake">모집 상태</label><select id="support-list-intake" value={intake} onChange={e=>{setIntake(e.target.value);setVisible(12);}}><option value="CURRENT">모집·확인할 사업 우선</option><option value="OPEN">공식 접수중 확인</option><option value="ALL">마감 포함 전체</option><option value="ACTIVE">공고상 접수 안내</option><option value="CLOSED">마감·미운영</option><option value="REVIEW">일정·접수 확인 필요</option></select></div><div><label htmlFor="support-list-sort">지원사업 정렬</label><select id="support-list-sort" value={sort} onChange={e=>{setSort(e.target.value);setVisible(12);}}><option value="MATCH">추천순 · 모집·지역·입력조건</option><option value="DEADLINE">공고 마감일 가까운 순</option></select></div><p>{sort==='DEADLINE'?'지역·입력조건이 맞는 범위에서 날짜가 명시된 공고를 먼저 표시합니다. 상시·일정 미확인 사업은 뒤에 표시하며, 접수중 여부는 별도로 확인하세요.':'관련 지역을 우선하고 모집 상태와 입력 조건 일치를 함께 봅니다. 최종 자격을 확정하지 않습니다.'}</p></div>}
  <DataFreshness scope="supports"/>
  <div className="support-summary"><div><strong>{prepared.programs.length}</strong><span>지원사업·모집 안내</span></div><div><strong>{regionalProvinces.size}</strong><span>자료 검색 권역</span></div><div><strong>{province?scoped.length:'—'}</strong><span>전국·선택지역 검토 목록</span></div></div>
  <p className="support-context" role="status">{province?`${province}${city&&city!=='__OTHER__'?' '+city:''} 기준으로 전국 사업과 해당 지역 사업을 함께 찾고 있어요.`:'지역을 고르면 전국·광역지역·시군구 지원을 함께 좁힐 수 있어요.'} 지역 일치는 신청·수급 가능 확정이 아닙니다.</p>
  {hasProfile&&<p className="support-profile-summary" role="status">{sort==='DEADLINE'?'지역·입력조건이 맞는 범위에서 공고 마감일이 가까운 순서로 표시합니다. 날짜가 없는 사업은 뒤에 배치합니다.':'공식 접수중이고 입력 조건과 충돌이 없는 내 시·군·구 공고를 먼저 보여드려요. 같은 지역·모집 상태 안에서는 일치하는 조건이 많은 순서예요.'} 나이·취업·월세 중 명확히 다른 후보는 기본적으로 숨기며, 아래에서 다시 볼 수 있어요. 모든 후보의 최종 지원자격은 추가 확인입니다.</p>}
  <p className="support-update">{sort==='DEADLINE'?'공고에 적힌 마감일 순서이며, 현재 접수중 순위는 아닙니다.':'공식 접수 상태를 확인한 사업부터 표시합니다.'} 모집기간·접수중 표시가 있어도 잔여예산·여석·최종 자격은 공식 기관에서 확인하세요. 자료 확인 {prepared.updated_on??prepared.built_on} · 화면 기준 {asOf}</p>
  <div className="support-list-tools"><label><input type="checkbox" checked={savedOnly} onChange={e=>{setSavedOnly(e.target.checked);setVisible(12);}}/>관심사업만 ({planner.favorites.length})</label><label><input type="checkbox" checked={different} onChange={e=>{setDifferent(e.target.checked);setVisible(12);}}/>현재 조건과 다른 사업도 보기</label><label><input type="checkbox" checked={otherRegions} onChange={e=>{setOtherRegions(e.target.checked);setVisible(12);}}/>다른 지역 사업도 함께 보기</label><button type="button" onClick={reset}>조건 초기화</button><p>{rows.length}개 검색됨 · 현재 {Math.min(rows.length,visible)}개 표시</p></div>
  {localNotice&&<LocalNotice {...localNotice}/>}{!finder&&scopeTools}
  <div className="support-planner-toolbar"><p>최대 3개 사업을 골라 조건과 확인할 항목을 나란히 비교하세요.</p>{comparison.length>0&&<a href="#support-comparison" onClick={e=>{e.preventDefault();document.getElementById('support-comparison')?.scrollIntoView({block:'start',behavior:'auto'});document.getElementById('support-comparison')?.focus();}}>선택한 {comparison.length}개 비교 보기 ↓</a>}<FavoriteCalendar programs={prepared.programs.filter(p=>planner.favorites.includes(p.program_id))} asOf={asOf}/><button type="button" onClick={planner.clear} disabled={!planner.favorites.length&&!planner.checks.length}>내 기기의 관심·확인 기록 지우기</button></div>
  {planner.error&&<p role="status">{planner.error}</p>}
  </>}
  {finder ? <FinderDialog
    initialView={finder} localNotice={localNotice} scopeTools={scopeTools}
    context={[displayProvince(province)||'전국',city==='__OTHER__'?'기타 지역':city,age&&('만 '+age+'세'),({employed:'근로 중',unemployed:'현재 일하지 않음',self_employed:'자영업·프리랜서'} as Record<string,string>)[employment],rent==='yes'?'월세 거주':rent==='no'?'월세 외 거주':'',browse&&category!=='ALL'?categories[category]:'',query&&('검색어 '+query)].filter(Boolean).join(' · ')}
    items={rows.map((p,index)=>{
      const conditions=readPersonalDecision(p.program_id,regionKey,profile,asOf);
      return {id:p.program_id,title:p.title,location:locationText(p),benefit:p.benefit_summary,
        recommendationLabel:index<3&&conditions.region!=='FAIL'&&conditions.summary.matched_count>0&&conditions.summary.candidate_status!=='DIFFERENT'&&readRegionalDecision(p.program_id,regionKey,asOf).intake==='VERIFIED_OPEN'?'우선 검토 추천 '+String(index+1).padStart(2,'0'):undefined,
        status:labels[readRegionalDecision(p.program_id,regionKey,asOf).intake],
        match:conditions.summary.candidate_status==='DIFFERENT'?'현재 입력과 다른 조건 있음':`입력 조건 ${conditions.summary.matched_count}개 일치`,
        reasons:([['region','지역'],['age','나이'],['employment','취업'],['rent','월세']] as const).map(([key,label])=>label+' '+matchWords[conditions[key]]),
        checks:p.required_checks,url:p.sources[0].url,
        deadline:(()=>{const end=deadlineOf(p,asOf);return end?{label:deadlineLabel(end,asOf),file:p.program_id+'-deadline.ics',text:()=>calendarTextMany([p],asOf)}:undefined;})()};
    })}
    excluded={hasProfile?excluded.map(p=>({id:p.program_id,title:p.title,location:locationText(p),url:p.sources[0].url,gaps:conditionGaps(p.program_id,regionKey,profile,asOf)})):[]}
    help={<YouthCenterHelp province={province} city={city}/>}
    selected={comparison} onSelect={toggleComparison} onClose={()=>setFinder(null)} comparison={comparisonPanel} favorites={planner.favorites} onFavorite={planner.toggleFavorite} storageError={planner.error}
  /> : browse?comparisonPanel:null}

  {browse&&<>{rows.length===0?<div className="support-empty"><h3>등록한 자료 중 표시할 사업이 없어요.</h3><p>해당 지역에 실제 지원사업이 없다는 뜻은 아닙니다. 검색·분야·모집 필터를 바꾸거나 아래 공식 통합검색에서 더 찾아보세요.</p><button type="button" onClick={()=>{reset();setIntake('ALL');}}>전체 등록 사업 보기</button></div>:<div className="support-card-list">{rows.slice(0,visible).map(p=><Card key={p.program_id} p={p} regionKey={regionKey} selected={!!province} profile={profile} hasProfile={hasProfile} asOf={asOf} favorite={planner.favorites.includes(p.program_id)} onFavorite={()=>planner.toggleFavorite(p.program_id)} compared={comparison.includes(p.program_id)} onCompare={()=>setComparison(old=>old.includes(p.program_id)?old.filter(id=>id!==p.program_id):old.length<3?[...old,p.program_id]:old)} full={comparison.length>=3} checks={planner.checks} onCheck={planner.toggleCheck}/>)}</div>}
  {rows.length>visible&&<button type="button" className="support-more" onClick={()=>setVisible(v=>v+12)}>사업 12개 더 보기</button>}
  <YouthCenterHelp province={province} city={city}/>
  <div className="support-scope"><h3>우리 목록 밖의 지원도 더 찾아보세요.</h3><p>현재는 공식 자료를 확보한 사업부터 제공합니다. 전국 모든 시군구·지원사업을 전수 수집한 서비스는 아닙니다. 모집 기간 안이어도 예산 소진·추가 공고·선발 여부는 공식 기관에서 확인해야 합니다.</p><a href="https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch" target="_blank" rel="noopener noreferrer">온통청년 공식 정책 통합검색 ↗</a><p>자료 갱신·알림은 자동으로 실행되지 않습니다. 표시된 확인일과 개별 공고를 확인하세요. 실제 지원금 반영0원·가입/수급 자격 추가 확인 원칙을 유지합니다.</p></div></>}
 </section>;
}
