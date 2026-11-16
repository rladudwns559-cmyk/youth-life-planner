import {useId,useMemo,useState} from 'react';
import {futureStages,stageLabel,assumesGraduation,type Stage} from './ontong-timeline';
import type {OntongPolicy,OntongProfile} from './ontong-policies';
import './future-timeline.css';

const SHOW=3;

function Stages({stages,profile}:{stages:Stage[];profile:OntongProfile}){
  const changes=stages.slice(1);
  return <>
    <p className="future-timeline-lead">지금 올라와 있는 공고를 기준으로, 나이가 들면서{assumesGraduation(profile.school)?' 그리고 대학을 졸업하면서':''} 맞는 정책이 어떻게 바뀌는지 보여 드려요. 지역·취업 상태·혼인 여부는 지금과 같다고 가정했어요.</p>
    <ol className="future-timeline-list">{stages.map(s=><li key={s.key} className={s.years===0?'is-now':undefined}>
      <span className="future-timeline-dot" aria-hidden="true"/>
      <div>
        <p className="future-timeline-when"><b>{stageLabel(s)}</b> <span>맞는 정책 {s.count.toLocaleString('ko-KR')}건</span></p>
        {s.years>0&&<p className="future-timeline-delta">{s.opened.length>0&&<span className="opened">+{s.opened.length} 열림</span>}{s.closed.length>0&&<span className="closed">−{s.closed.length} 닫힘</span>}{!s.opened.length&&!s.closed.length&&<span>바뀌는 정책 없음</span>}</p>}
        {s.opened.length>0&&<ul className="future-timeline-titles">{s.opened.slice(0,SHOW).map(p=><li key={p.id}><a href={p.url} target="_blank" rel="noopener noreferrer">{p.title} ↗</a></li>)}{s.opened.length>SHOW&&<li className="more">외 {s.opened.length-SHOW}건</li>}</ul>}
        {s.closed.length>0&&<details className="future-timeline-closed"><summary>닫히는 정책 {s.closed.length}건 보기</summary><ul>{s.closed.slice(0,10).map(p=><li key={p.id}>{p.title}</li>)}{s.closed.length>10&&<li>외 {s.closed.length-10}건</li>}</ul></details>}
      </div>
    </li>)}</ol>
    {changes.length===0&&<p className="future-timeline-empty">만 40세까지 나이 때문에 바뀌는 정책은 없어요.</p>}
    <small>지금 공고의 나이·학력 조건만 따졌어요. 해마다 공고가 새로 나오고 조건이 바뀔 수 있으니, 그 해가 되면 다시 확인하세요.{assumesGraduation(profile.school)?' 대학 재학이면 1년 뒤 졸업 예정, 2년 뒤 졸업으로 가정했어요.':''}</small>
  </>;
}

/**
 * The years ahead on one line: how many 온통청년 policies fit each year, and what opens or
 * closes. It ranks the whole list once per year, so it is worked out only when opened.
 */
export default function FutureTimeline({list,profile,asOf,known,defaultOpen=false}:{list:OntongPolicy[];profile:OntongProfile;asOf:string;known:string[];defaultOpen?:boolean}){
  const [open,setOpen]=useState(defaultOpen);
  const id=useId();
  const stages=useMemo(()=>open?futureStages(list,profile,asOf,known):undefined,[open,list,profile.province,profile.city,profile.age,profile.employment,profile.school,profile.marriage,asOf,known]); // eslint-disable-line react-hooks/exhaustive-deps
  return <section className="future-timeline" aria-labelledby={id+'title'}>
    <div className="future-timeline-head">
      <h4 id={id+'title'}>내 미래 정책 타임라인</h4>
      <button type="button" aria-expanded={open} aria-controls={id+'body'} onClick={()=>setOpen(v=>!v)}>{open?'접기':'앞으로 열리고 닫히는 정책 보기'}</button>
    </div>
    <div id={id+'body'} className="future-timeline-body" hidden={!open}>
      {open&&(stages?<Stages stages={stages} profile={profile}/>:<p className="future-timeline-empty">만 나이를 넣으면 앞으로 몇 년 동안 열리고 닫히는 정책을 한 줄로 보여 드려요.</p>)}
    </div>
  </section>;
}
