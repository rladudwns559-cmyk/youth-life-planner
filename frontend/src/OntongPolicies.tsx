import {useEffect,useMemo,useState} from 'react';
import {rankPolicies,ageText,jobText,regionText,type OntongPolicyList,type OntongProfile,type Fit} from './ontong-policies';
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

export default function OntongPolicies({profile,asOf,known=[],query='',data}:{profile:OntongProfile;asOf:string;known?:string[];query?:string;data?:OntongPolicyList}){
  const {list,failed}=usePolicyList(data);
  const [shown,setShown]=useState(STEP);
  const key=[profile.province,profile.city,profile.age,profile.employment,query].join('|');
  useEffect(()=>setShown(STEP),[key]);
  const ranked=useMemo(()=>list?rankPolicies(list.policies,profile,asOf,known,query):[],[list,key,asOf,known]); // eslint-disable-line react-hooks/exhaustive-deps
  if(failed)return null;
  if(!list||!list.policies.length)return null;
  const place=profile.province?`${profile.province}${profile.city&&profile.city!=='__OTHER__'?' '+profile.city:''}`:'전국';
  return <section className="ontong" aria-labelledby="ontong-title">
    <h3 id="ontong-title">온통청년에 등록된 청년정책 {ranked.length.toLocaleString('ko-KR')}건 더 보기</h3>
    <p className="ontong-lead">온통청년(한국고용정보원)에 등록된 정책을 매일 받아, {place}·나이·취업 상태와 맞지 않는 것만 뺐어요. 위 목록처럼 저희가 공고를 직접 읽고 확인한 사업은 아니에요. 소득·거주기간 같은 자격과 지금 모집 중인지는 온통청년과 공고에서 확인하세요.{profile.province?'':' 지역을 고르면 그 지역 정책도 함께 보여드려요.'}</p>
    {ranked.length===0?<p className="ontong-empty">입력한 조건과 맞지 않는 정책을 빼고 나니 남은 정책이 없어요. 조건을 바꾸거나 온통청년에서 직접 찾아보세요.</p>:
    <ul className="ontong-list">{ranked.slice(0,shown).map(({p,region,age,job})=><li key={p.id}>
      <div className="ontong-meta"><span>{p.category}{p.subcategory&&' · '+p.subcategory}</span><span>{regionText(p,profile.province)}</span></div>
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
      <div className="ontong-links"><a href={p.url} target="_blank" rel="noopener noreferrer" aria-label={p.title+' 온통청년에서 보기'}>온통청년에서 보기 ↗</a>{p.apply_url&&<a href={p.apply_url} target="_blank" rel="noopener noreferrer" aria-label={p.title+' 신청·안내 페이지'}>신청·안내 페이지 ↗</a>}</div>
    </li>)}</ul>}
    {ranked.length>shown&&<button type="button" className="ontong-more" onClick={()=>setShown(s=>s+STEP)}>정책 {Math.min(STEP,ranked.length-shown)}건 더 보기</button>}
    <small className="ontong-source">{list.source.attribution} · <a href={list.source.url} target="_blank" rel="noopener noreferrer">{list.source.title}</a>{list.fetched_on&&<> · {list.fetched_on} 수집</>}</small>
  </section>;
}
