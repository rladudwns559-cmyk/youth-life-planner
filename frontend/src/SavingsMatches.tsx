import {useEffect,useRef,useState} from 'react';
import type {SimulationResult} from './api';
import {requestSavingsMatches,type MatchingRow,type SavingsMatchesResponse} from './savings-matching-api';

const money=(n:number|null)=>n===null?'미확인':`${n.toLocaleString('ko-KR')}원`;
const rate=(n:string|null)=>n===null?'미확인':`${n}%`;

function ProductMatchCard({row,amount,months}:{row:MatchingRow;amount:number;months:number}) {
  const p=row.product,s=row.source;
  return <article className="savings-match-card" data-product-id={p.product_id}>
    <div className="match-card-heading"><span className={`match-bank bank-${p.bank_id.toLowerCase()}`} aria-hidden="true">{p.bank_id==='KAKAO'?'k':p.bank_id==='KBANK'?'K':'t'}</span>
      <div><p>{p.institution}</p><h4>{p.product_name}</h4></div><span className="match-tag">금액·기간 일치</span></div>
    <div className="match-rates"><div><span>선택 기간 기본금리 · 세전</span><strong>{rate(row.selected_base_rate_percent)}</strong></div>
      <div><span>{row.selected_max_rate_percent!==null&&row.selected_max_rate_percent===row.selected_base_rate_percent?'별도 우대금리 미반영 · 세전':'공개 우대조건 충족 시 · 세전'}</span><b>{rate(row.selected_max_rate_percent)}</b></div></div>
    <p className="match-fit">월 {money(amount)} · {months}개월 조건으로 조회했어요.</p>
    <dl className="match-limits"><div><dt>월 납입 범위</dt><dd>{money(p.minimum_monthly_payment)} ~ {money(p.maximum_monthly_payment)}</dd></div>
      <div><dt>가입 기간</dt><dd>{p.allowed_months?p.allowed_months.join('·'):`${p.min_months}~${p.max_months}`}개월</dd></div></dl>
    <p className="match-eligibility">가입 자격·우대조건은 별도 확인이 필요해요.</p>
    <details><summary>우대조건·가입 대상·확인 근거</summary><ul>{p.preferential_conditions.map((text,i)=><li key={i}>{text}</li>)}</ul>
      <p>{p.eligibility_note}</p><p>{p.term_note}</p><p>{p.rate_note}</p><p>추가 확인: {p.unknown_fields.join(', ')}</p>
      <p>공식 근거: {s.document_name} · {s.evidence_locator}</p>
      {s.document_url&&<a href={s.document_url} target="_blank" rel="noopener noreferrer">은행 공식 공시·설명서 확인 ↗</a>}
    </details>
    <div className="match-card-footer"><p>금리 기준 {s.rate_basis_date??'페이지 기준일 미표시'}<br/>자료 확인 {s.verified_on}</p>
      <a href={s.official_url} target="_blank" rel="noopener noreferrer">공식 상품 보기 <span aria-hidden="true">↗</span></a></div>
  </article>;
}

