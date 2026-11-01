import GroupedInput from './GroupedInput';
import {publicBackendPending} from './portal-routing';
import {useEffect,useRef,useState} from 'react';
import type {SimulationResult} from './api';
import {getAssetPrograms,type AssetFacts,type AssetResponse,type AssetRow} from './asset-programs-api';
import './asset-programs.css';

const money=(n:number)=>`${n.toLocaleString('ko-KR')}원`;
const emptyFacts:AssetFacts={province:null,birth_date:null,owns_home:null};
const provinces=['서울','부산','대구','인천','광주','대전','울산','세종','경기','강원','충북','충남','전북','전남','경북','경남','제주'];
const bucketNames={CATALOG:'공식 사업 안내',CURRENT_CANDIDATE:'현재 검토 후보',WATCHLIST:'다음 모집 확인용',BUDGET_SHORTFALL:'납입 여력 확인',NOT_MATCHED:'기초조건 불일치'};
const statusNames={PASS:'충족',FAIL:'미충족',UNKNOWN:'확인 필요'};
function contribution(p:AssetRow['program']){
  if(p.monthly_minimum===null&&p.monthly_maximum===null)return '새 모집 공고 확인';
  if(p.monthly_minimum===null)return `월 최대 ${money(p.monthly_maximum!)} · 최소금액 확인 필요`;
  if(p.monthly_maximum===p.monthly_minimum)return `월 ${money(p.monthly_minimum)}`;
  return `월 ${money(p.monthly_minimum)}${p.monthly_maximum===null?' 이상':` ~ ${money(p.monthly_maximum)}`}`;
}
function dateRange(row:AssetRow){
  const w=row.intake.application;
  if(!w)return row.intake.note;
  // The end is exclusive in the API; show only its explicitly provided official note for precision.
  const start=new Date(w.starts_at).toLocaleDateString('ko-KR',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'});
  const end=new Date(new Date(w.ends_at_exclusive).getTime()-1).toLocaleDateString('ko-KR',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'});
  return `${start} ~ ${end}`;
}
function AssetCard({row}:{row:AssetRow}){
  const p=row.program,a=row.assessment;
  return <article className="asset-card" data-asset-id={p.program_id}>
    <div className="asset-card-top"><span className={`asset-intake intake-${row.intake.status.toLowerCase()}`}>{row.intake.label}</span><span>{p.regions.length?p.regions.join(' · '):'전국'} · {p.edition}</span></div>
    <p className="asset-authority">{p.authority}</p><h3>{p.title}</h3>
    <p className="asset-benefit">{p.benefit_summary}</p>
    <dl className="asset-facts"><div><dt>본인 저축</dt><dd>{contribution(p)}</dd></div><div><dt>저축 기간</dt><dd>{p.term_months.length?p.term_months.map(m=>`${m}개월`).join(' / '):'공식 가입·유지조건 확인'}</dd></div><div><dt>{row.intake.status==='CLOSED'?'확인한 신청 기간':'신청 안내'}</dt><dd>{dateRange(row)}</dd></div></dl>
    {row.intake.phase&&<p className="asset-phase">현재 단계: {row.intake.phase} · 신규 신청 기간과 구분해 주세요.</p>}
    {!row.intake.fresh&&<p className="asset-review-note">마지막 확인 이후 시간이 지나 새 공고 재확인이 필요해요.</p>}
    {a&&<div className={`asset-recommendation rec-${row.bucket.toLowerCase()}`}><strong>{bucketNames[row.bucket]}</strong><span>{a.display_status}</span>
      {row.reasons.map((reason,i)=><p key={i}>{reason}</p>)}
      {a.budget.status==='FAIL'&&<p>현재 저축 여력으로 최소 납입액을 채우기 어려워요. 자격 판정과는 별개예요.</p>}
      {a.allocation_krw!==null&&<p>납입 검토 금액 월 {money(a.allocation_krw)}{a.unallocated_capacity_krw!==null&&a.unallocated_capacity_krw>0?` · 남는 저축 여력 ${money(a.unallocated_capacity_krw)}`:''}</p>}
      {a.goal_matches===false&&<p>입력한 목표 기간과 사업의 저축 기간이 달라요.</p>}
    </div>}
    <details className="asset-details"><summary>조건·추천 근거·추가 확인사항</summary>
      <p>{p.age_note}</p><p>{p.income_note}</p><p>{p.contribution_note}</p><p>{row.intake.note}</p>{row.intake.application&&<p>{row.intake.application.time_note}</p>}
      {a&&<><ul className="asset-checks">{[...a.checks,a.budget].map(c=><li key={c.key}><strong>{c.label} · {statusNames[c.status]}</strong><p>{c.note}</p></li>)}</ul><h4>아직 확인해야 할 공식 조건</h4><ul>{a.remaining_checks.map(c=><li key={c.key}>{c.note}</li>)}</ul></>}
      <p className="hint">일부 조건의 기초 검토이며, 모든 가입조건을 확인한 결과는 아닙니다. 지원금은 예산에 더하지 않습니다.</p>
      {row.sources.map(s=><div className="asset-source" key={s.source_id}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.title} ↗</a><p>{s.locator}</p><small>자료 기준 {s.published_on??'게시일 미표시'} · 확인 {s.verified_on}</small></div>)}
    </details>
    <div className="asset-card-bottom"><span>공식 자료 확인 {row.sources.map(s=>s.verified_on).sort()[0]}</span><a href={row.sources[0].url} target="_blank" rel="noopener noreferrer" aria-label={`${p.title} 공식 공고 보기`}>공식 공고 보기 ↗</a></div>
  </article>;
}

export default function AssetPrograms({baseline,after,goalMonths}:{baseline?:SimulationResult|null;after?:SimulationResult|null;goalMonths:number|null}){
  const [data,setData]=useState<AssetResponse|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const [facts,setFacts]=useState<AssetFacts>({...emptyFacts}),[draft,setDraft]=useState<AssetFacts>({...emptyFacts}),[extraError,setExtraError]=useState('');
  const [filter,setFilter]=useState('all'),[query,setQuery]=useState(''),[expanded,setExpanded]=useState(false),[retry,setRetry]=useState(0),[mode,setMode]=useState<'current'|'after'>('current');
  const version=useRef(0);
  useEffect(()=>{const update=()=>setRetry(n=>n+1);window.addEventListener('asset-official-updated',update);return()=>window.removeEventListener('asset-official-updated',update);},[]);
  useEffect(()=>{setFilter(baseline?'relevant':'all');setExpanded(false);},[baseline]);
  useEffect(()=>{
    const sequence=++version.current,controller=new AbortController();setData(null);setError('');setLoading(true);setMode('current');
    const timer=window.setTimeout(()=>controller.abort('timeout'),10000);
    void getAssetPrograms(baseline?.input_summary??null,after?.input_summary??null,facts,goalMonths,controller.signal)
      .then(value=>{if(version.current===sequence&&!controller.signal.aborted)setData(value);})
      .catch(cause=>{if(version.current!==sequence||(controller.signal.aborted&&controller.signal.reason!=='timeout'))return;
        setError(controller.signal.reason==='timeout'?'지원사업 조회 시간이 초과됐습니다. 기존 계산 결과는 그대로입니다.':cause instanceof Error&&!(cause instanceof TypeError)&&!(cause instanceof SyntaxError)?cause.message:'지원사업 자료에 연결하지 못했습니다. 다시 시도해 주세요.');})
      .finally(()=>{window.clearTimeout(timer);if(version.current===sequence)setLoading(false);});
    return()=>{++version.current;window.clearTimeout(timer);controller.abort();};
  },[baseline,after,facts,goalMonths,retry]);
  const selected=mode==='after'&&data?.after?data.after:data;
  const rows=(selected?.programs??[]).filter(row=>{
    const text=[row.program.title,row.program.authority,...row.program.regions,row.program.regions.length?'':'전국'].join(' ').toLowerCase();
    if(!text.includes(query.trim().toLowerCase()))return false;
    if(filter==='relevant')return !['NOT_MATCHED','BUDGET_SHORTFALL'].includes(row.bucket);
    if(filter==='open')return row.intake.status==='OPEN';
    if(filter==='closed')return row.intake.status==='CLOSED';
    if(filter==='review')return ['UNKNOWN','REVIEW_REQUIRED','NO_INTAKE','UPCOMING'].includes(row.intake.status);
    return true;
  });
  const applyFacts=(event:React.FormEvent)=>{
    event.preventDefault();setExtraError('');
    if(draft.birth_date&&(!/^\d{4}-\d{2}-\d{2}$/.test(draft.birth_date)||Number.isNaN(Date.parse(draft.birth_date)))){setExtraError('생년월일을 올바른 날짜로 입력해 주세요.');return;}
    setFacts({...draft});
  };
  return <section className={`asset-programs ${baseline?'asset-personalized':''}`} id="asset-programs" aria-labelledby="asset-heading" aria-busy={loading}>
    <div className="asset-section-heading"><div><p className="eyebrow">정부·지자체 공식 지원정보</p><h2 id="asset-heading">청년의 목돈 마련, 함께 지원받아요.</h2><p>{baseline?'입력한 상황과 납입 여력을 바탕으로 검토할 사업을 모았어요.':'전국 정책형 저축부터 지역 청년통장까지, 모집 현황을 먼저 살펴보세요.'}</p></div>{!publicBackendPending&&<a className="asset-start-link" href="#input-heading">{baseline?'내 상황 수정하기':'내 조건으로 찾아보기'} →</a>}</div>
    <p className="asset-catalog-notice">확인일 기준 공식 자료예요. 모집 현황과 개인 자격은 다르며, 마감·미운영 사업도 다음 모집 확인용으로 구분해 보여드려요.</p>
    {baseline&&<details className="asset-additional"><summary>추천 정확도를 높일 추가 정보 · 선택</summary><form onSubmit={applyFacts} noValidate><div className="asset-extra-grid"><div><label htmlFor="asset-province">추천용 거주 광역지역</label><select id="asset-province" value={draft.province??''} onChange={e=>setDraft({...draft,province:e.target.value||null})}><option value="">현재 지역 입력에서 확인</option>{provinces.map(p=><option key={p} value={p}>{p}</option>)}</select></div><div><label htmlFor="asset-birth">생년월일</label><input id="asset-birth" type="date" value={draft.birth_date??''} onChange={e=>setDraft({...draft,birth_date:e.target.value||null})}/></div><div><label htmlFor="asset-home">본인 명의 주택 소유</label><select id="asset-home" value={draft.owns_home===null?'':String(draft.owns_home)} onChange={e=>setDraft({...draft,owns_home:e.target.value===''?null:e.target.value==='true'})}><option value="">모름 / 미입력</option><option value="false">소유하지 않음</option><option value="true">소유함</option></select></div></div><p>공고마다 연령 기준일이 달라 생년월일이 필요할 수 있어요. 주민등록번호·계좌정보는 받지 않으며, 입력은 저장하지 않아요.</p>{extraError&&<p role="alert">{extraError}</p>}<button type="submit">추가 정보로 추천 갱신</button></form></details>}
    {loading&&<p role="status" className="asset-loading">공식 사업과 모집 일정을 확인하고 있어요…</p>}
    {error&&<div role="alert" className="error-message"><p>{error}</p><button type="button" onClick={()=>setRetry(n=>n+1)}>지원사업 다시 조회</button></div>}
    {selected&&<div data-testid="asset-programs-result">
      <div className="asset-stats"><div><strong>{selected.program_count}</strong><span>등록 사업</span></div><div><strong>{selected.counts.OPEN}</strong><span>확인일의 모집 안내</span></div><div><strong>{selected.counts.CLOSED}</strong><span>신청 마감</span></div><div><strong>{selected.counts.NO_INTAKE+selected.counts.UNKNOWN+selected.counts.REVIEW_REQUIRED+selected.counts.UPCOMING}</strong><span>미운영·예정·재확인</span></div></div>
      {data?.after&&<div className="matching-toggle" aria-label="지원사업 추천 기준"><button type="button" aria-pressed={mode==='current'} onClick={()=>setMode('current')}>지원사업 현재 기준</button><button type="button" aria-pressed={mode==='after'} onClick={()=>setMode('after')}>지원사업 변경 후 기준</button></div>}
      {selected.personalized&&<p className="asset-personal-context">{selected.province??'지역 추가 확인'} · 월 저축 여력 {money(selected.monthly_capacity??0)} · 현재 검토 후보 {selected.recommendation_counts.CURRENT_CANDIDATE}개 / 다음 모집 확인용 {selected.recommendation_counts.WATCHLIST}개</p>}
      {selected.input_notes.map((note,i)=><p className="asset-review-note" key={i}>{note}</p>)}
      <div className="asset-tools"><div className="asset-filter" aria-label="지원사업 목록 필터">{[...(selected.personalized?[['relevant','내 조건으로 보기']]:[]),['all','전체'],['open','모집 중'],['closed','마감'],['review','예정·확인 필요']].map(([key,label])=><button type="button" key={key} aria-pressed={filter===key} onClick={()=>{setFilter(key);setExpanded(false);}}>{label}</button>)}</div><label className="asset-search"><span className="sr-only">지원사업 검색</span><GroupedInput type="search" placeholder="사업명·지역 검색" mode="search" value={query} onChange={e=>{setQuery(e.target.value);setExpanded(false);}}/></label></div>
      <div className="asset-list-meta"><p>{rows.length}개 사업 표시{!expanded&&rows.length>3?' · 먼저 3개를 보여드려요.':''}</p><button type="button" onClick={()=>setRetry(n=>n+1)}>목록 다시 불러오기</button></div>
      {rows.length===0&&<div className="matching-empty"><strong>이 조건에서 표시할 사업이 없어요.</strong><p>‘전체’에서 다른 지역·마감 사업과 납입조건도 확인할 수 있어요. 새로운 모집은 공식 공고 확인 후 추가됩니다.</p></div>}
      <div className="asset-card-list">{(expanded?rows:rows.slice(0,3)).map(row=><AssetCard key={row.program.program_id} row={row}/>)}</div>
      {rows.length>3&&<button type="button" className="asset-show-more" onClick={()=>setExpanded(v=>!v)}>{expanded?'처음 3개만 보기':`나머지 ${rows.length-3}개 사업 더 보기`}</button>}
      <p className="asset-disclaimer">{selected.disclaimer}</p>
      <details className="asset-update-note"><summary>자료 갱신과 모집 알림 안내</summary><p>공개 정보는 표시된 검토일 기준 자료입니다. 목록 다시 불러오기는 새 모집을 실시간 수집하는 동작이 아닙니다. 공식 공고에서 최신 모집 여부와 적용 조건을 확인해 주세요.</p><p>현재 공개 서비스에서는 자동 갱신·브라우저 알림·이메일 구독을 제공하지 않습니다. 유료 요금제는 신청하지 않았습니다. 기존 로컬 수집·알림 코드는 별도 검증 자료로 보존했습니다.</p></details>
    </div>}
  </section>;
}
