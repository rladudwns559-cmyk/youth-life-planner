import {useMemo,useState} from 'react';
import {usePolicyList} from './ontong-list';
import {regionStats,cityCounts,comparisonNotes,PROVINCES} from './region-stats';
import {POLICY_GROUPS} from './ontong-policies';
import {readProfile} from './support-profile';
import {useKoreaDay} from './SupportPlanner';
import {routeLinks} from './portal-routing';
import type {OntongPolicyList} from './ontong-policies';
import './region-insights.css';

const fmt=(n:number)=>Math.round(n).toLocaleString('ko-KR');
const label=(p:string)=>p==='광주'?'광주(전남광주 광주 권역)':p==='전남'?'전남(전남광주 전남 권역)':p;

/** One horizontal bar with its number; the bar is decoration, the text carries the value. */
function Bar({name,value,max,mark,highlight,note}:{name:string;value:number;max:number;mark?:number;highlight?:boolean;note?:string}){
  const pct=max?value/max*100:0;
  return <li className={'ri-bar'+(highlight?' is-mine':'')}>
    <span className="ri-bar-name">{name}</span>
    <span className="ri-bar-track" aria-hidden="true">
      <span className="ri-bar-fill" style={{width:pct+'%'}}/>
      {mark!==undefined&&<span className="ri-bar-mark" style={{left:(max?mark/max*100:0)+'%'}}/>}
    </span>
    <span className="ri-bar-value">{fmt(value)}건{note&&<small> {note}</small>}</span>
  </li>;
}

export default function RegionInsights({data}:{data?:OntongPolicyList}){
  const asOf=useKoreaDay();
  const {list,failed}=usePolicyList(data);
  const [province,setProvince]=useState(()=>{const p=readProfile()?.province;return p&&PROVINCES.includes(p)?p:'경기';});
  const stats=useMemo(()=>list?regionStats(list.policies,asOf):null,[list,asOf]);
  const cities=useMemo(()=>list?cityCounts(list.policies,province,asOf):[],[list,province,asOf]);
  if(failed)return <p className="ri-status">정책 자료를 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.</p>;
  if(!list||!stats)return <p className="ri-status" role="status">정책 자료를 불러오는 중이에요…</p>;
  if(!stats.total)return <p className="ri-status">아직 받은 정책 자료가 없어요.</p>;
  const mine=stats.provinces.find(s=>s.province===province)!;
  const sorted=[...stats.provinces].sort((a,b)=>b.count-a.count||a.province.localeCompare(b.province,'ko'));
  const rank=sorted.findIndex(s=>s.province===province)+1;
  const maxProvince=Math.max(...sorted.map(s=>s.count));
  const maxGroup=Math.max(...POLICY_GROUPS.map(g=>Math.max(mine.byGroup[g],stats.averageByGroup[g])));
  const notes=comparisonNotes(mine,stats.averageByGroup);
  const topCities=cities.slice(0,10);
  return <div className="region-insights">
    <ul className="ri-tiles" aria-label="정책 수 요약">
      <li><b>{fmt(stats.total)}건</b><span>지금 신청할 수 있거나 상시 모집 중인 온통청년 정책</span></li>
      <li><b>{fmt(stats.national)}건</b><span>전국 어디서나 대상인 정책</span></li>
      <li><b>{fmt(stats.regional)}건</b><span>특정 지역 주민만 대상인 정책</span></li>
    </ul>

    <div className="ri-filter"><label htmlFor="ri-province">비교할 지역</label>
      <select id="ri-province" value={province} onChange={e=>setProvince(e.target.value)}>{PROVINCES.map(p=><option key={p} value={p}>{label(p)}</option>)}</select></div>

    <section className="ri-card" aria-labelledby="ri-provinces-title">
      <h3 id="ri-provinces-title">광역지역별 지역 대상 정책 수</h3>
      <p className="ri-lead">{label(province)} 지역은 17개 광역 중 <b>{rank}번째</b>로 많아요({fmt(mine.count)}건 · 평균 {fmt(stats.average)}건). 전국 대상 {fmt(stats.national)}건은 모든 지역에 더해져요.</p>
      <ol className="ri-bars">{sorted.map(s=><Bar key={s.province} name={s.province} value={s.count} max={maxProvince} highlight={s.province===province}/>)}</ol>
    </section>

    <section className="ri-card" aria-labelledby="ri-groups-title">
      <h3 id="ri-groups-title">분야별 비교: {label(province)} vs 17개 광역 평균</h3>
      <p className="ri-legend"><span className="ri-key-bar" aria-hidden="true"/>{province} 지역 대상 정책 <span className="ri-key-mark" aria-hidden="true"/>17개 광역 평균</p>
      <ol className="ri-bars">{POLICY_GROUPS.map(g=><Bar key={g} name={g} value={mine.byGroup[g]} max={maxGroup} mark={stats.averageByGroup[g]} highlight note={`(평균 ${fmt(stats.averageByGroup[g])}건)`}/>)}</ol>
      <ul className="ri-notes">{notes.slice(0,3).map(n=><li key={n.group} className={n.diff>0?'up':n.diff<0?'down':undefined}>{n.text}</li>)}</ul>
    </section>

    {topCities.length>0&&<section className="ri-card" aria-labelledby="ri-cities-title">
      <h3 id="ri-cities-title">{label(province)} 안 시·군·구별 정책 수{cities.length>10?' (상위 10곳)':''}</h3>
      <p className="ri-lead">광역 전체가 대상인 정책은 빼고, 시·군·구를 지정한 정책만 셌어요.</p>
      <ol className="ri-bars">{topCities.map(c=><Bar key={c.city} name={c.city} value={c.count} max={topCities[0].count}/>)}</ol>
    </section>}

    <details className="ri-table"><summary>숫자 표로 보기</summary>
      <table><caption>광역지역별·분야별 지역 대상 정책 수</caption>
        <thead><tr><th scope="col">지역</th><th scope="col">전체</th>{POLICY_GROUPS.map(g=><th scope="col" key={g}>{g}</th>)}</tr></thead>
        <tbody>{sorted.map(s=><tr key={s.province} className={s.province===province?'is-mine':undefined}><th scope="row">{s.province}</th><td>{s.count}</td>{POLICY_GROUPS.map(g=><td key={g}>{s.byGroup[g]}</td>)}</tr>)}
          <tr><th scope="row">전국 대상</th><td>{stats.national}</td>{POLICY_GROUPS.map(g=><td key={g}>{stats.nationalByGroup[g]}</td>)}</tr></tbody>
      </table>
    </details>

    <p className="ri-note">출처: 온통청년(한국고용정보원) · {list.fetched_on??''} 수집 · {asOf} 기준 신청 기간이 끝나지 않은 정책. 여러 지역이 대상인 정책은 지역마다 한 번씩 세요. 청년 인구는 반영하지 않았어요. 한 정책이 여러 분야에 걸치면 분야마다 셌어요.</p>
    <a className="ri-cta" href={routeLinks.programs}>내 조건으로 맞는 정책 찾기 →</a>
  </div>;
}
