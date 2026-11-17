import {useMemo} from 'react';
import prepared from './public-data/current-support-web.json';
import {readProfile} from './support-profile';
import {readPlanner,deadlineOf,daysLeft,useKoreaDay} from './SupportPlanner';
import {usePolicyList} from './ontong-list';
import {rankPolicies,SCHOOL_NAMES,MARRIAGE_NAMES} from './ontong-policies';
import {useOntongSaved} from './ontong-saved';
import {useSeenPolicies} from './ontong-seen';
import {routeLinks,programLink} from './portal-routing';
import './home-summary.css';

const jobNames:Record<string,string>={employed:'근로 중',unemployed:'현재 일하지 않음',self_employed:'자영업·프리랜서'};
const knownTitles=prepared.programs.map(p=>({title:p.title,provinces:p.provinces as string[],city:p.city??null}));
const md=(iso:string)=>{const [,m,d]=iso.split('-').map(Number);return `${m}월 ${d}일`;};

type Closing={key:string;title:string;end:string;href:string;external:boolean};

/**
 * What needs attention today, on the home screen: policies that fit the remembered conditions,
 * new ones since the last visit, and saved programs or policies closing within a week.
 * It appears only for people who keep their conditions or saved something on this device.
 */
export default function HomeSummary(){
  const asOf=useKoreaDay();
  const profile=useMemo(()=>readProfile(),[]);
  const saved=useOntongSaved();
  const favorites=useMemo(()=>readPlanner(prepared.programs).favorites,[]);
  const {list}=usePolicyList(undefined,!!profile);
  const ids=useMemo(()=>list?list.policies.map(p=>p.id):null,[list]);
  const seen=useSeenPolicies(profile?ids:null,asOf);
  const p=profile?{province:profile.province,city:profile.city,age:profile.age,employment:profile.employment,school:profile.school,marriage:profile.marriage}:null;
  const fitting=useMemo(()=>list&&p?rankPolicies(list.policies,p,asOf,knownTitles):null,[list,asOf]); // eslint-disable-line react-hooks/exhaustive-deps
  const closing:Closing[]=[
    ...prepared.programs.filter(x=>favorites.includes(x.program_id)).flatMap(x=>{const end=deadlineOf(x,asOf);return end&&daysLeft(end,asOf)<=7?[{key:x.program_id,title:x.title,end,href:programLink(x.program_id),external:false}]:[];}),
    ...saved.saved.filter(s=>s.end&&s.end>=asOf&&daysLeft(s.end,asOf)<=7).map(s=>({key:'ontong-'+s.id,title:s.title,end:s.end!,href:s.url,external:true})),
  ].sort((a,b)=>a.end.localeCompare(b.end)||a.title.localeCompare(b.title,'ko'));
  if(!profile&&!closing.length)return null;
  const who=profile?[profile.province||'전국',profile.city&&profile.city!=='__OTHER__'?profile.city:'',profile.age&&'만 '+profile.age+'세',jobNames[profile.employment]??'',SCHOOL_NAMES[profile.school]??'',MARRIAGE_NAMES[profile.marriage]??''].filter(Boolean).join(' · '):'';
  const fresh=fitting?fitting.filter(r=>seen.fresh.has(r.p.id)).length:0;
  return <section className="home-summary" aria-labelledby="home-summary-title">
    <h2 id="home-summary-title">오늘 확인할 것</h2>
    {profile&&<p className="home-summary-who">이 기기에 기억한 조건: {who}</p>}
    <ul className="home-summary-stats">
      {profile&&<li><b>{fitting?fitting.length.toLocaleString('ko-KR')+'건':'…'}</b><span>내 조건과 맞지 않는 것을 뺀 온통청년 정책</span><a href={routeLinks.catalog}>정책 보기 →</a></li>}
      {profile&&seen.since&&<li><b>{fresh}건</b><span>지난 방문({md(seen.since)}) 이후 새로 올라온 정책</span>{fresh>0&&<a href={routeLinks.catalog}>새 정책 보기 →</a>}</li>}
      <li><b>{closing.length}건</b><span>일주일 안에 마감되는 관심 사업·정책</span></li>
    </ul>
    {closing.length>0&&<ul className="home-summary-closing">{closing.slice(0,4).map(c=>{const n=daysLeft(c.end,asOf);return <li key={c.key}>
      {c.external?<a href={c.href} target="_blank" rel="noopener noreferrer">{c.title} ↗</a>:<a href={c.href}>{c.title}</a>}
      <span>{md(c.end)} · {n===0?'오늘 마감':'D-'+n}</span></li>;})}</ul>}
    <p className="home-summary-note">조건과 관심 목록은 이 기기에만 저장돼 있어요. 자격과 모집 여부는 공식 안내에서 확인하세요.</p>
  </section>;
}
