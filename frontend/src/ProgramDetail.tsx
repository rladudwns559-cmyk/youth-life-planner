import {useEffect,useState} from 'react';
import prepared from './public-data/current-support-web.json';
import {readRegionalDecision,intakeLabels,locationText,programIndex} from './support-status';
import {readPersonalDecision,conditionGaps,categories} from './RegionalPrograms';
import {DeadlineAction,useKoreaDay} from './SupportPlanner';
import {readProfile} from './support-profile';
import YouthCenterHelp from './YouthCenterHelp';
import {programIdFromHash,routeLinks} from './portal-routing';
import './regional-programs.css';
import './program-detail.css';

type Program=typeof prepared.programs[number];
const matchWords={PASS:'입력 조건 일치',FAIL:'현재 입력과 다름',UNKNOWN:'추가 확인'} as const;
const evidenceText=(e:string)=>e==='AUTOMATED_PAGE_MATCH'?'자동 대조 · 사람이 읽은 확인 아님':e==='PREVIOUS_VERIFIED_SNAPSHOT'?'기존 공식 스냅샷':e==='OFFICIAL_INDEXED_PAGE'?'공식 페이지 검색색인 · 원문 추가 확인':'공식 페이지·공고';

export function findProgram(id:string|null):Program|null{
  if(!id)return null;const i=programIndex.get(id);return i===undefined?null:prepared.programs[i];
}

function useHashProgramId(){
  const [id,setId]=useState(()=>programIdFromHash(window.location.hash));
  useEffect(()=>{const on=()=>{const next=programIdFromHash(window.location.hash);if(next)setId(next);};window.addEventListener('hashchange',on);return()=>window.removeEventListener('hashchange',on);},[]);
  return id;
}

function MyMatch({p,asOf}:{p:Program;asOf:string}){
  const saved=readProfile();
  const has=!!saved&&(saved.age!==''||saved.employment!=='unknown'||saved.rent!=='unknown'||saved.province!=='');
  if(!saved||!has)return <div className="detail-mine"><h2>내 조건과 비교</h2><p>지원사업 화면에서 “이 기기에 내 조건 기억하기”를 켜고 조건을 넣으면, 여기서도 이 사업과 바로 비교해 드려요.</p><a href={routeLinks.programs}>내 조건 넣고 비교하기 →</a></div>;
  const regionKey=saved.province||'*';
  const input={age:saved.age,employment:saved.employment,rent:saved.rent};
  const m=readPersonalDecision(p.program_id,regionKey,input,asOf);
  const gaps=conditionGaps(p.program_id,regionKey,input,asOf);
  return <div className="detail-mine"><h2>내 조건과 비교</h2>
    <p className="detail-mine-profile">이 기기에 기억한 조건: {[saved.province||'지역 미선택',saved.city,saved.age&&('만 '+saved.age+'세')].filter(Boolean).join(' · ')}</p>
    <ul className="support-match">{([['region','지역'],['age','나이'],['employment','취업 상태'],['rent','월세 거주']] as const).map(([k,label])=><li key={k} className={'match-'+m[k].toLowerCase()}><span>{label}</span><b>{matchWords[m[k]]}</b></li>)}</ul>
    {gaps.length>0&&<div className="condition-gaps"><h3>무엇이 달라서 맞지 않나요?</h3><ul>{gaps.map(g=><li key={g.key}><b>{g.label}</b><span>{g.text}</span></li>)}</ul></div>}
  </div>;
}

function Share({p}:{p:Program}){
  const [message,setMessage]=useState('');
  async function share(){
    const url=window.location.href;
    try{
      if(typeof navigator.share==='function'){await navigator.share({title:p.title,text:p.benefit_summary,url});setMessage('공유 창을 열었어요.');return;}
      await navigator.clipboard.writeText(url);setMessage('링크를 복사했어요. 원하는 곳에 붙여 넣으세요.');
    }catch{setMessage('이 브라우저에서는 자동 복사가 안 돼요. 주소창의 링크를 직접 복사해 주세요.');}
  }
  return <div className="detail-share"><button type="button" onClick={share}>이 사업 링크 공유</button>{message&&<small role="status">{message}</small>}</div>;
}

/** One program on its own page: #/programs/item/<id>. */
export default function ProgramDetail({active=true}:{active?:boolean}={}){
  const id=useHashProgramId();
  const asOf=useKoreaDay();
  const p=findProgram(id);
  // The page stays mounted when hidden, so the tab title follows whether it is the visible page.
  useEffect(()=>{if(!active||!p)return;const before=document.title;document.title=`${p.title} | 청년 경제생활`;return()=>{document.title=before;};},[p,active]);
  if(!p)return <section className="program-detail" aria-labelledby="portal-detail-title">
    <a className="portal-back" href={routeLinks.catalog}>← 청년지원사업 목록으로</a>
    <h1 id="portal-detail-title" data-page-heading tabIndex={-1}>사업을 찾을 수 없어요</h1>
    <p>주소가 바뀌었거나 목록에서 빠진 사업일 수 있어요. 지원사업 목록에서 다시 찾아 주세요.</p>
    <a className="finder-primary detail-cta" href={routeLinks.catalog}>지원사업 목록 보기 →</a>
  </section>;
  const intake=readRegionalDecision(p.program_id,'*',asOf).intake;
  return <article className="program-detail" aria-labelledby="portal-detail-title">
    <a className="portal-back" href={routeLinks.catalog}>← 청년지원사업 목록으로</a>
    <p className="eyebrow">{categories[p.category]} · {p.authority}</p>
    <h1 id="portal-detail-title" data-page-heading tabIndex={-1}>{p.title}</h1>
    <div className="detail-meta"><span className={'support-intake state-'+intake.toLowerCase()}>{intakeLabels[intake]}</span><span>{locationText(p)}</span><span>{p.edition}</span></div>
    <p className="detail-benefit">{p.benefit_summary}</p>
    <DeadlineAction program={p} asOf={asOf}/>
    <div className="detail-actions"><a className="finder-primary detail-cta" href={p.sources[0].url} target="_blank" rel="noopener noreferrer">공식 안내 보기 ↗</a><Share p={p}/></div>
    <MyMatch p={p} asOf={asOf}/>
    <section className="detail-section"><h2>지원 조건과 일정</h2>
      <dl><div><dt>연령·대상</dt><dd>{p.age_note}</dd></div><div><dt>소득 기준</dt><dd>{p.income_note}</dd></div><div><dt>모집 안내</dt><dd>{p.schedule_note}</dd></div></dl>
    </section>
    <section className="detail-section"><h2>신청 전에 확인할 것</h2><ul>{p.required_checks.map(t=><li key={t}>{t}</li>)}</ul>
      <p className="detail-note">표시한 조건 비교는 신청·수급 가능을 확정하지 않아요. 가구소득·재산·거주기간·증빙·중복 지원은 공고에서 확인하세요.</p></section>
    <section className="detail-section"><h2>근거 자료</h2>
      {p.sources.map((s,i)=><div className="support-source" key={i}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.title} ↗</a><small>자료 기준 {s.basis_date??'게시일 미표시'} · 확인 {s.verified_on} · {evidenceText(s.evidence)}</small><p>{s.locator}</p></div>)}
    </section>
    <YouthCenterHelp province={p.provinces.length===1?p.provinces[0]:''} city={p.city??''}/>
  </article>;
}
