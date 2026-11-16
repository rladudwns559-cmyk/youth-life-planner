import {useEffect,useMemo,useState} from 'react';
import {rankPolicies,leftOut,gapText,ageText,jobText,regionText,categoryText,policyGroups,closesSoon,POLICY_GROUPS,SOON_DAYS,type OntongPolicy,type OntongPolicyList,type OntongProfile,type Fit,type PolicyGroup} from './ontong-policies';
import {useOntongSaved,type SavedPolicy} from './ontong-saved';
import {useSeenPolicies} from './ontong-seen';
import {deadlineLabel,daysLeft} from './SupportPlanner';
import './ontong-policies.css';

const fitWords:Record<Fit,string>={PASS:'일치',UNKNOWN:'추가 확인',FAIL:'다름'};
const STEP=8;

/** The policy list is large, so it loads as its own file only when this section appears. */
function usePolicyList(given?:OntongPolicyList){
  const [list,setList]=useState<OntongPolicyList|null>(given??null);
  const [failed,setFailed]=useState(false);
  useEffect(()=>{
    if(given){setList(given);return;}
    let live=true;
    import('./public-data/youth-policies.json').then(m=>{if(live)setList(m.default as unknown as OntongPolicyList);}).catch(()=>{if(live)setFailed(true);});
    return()=>{live=false;};
  },[given]);
  return {list,failed};
}

function Star({p,on,onToggle}:{p:OntongPolicy;on:boolean;onToggle:()=>void}){
  return <button type="button" className="ontong-save" aria-pressed={on} aria-label={p.title+' 관심 정책'} onClick={onToggle}>{on?'★ 저장됨':'☆ 관심 저장'}</button>;
}

const md=(iso:string)=>{const [,m,d]=iso.split('-').map(Number);return `${m}월 ${d}일`;};

/** Saved policies whose application closes within a week, so they are not missed. */
function SavedClosing({saved,asOf}:{saved:SavedPolicy[];asOf:string}){
  const soon=saved.filter(s=>s.end&&s.end>=asOf&&daysLeft(s.end,asOf)<=7).sort((a,b)=>a.end!.localeCompare(b.end!));
  if(!soon.length)return null;
  return <div className="ontong-alert" role="note" aria-label="곧 마감되는 관심 정책">
    <strong>관심 저장한 정책 {soon.length}건이 일주일 안에 마감돼요</strong>
    <ul>{soon.map(s=>{const n=daysLeft(s.end!,asOf);return <li key={s.id}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.title} ↗</a> <span>{md(s.end!)} · {n===0?'오늘 마감':'D-'+n}</span></li>;})}</ul>
  </div>;
}

/** Policies in the area left out because of age or employment, and what would open them. */
function LeftOut({list,profile,asOf,known,query}:{list:OntongPolicy[];profile:OntongProfile;asOf:string;known:string[];query:string}){
  const {excluded,openings}=useMemo(()=>leftOut(list,profile,asOf,known,query),[list,profile.province,profile.city,profile.age,profile.employment,asOf,known,query]); // eslint-disable-line react-hooks/exhaustive-deps
  if(!excluded.length)return null;
  const byAge=excluded.filter(r=>r.age==='FAIL').length,byJob=excluded.filter(r=>r.job==='FAIL').length;
  return <details className="ontong-leftout">
    <summary>조건이 달라 뺀 정책 {excluded.length}건 · 왜 빠졌는지 보기</summary>
    <p>{[byAge&&`나이 때문에 ${byAge}건`,byJob&&`취업 상태 때문에 ${byJob}건`].filter(Boolean).join(', ')} 뺐어요. 입력한 조건과 공고 조건만 비교했어요.</p>
    {openings.length>0&&<div className="ontong-openings"><h4>조건이 바뀌면 열리는 정책</h4><ul>{openings.map(o=><li key={o.key}><b>{o.label}</b> {o.policies.length}건 · {o.policies.slice(0,3).map(p=>p.title).join(', ')}{o.policies.length>3?' 외':''}</li>)}</ul>
      {openings.some(o=>o.key.startsWith('age-'))&&<small>나이로 열리는 정책은 지금 공고 기준이에요. 그때도 같은 공고가 있는지는 다시 확인하세요.</small>}</div>}
    <ul className="ontong-leftout-list">{excluded.slice(0,30).map(r=><li key={r.p.id}><a href={r.p.url} target="_blank" rel="noopener noreferrer">{r.p.title} ↗</a><span>{gapText(r,profile).join(' · ')}</span></li>)}</ul>
    {excluded.length>30&&<small>처음 30건만 보여드려요. 조건을 바꾸면 목록이 다시 계산돼요.</small>}
  </details>;
}