export default function SavingsMatches({baseline,after,termMonths}:{baseline:SimulationResult;after?:SimulationResult|null;termMonths:number|null}) {
  const [result,setResult]=useState<SavingsMatchesResponse|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false);
  const [mode,setMode]=useState<'current'|'after'>('current'),[retry,setRetry]=useState(0);
  const version=useRef(0);
  useEffect(()=>{
    const sequence=++version.current;setResult(null);setError('');setLoading(false);setMode('current');
    if(termMonths===null)return;
    const controller=new AbortController();setLoading(true);
    const timer=window.setTimeout(()=>controller.abort('timeout'),10000);
    void requestSavingsMatches(baseline.input_summary,termMonths,after?.input_summary??null,controller.signal)
      .then(value=>{if(version.current===sequence&&!controller.signal.aborted)setResult(value);})
      .catch(cause=>{if(version.current!==sequence || (controller.signal.aborted&&controller.signal.reason!=='timeout'))return;
        setError(controller.signal.reason==='timeout'?'적금 조회 시간이 초과됐습니다. 기존 예산과 정책 결과는 그대로입니다.':cause instanceof Error&&!(cause instanceof TypeError)&&!(cause instanceof SyntaxError)?cause.message:'공식 적금 자료를 확인하지 못했습니다. 연결 상태를 확인하고 다시 시도해 주세요.');})
      .finally(()=>{window.clearTimeout(timer);if(version.current===sequence)setLoading(false);});
    return()=>{++version.current;window.clearTimeout(timer);controller.abort();};
  },[baseline,after,termMonths,retry]);
  const selected=mode==='after'&&result?.after?result.after:result?.current;
  const allRows=selected?[...selected.matches,...selected.excluded,...selected.review_required]:[];
  const names=(ids:string[])=>ids.map(id=>allRows.find(r=>r.product.product_id===id)?.product.product_name??id).join(', ');
  return <section className="savings-matches" aria-labelledby="matching-heading" aria-busy={loading}>
    <div className="matching-heading"><div><p className="eyebrow">공식 자료 기반 · 자동 매칭</p><h3 id="matching-heading">내 예산에 맞는 적금</h3></div><span className="matching-auto">자동 조회</span></div>
    <p className="hint">계산한 월 저축 투입 상한 전체와 목표 기간이 맞는 상품을 보여드려요. 가입 자격이나 수익 순위는 판단하지 않아요.</p>
    {termMonths===null&&<div className="matching-empty"><strong>얼마 동안 모으고 싶으세요?</strong><p>현재 상황 입력의 ‘목표 저축 기간’을 정하면 상품이 자동으로 표시돼요.</p><a href="#saving-period">목표 기간 입력하기 →</a></div>}
    {loading&&<p role="status" className="matching-loading">공식 적금의 납입 한도와 기간을 확인하고 있어요…</p>}
    {error&&<div role="alert" className="error-message"><p>{error}</p><button type="button" onClick={()=>setRetry(v=>v+1)}>적금 다시 조회</button></div>}
    {result&&selected&&<div data-testid="savings-matches-result">
      {result.after&&<div className="matching-toggle" aria-label="적금 조회 기준"><button type="button" aria-pressed={mode==='current'} onClick={()=>setMode('current')}>현재 예산 기준</button><button type="button" aria-pressed={mode==='after'} onClick={()=>setMode('after')}>변경 후 예산 기준</button></div>}
      <div className="matching-summary"><p>월 <strong>{money(selected.monthly_amount)}</strong> · <strong>{selected.term_months}개월</strong></p><span>{selected.matched_count}개 조건 일치 / {selected.total_count}개 확인</span></div>
      {result.changes&&mode==='after'&&(result.changes.added.length>0||result.changes.removed.length>0)&&<div className="matching-change">{result.changes.added.length>0&&<p>새로 조건이 맞는 상품: {names(result.changes.added)}</p>}{result.changes.removed.length>0&&<p>변경 후 조건과 맞지 않는 상품: {names(result.changes.removed)}</p>}</div>}
      {selected.matched_count===0&&<div className="matching-empty"><strong>{selected.monthly_amount===0?'현재 저축 투입 상한이 0원이에요.':'현재 금액과 기간이 모두 맞는 상품이 없어요.'}</strong><p>등록된 공식 자료 안에서의 결과입니다. 아래의 미일치·재확인 사유를 살펴보세요.</p></div>}
      <div className="matching-card-list">{selected.matches.map(row=><ProductMatchCard key={row.product.product_id} row={row} amount={selected.monthly_amount} months={selected.term_months}/>)}</div>
      {selected.review_count>0&&<div className="savings-warning"><strong>자료 재확인 필요 {selected.review_count}개</strong><p>확인 시점이 지났거나 필수 정보가 부족한 상품은 자동 매칭에서 제외했어요.</p>{selected.review_required.map(row=><p key={row.product.product_id}>{row.product.product_name}: {row.reasons.join(' ')}</p>)}</div>}
      {selected.excluded_count>0&&<details className="matching-excluded"><summary>금액·기간이 맞지 않는 상품 {selected.excluded_count}개 보기</summary>{selected.excluded.map(row=><div key={row.product.product_id}><strong>{row.product.institution} · {row.product.product_name}</strong><ul>{row.reasons.map((reason,i)=><li key={i}>{reason}</li>)}</ul></div>)}</details>}
      <p className="match-dataset-note">자료 확인 후 {result.review_after_days}일이 지나면 자동 매칭을 보류합니다. 서비스 재검토 기준이며 은행의 금리 보장기간이 아닙니다.</p>
      <p className="match-dataset-note">{result.disclaimer}</p>
    </div>}
  </section>;
}
