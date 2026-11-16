import {useEffect,useMemo,useState} from 'react';
import {rankPolicies,ageText,jobText,regionText,categoryText,policyGroups,closesSoon,POLICY_GROUPS,SOON_DAYS,type OntongPolicy,type OntongPolicyList,type OntongProfile,type Fit,type PolicyGroup} from './ontong-policies';
import {useOntongSaved} from './ontong-saved';
import {deadlineLabel} from './SupportPlanner';
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

export default function OntongPolicies({profile,asOf,known=[],query='',data}:{profile:OntongProfile;asOf:string;known?:string[];query?:string;data?:OntongPolicyList}){
  const {list,failed}=usePolicyList(data);
  const [shown,setShown]=useState(STEP);
  const [group,setGroup]=useState<PolicyGroup|'ALL'>('ALL');
  const [soon,setSoon]=useState(false);
  const saved=useOntongSaved();
  const key=[profile.province,profile.city,profile.age,profile.employment,query].join('|');
  useEffect(()=>setShown(STEP),[key,group,soon]);
  const ranked=useMemo(()=>list?rankPolicies(list.policies,profile,asOf,known,query):[],[list,key,asOf,known]); // eslint-disable-line react-hooks/exhaustive-deps
  const counts=useMemo(()=>{const c=new Map<PolicyGroup,number>();for(const r of ranked)for(const g of policyGroups(r.p))c.set(g,(c.get(g)??0)+1);return c;},[ranked]);
  const visible=ranked.filter(r=>(group==='ALL'||policyGroups(r.p).includes(group))&&(!soon||closesSoon(r.p,asOf)));
  // Closing soon is about dates, so that view goes strictly by deadline.
  const endOf=(r:typeof ranked[number])=>r.p.apply.mode==='PERIOD'?r.p.apply.end:'';
  if(soon)visible.sort((a,b)=>endOf(a).localeCompare(endOf(b))||a.p.title.localeCompare(b.p.title,'ko'));
  if(failed)return null;
  if(!list||!list.policies.length)return null;
  const place=profile.province?`${profile.province}${profile.city&&profile.city!=='__OTHER__'?' '+profile.city:''}`:'전국';
  const filtered=group!=='ALL'||soon;
  return <section className="ontong" aria-labelledby="ontong-title">
    <h3 id="ontong-title">온통청년에 등록된 청년정책 {ranked.length.toLocaleString('ko-KR')}건 더 보기</h3>
    <p className="ontong-lead">온통청년(한국고용정보원)에 등록된 정책을 매일 받아, {place}·나이·취업 상태와 맞지 않는 것만 뺐어요. 위 목록처럼 저희가 공고를 직접 읽고 확인한 사업은 아니에요. 소득·거주기간 같은 자격과 지금 모집 중인지는 온통청년과 공고에서 확인하세요.{profile.province?'':' 지역을 고르면 그 지역 정책도 함께 보여드려요.'}</p>
    {ranked.length>0&&<div className="ontong-filters">
      <div className="ontong-groups" role="group" aria-label="정책 분야">
        <button type="button" aria-pressed={group==='ALL'} onClick={()=>setGroup('ALL')}>전체 {ranked.length}</button>
        {POLICY_GROUPS.filter(g=>counts.get(g)).map(g=><button type="button" key={g} aria-pressed={group===g} onClick={()=>setGroup(g)}>{g} {counts.get(g)}</button>)}
      </div>
      <label className="ontong-soon"><input type="checkbox" checked={soon} onChange={e=>setSoon(e.target.checked)}/>마감 {SOON_DAYS}일 이내만 보기</label>
      {filtered&&<p role="status" className="ontong-count">{group==='ALL'?'':group+' 분야 '}{soon?`마감 ${SOON_DAYS}일 이내 `:''}{visible.length}건</p>}
    </div>}
    {saved.error&&<p role="status">{saved.error}</p>}
    {ranked.length===0?<p className="ontong-empty">입력한 조건과 맞지 않는 정책을 빼고 나니 남은 정책이 없어요. 조건을 바꾸거나 온통청년에서 직접 찾아보세요.</p>:
    visible.length===0?<p className="ontong-empty">고른 분야·마감 조건에 맞는 정책이 없어요. 분야를 ‘전체’로 바꾸거나 마감 조건을 풀어 보세요.</p>:
    <ul className="ontong-list">{visible.slice(0,shown).map(({p,region,age,job})=><li key={p.id} className={closesSoon(p,asOf)?'ontong-soon-item':undefined}>
      <div className="ontong-meta"><span>{categoryText(p)}</span><span>{regionText(p,profile.province)}</span></div>
      <h4>{p.title}</h4>
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
    <small className="ontong-source">{list.source.attribution} · <a href={list.source.url} target="_blank" rel="noopener noreferrer">{list.source.title}</a>{list.fetched_on&&<> · {list.fetched_on} 수집</>} · 관심 저장은 정책 제목·마감일·링크만 이 기기에 보관해요.</small>
  </section>;
}
