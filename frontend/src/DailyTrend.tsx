import ontongFile from './public-data/metrics-ontong.json';
import supportFile from './public-data/metrics-support.json';
import './daily-trend.css';

/** Day-by-day record of the automatic updates (tools/record_daily_metrics.py). */
export type OntongDay={date:string;policies:number;new:number|null;removed:number|null;centers?:number};
/** manual: run by hand on a PC before the daily job existed (it reaches more sites than GitHub's servers). */
export type SupportDay={date:string;checked:number;renewed:number;closed_signal:number;not_matched:number;manual?:boolean};
type Files={ontong:{days:OntongDay[]};support:{days:SupportDay[]}};
const real:Files={ontong:ontongFile as unknown as Files['ontong'],support:supportFile as unknown as Files['support']};

const md=(iso:string)=>{const [,m,d]=iso.split('-').map(Number);return `${m}/${d}`;};
const daysBetween=(a:string,b:string)=>Math.round((Date.parse(b+'T00:00:00Z')-Date.parse(a+'T00:00:00Z'))/86_400_000)+1;

/** Small vertical bars, one per day; each bar carries its number, a missing value says why. */
function DayBars({title,rows,unit,empty}:{title:string;rows:{date:string;value:number|null;mark?:string}[];unit:string;empty:string}){
  const max=Math.max(1,...rows.map(r=>r.value??0));
  return <figure className="dt-figure">
    <figcaption>{title}</figcaption>
    <ol className="dt-bars">{rows.map(r=><li key={r.date} title={`${r.date} · ${r.value===null?empty:r.value+unit}`}>
      <span className="dt-value">{r.value===null?'–':r.value}</span>
      <span className="dt-track" aria-hidden="true">{r.value!==null&&<span className="dt-fill" style={{height:r.value/max*100+'%'}}/>}</span>
      <span className="dt-day">{md(r.date)}{r.mark&&<small>{r.mark}</small>}</span>
      <span className="sr-only">{r.date} {r.value===null?empty:r.value+unit}</span>
    </li>)}</ol>
  </figure>;
}

export default function DailyTrend({files=real}:{files?:Files}){
  const ontong=[...files.ontong.days].sort((a,b)=>a.date.localeCompare(b.date));
  const support=[...files.support.days].sort((a,b)=>a.date.localeCompare(b.date));
  const dates=[...new Set([...ontong.map(d=>d.date),...support.map(d=>d.date)])].sort();
  if(!dates.length)return null;
  const first=dates[0],last=dates[dates.length-1];
  const byDate=(list:{date:string}[],date:string)=>list.find(d=>d.date===date);
  return <section className="ri-card daily-trend" aria-labelledby="dt-title">
    <h3 id="dt-title">매일 자동 갱신 기록</h3>
    <p className="ri-lead">{md(first)}부터 {md(last)}까지 {daysBetween(first,last)}일 동안의 기록이에요. 매일 아침 자동 작업이 공식 자료를 다시 받아 대조하고, 결과를 여기에 한 줄씩 남겨요.{support.some(d=>d.manual)?' ‘PC’ 표시가 있는 날은 자동 작업을 만들기 전에 PC에서 직접 실행한 결과예요.':''}</p>
    <div className="dt-charts">
      {support.length>0&&<DayBars title="지원사업 공식 페이지 자동 대조 · 일치해서 갱신한 사업 수" unit="건" empty="기록 없음" rows={support.map(d=>({date:d.date,value:d.renewed,mark:d.manual?'PC':undefined}))}/>}
      {ontong.length>0&&<DayBars title="온통청년에 새로 올라온 정책 수" unit="건" empty="첫 수집일이라 비교 대상 없음" rows={ontong.map(d=>({date:d.date,value:d.new}))}/>}
    </div>
    <details className="ri-table"><summary>일별 기록 표로 보기</summary>
      <table><caption>날짜별 자동 갱신 결과</caption>
        <thead><tr><th scope="col">날짜</th><th scope="col">온통청년 정책</th><th scope="col">새 정책</th><th scope="col">빠진 정책</th><th scope="col">청년센터</th><th scope="col">사업 대조</th><th scope="col">일치·갱신</th><th scope="col">마감 표시</th></tr></thead>
        <tbody>{dates.map(date=>{const o=byDate(ontong,date) as OntongDay|undefined;const s=byDate(support,date) as SupportDay|undefined;return <tr key={date}>
          <th scope="row">{date}{s?.manual?' (PC)':''}</th><td>{o?.policies??'–'}</td><td>{o?(o.new??'–'):'–'}</td><td>{o?(o.removed??'–'):'–'}</td><td>{o?.centers??'–'}</td>
          <td>{s?.checked??'–'}</td><td>{s?.renewed??'–'}</td><td>{s?.closed_signal??'–'}</td></tr>;})}</tbody>
      </table>
    </details>
    <p className="ri-note">사업 대조는 공식 페이지에서 사업명·마감일·마감 표시를 자동으로 확인한 결과예요(사람이 읽은 확인 아님). 일부 기관 누리집은 자동 접속이 막혀 ‘일치·갱신’ 수가 날마다 조금씩 달라요. ‘–’는 그날 기록이 없거나 첫 수집일이라 비교할 수 없다는 뜻이에요.</p>
  </section>;
}
