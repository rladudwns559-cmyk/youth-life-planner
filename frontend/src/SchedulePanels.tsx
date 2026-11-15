import {useState} from 'react';
import {deadlineOf,daysLeft} from './SupportPlanner';
import {readRegionalDecision,intakeLabels,locationText,type SupportProgram} from './support-status';
import {programLink} from './portal-routing';
import {CALENDAR_FEEDS,calendarUrl} from './static-site';
import './schedule-panels.css';

const md=(iso:string)=>{const [,m,d]=iso.split('-').map(Number);return `${m}월 ${d}일`;};

/** Saved programs on one timeline: dated deadlines by month, then the ones without a date. */
export function FavoriteSchedule({programs,asOf}:{programs:SupportProgram[];asOf:string}){
  if(!programs.length)return null;
  const rows=programs.map(p=>({p,end:deadlineOf(p,asOf),status:intakeLabels[readRegionalDecision(p.program_id,'*',asOf).intake]}));
  const dated=rows.filter(r=>r.end).sort((a,b)=>a.end!.localeCompare(b.end!)||a.p.title.localeCompare(b.p.title,'ko'));
  const undated=rows.filter(r=>!r.end);
  const months=[...new Set(dated.map(r=>r.end!.slice(0,7)))];
  return <section className="favorite-schedule" aria-labelledby="favorite-schedule-title">
    <h3 id="favorite-schedule-title">내 관심 사업 일정</h3>
    <p className="schedule-lead">관심 저장한 사업 {programs.length}개를 공고 마감일 순서로 모았어요. 접수 여부와 잔여 예산은 공식 안내에서 확인하세요.</p>
    {months.map(m=><div key={m} className="schedule-month"><h4>{Number(m.slice(5))}월 마감</h4><ol>
      {dated.filter(r=>r.end!.startsWith(m)).map(({p,end,status})=>{const n=daysLeft(end!,asOf);return <li key={p.program_id} className={n<=7?'soon':undefined}>
        <span className="schedule-day" aria-hidden="true"><b>{md(end!)}</b><small>{n===0?'오늘':'D-'+n}</small></span>
        <div><a href={programLink(p.program_id)}>{p.title}</a><small>{locationText(p)} · {status}{p.starts_on?` · 신청 시작 ${md(p.starts_on)}`:''}</small><span className="sr-only">{md(end!)} 마감, {n===0?'오늘 마감':`${n}일 남음`}</span></div>
      </li>;})}
    </ol></div>)}
    {undated.length>0&&<div className="schedule-month"><h4>마감일이 정해지지 않은 사업</h4><ol>
      {undated.map(({p,status})=><li key={p.program_id}><span className="schedule-day" aria-hidden="true"><b>상시·미정</b></span>
        <div><a href={programLink(p.program_id)}>{p.title}</a><small>{locationText(p)} · {status}</small></div></li>)}
    </ol></div>}
  </section>;
}

/** Subscribe once, and new deadlines for the region arrive in the phone calendar by themselves. */
export function CalendarSubscribe({province}:{province:string}){
  const initial=CALENDAR_FEEDS.find(f=>f.province===province)?.slug??'all';
  const [slug,setSlug]=useState(initial);
  const [message,setMessage]=useState('');
  const feed=CALENDAR_FEEDS.find(f=>f.slug===slug)!;
  const https=calendarUrl(feed.slug);
  const webcal=https.replace(/^https:/,'webcal:');
  async function copy(){try{await navigator.clipboard.writeText(https);setMessage('구독 주소를 복사했어요. 캘린더 앱의 “URL로 구독”에 붙여 넣으세요.');}catch{setMessage('자동 복사가 안 돼요. 아래 주소를 직접 복사해 주세요.');}}
  return <section className="calendar-subscribe" aria-labelledby="calendar-subscribe-title">
    <h3 id="calendar-subscribe-title">지역 마감일을 캘린더로 구독하기</h3>
    <p>한 번 구독하면 그 지역(전국 대상 포함) 지원사업의 신청 마감일이 휴대폰·PC 캘린더에 자동으로 들어와요. 새 공고가 생기면 캘린더 앱이 알아서 갱신해요.</p>
    <div className="calendar-subscribe-row"><label htmlFor="calendar-region">지역</label>
      <select id="calendar-region" value={slug} onChange={e=>{setSlug(e.target.value);setMessage('');}}>{CALENDAR_FEEDS.map(f=><option key={f.slug} value={f.slug}>{f.label}</option>)}</select></div>
    <div className="calendar-subscribe-actions">
      <a href={`https://calendar.google.com/calendar/render?cid=${encodeURIComponent(webcal)}`} target="_blank" rel="noopener noreferrer">구글 캘린더에 추가 ↗</a>
      <a href={webcal}>아이폰·맥·아웃룩에서 구독</a>
      <button type="button" onClick={copy}>구독 주소 복사</button>
    </div>
    <p className="calendar-subscribe-url"><code>{https}</code></p>
    {message&&<p role="status" className="calendar-subscribe-status">{message}</p>}
    <small>공고에 적힌 마감일 기준이에요. 실제 마감 시각·예산 소진·자격은 공식 안내에서 확인하세요. 캘린더 앱에 따라 반영까지 몇 시간~하루가 걸릴 수 있어요.</small>
  </section>;
}