export default function OntongPolicies({profile,asOf,known=[],query='',data,remember=false}:{profile:OntongProfile;asOf:string;known?:string[];query?:string;data?:OntongPolicyList;remember?:boolean}){
  const {list,failed}=usePolicyList(data);
  const [shown,setShown]=useState(STEP);
  const [group,setGroup]=useState<PolicyGroup|'ALL'>('ALL');
  const [soon,setSoon]=useState(false);
  const [onlyNew,setOnlyNew]=useState(false);
  const saved=useOntongSaved();
  const ids=useMemo(()=>list?list.policies.map(p=>p.id):null,[list]);
  // Policy numbers are kept only for people who chose to keep their conditions on this device.
  const seen=useSeenPolicies(remember?ids:null,asOf);
  const key=[profile.province,profile.city,profile.age,profile.employment,query].join('|');
  useEffect(()=>setShown(STEP),[key,group,soon,onlyNew]);
  const ranked=useMemo(()=>list?rankPolicies(list.policies,profile,asOf,known,query):[],[list,key,asOf,known]); // eslint-disable-line react-hooks/exhaustive-deps
  const counts=useMemo(()=>{const c=new Map<PolicyGroup,number>();for(const r of ranked)for(const g of policyGroups(r.p))c.set(g,(c.get(g)??0)+1);return c;},[ranked]);
  const visible=ranked.filter(r=>(group==='ALL'||policyGroups(r.p).includes(group))&&(!soon||closesSoon(r.p,asOf))&&(!onlyNew||seen.fresh.has(r.p.id)));
  const newCount=ranked.filter(r=>seen.fresh.has(r.p.id)).length;
  // Closing soon is about dates, so that view goes strictly by deadline.
  const endOf=(r:typeof ranked[number])=>r.p.apply.mode==='PERIOD'?r.p.apply.end:'';
  if(soon)visible.sort((a,b)=>endOf(a).localeCompare(endOf(b))||a.p.title.localeCompare(b.p.title,'ko'));
  if(failed)return null;
  if(!list||!list.policies.length)return null;
  const place=profile.province?`${profile.province}${profile.city&&profile.city!=='__OTHER__'?' '+profile.city:''}`:'전국';
  const filtered=group!=='ALL'||soon||onlyNew;
  return <section className="ontong" aria-labelledby="ontong-title">
    <h3 id="ontong-title">온통청년에 등록된 청년정책 {ranked.length.toLocaleString('ko-KR')}건 더 보기</h3>
    <p className="ontong-lead">온통청년(한국고용정보원)에 등록된 정책을 매일 받아, {place}·나이·취업 상태와 맞지 않는 것만 뺐어요. 위 목록처럼 저희가 공고를 직접 읽고 확인한 사업은 아니에요. 소득·거주기간 같은 자격과 지금 모집 중인지는 온통청년과 공고에서 확인하세요.{profile.province?'':' 지역을 고르면 그 지역 정책도 함께 보여드려요.'}</p>
    <SavedClosing saved={saved.saved} asOf={asOf}/>
    {!remember&&<p className="ontong-new-note ontong-new-hint">‘이 기기에 내 조건 기억하기’를 켜면 다음에 왔을 때 새로 올라온 정책을 따로 알려드려요.</p>}
    {remember&&seen.since&&<p className="ontong-new-note">지난 방문({md(seen.since)}) 이후 새로 올라온 정책이 {newCount>0?<b>{newCount}건</b>:'아직 없어요'}{newCount>0?' 있어요.':'.'}</p>}
    {ranked.length>0&&<div className="ontong-filters">
      <div className="ontong-groups" role="group" aria-label="정책 분야">
        <button type="button" aria-pressed={group==='ALL'} onClick={()=>setGroup('ALL')}>전체 {ranked.length}</button>
        {POLICY_GROUPS.filter(g=>counts.get(g)).map(g=><button type="button" key={g} aria-pressed={group===g} onClick={()=>setGroup(g)}>{g} {counts.get(g)}</button>)}
      </div>
      <div className="ontong-toggles"><label className="ontong-soon"><input type="checkbox" checked={soon} onChange={e=>setSoon(e.target.checked)}/>마감 {SOON_DAYS}일 이내만 보기</label>
      {newCount>0&&<label className="ontong-soon"><input type="checkbox" checked={onlyNew} onChange={e=>setOnlyNew(e.target.checked)}/>새로 올라온 정책만 보기</label>}</div>
      {filtered&&<p role="status" className="ontong-count">{group==='ALL'?'':group+' 분야 '}{onlyNew?'새 정책 ':''}{soon?`마감 ${SOON_DAYS}일 이내 `:''}{visible.length}건</p>}
    </div>}
    {saved.error&&<p role="status">{saved.error}</p>}
    {ranked.length===0?<p className="ontong-empty">입력한 조건과 맞지 않는 정책을 빼고 나니 남은 정책이 없어요. 조건을 바꾸거나 온통청년에서 직접 찾아보세요.</p>:
    visible.length===0?<p className="ontong-empty">고른 분야·마감 조건에 맞는 정책이 없어요. 분야를 ‘전체’로 바꾸거나 마감 조건을 풀어 보세요.</p>:
    <ul className="ontong-list">{visible.slice(0,shown).map(({p,region,age,job})=><li key={p.id} className={closesSoon(p,asOf)?'ontong-soon-item':undefined}>
      <div className="ontong-meta"><span>{categoryText(p)}</span><span>{regionText(p,profile.province)}</span></div>
      <h4>{seen.fresh.has(p.id)&&<span className="ontong-new-badge">새 정책</span>}{p.title}</h4>
      <p className="ontong-org">{p.org}</p>
      {p.summary&&<p>{p.summary}</p>}
      <dl>
        <div><dt>신청</dt><dd>{p.apply.mode==='PERIOD'?(p.apply.start>asOf?`${p.apply.start.slice(5).replace('-','월 ')}일부터 · `:'')+deadlineLabel(p.apply.end,asOf):p.apply.mode==='ALWAYS'?'상시 신청':'공고에서 일정 확인'}</dd></div>
        <div><dt>나이</dt><dd>{ageText(p)}</dd></div>
        <div><dt>취업 상태</dt><dd>{jobText(p)}</dd></div>
        <div><dt>소득</dt><dd>{p.income??'소득 조건 없음'}</dd></div>
        {p.extra&&<div><dt>추가 자격</dt><dd>{p.extra}</dd></div>}
      </dl>
      <p className="ontong-fit">지역 {fitWords[region]} · 나이 {fitWords[age]} · 취업 {fitWords[job]}</p>
      <div className="ontong-links"><Star p={p} on={saved.has(p.id)} onToggle={()=>saved.toggle(p)}/><a href={p.url} target="_blank" rel="noopener noreferrer" aria-label={p.title+' 온통청년에서 보기'}>온통청년에서 보기 ↗</a>{p.apply_url&&<a href={p.apply_url} target="_blank" rel="noopener noreferrer" aria-label={p.title+' 신청·안내 페이지'}>신청·안내 페이지 ↗</a>}</div>
    </li>)}</ul>}
    {visible.length>shown&&<button type="button" className="ontong-more" onClick={()=>setShown(s=>s+STEP)}>정책 {Math.min(STEP,visible.length-shown)}건 더 보기</button>}
    <LeftOut list={list.policies} profile={profile} asOf={asOf} known={known} query={query}/>
    <small className="ontong-source">{list.source.attribution} · <a href={list.source.url} target="_blank" rel="noopener noreferrer">{list.source.title}</a>{list.fetched_on&&<> · {list.fetched_on} 수집</>} · 관심 저장은 정책 제목·마감일·링크만, 새 정책 표시는 이미 본 정책 번호만 이 기기에 보관해요.</small>
  </section>;
}
