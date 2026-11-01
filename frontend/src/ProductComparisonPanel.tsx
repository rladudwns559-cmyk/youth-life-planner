import GroupedInput from './GroupedInput';
import {useEffect,useRef,useState} from 'react';
import type {SimulationResult} from './api';
import {compareProducts,getProducts,ProductApiError,type OfficialProduct,type OfficialSource,type ProductCatalog,type ProductComparison} from './products-api';
const money=(value:number|null)=>value===null?'미확인':`${value.toLocaleString('ko-KR')}원`;
const rate=(value:string|null)=>value===null?'미확인':`${value}%`;

function Sources({product,sources}:{product:OfficialProduct;sources:OfficialSource[]}){
  const source=sources.find(s=>s.source_id===product.source_id);
  return <div className="product-sources"><p>기준일 {product.basis_date} · 확인일 {product.verified_on} · 버전 {product.snapshot_version}</p>
    {source&&<p><a href={source.official_url} target="_blank" rel="noopener noreferrer">공식 자료 · {source.title}</a><br/>{product.evidence_locator}<br/><a href={source.license_url} target="_blank" rel="noopener noreferrer">이용 조건: {source.license_label}</a></p>}
    {product.product_detail_url?<a href={product.product_detail_url} target="_blank" rel="noopener noreferrer">은행 공식 상품 상세</a>:<p>개별 상품 상세 링크 미확인 · 위 링크는 공식 데이터셋입니다.</p>}</div>;
}

export default function ProductComparisonPanel({baseline,after}:{baseline:SimulationResult;after?:SimulationResult|null}){
  const [catalog,setCatalog]=useState<ProductCatalog|null>(null);const [catalogError,setCatalogError]=useState('');const [catalogLoading,setCatalogLoading]=useState(false);
  const [selected,setSelected]=useState<string[]>([]);const [payment,setPayment]=useState('200000');const [months,setMonths]=useState('12');
  const [result,setResult]=useState<ProductComparison|null>(null);const [error,setError]=useState('');const [loading,setLoading]=useState(false);
  const active=useRef<AbortController|null>(null);const listRequest=useRef<AbortController|null>(null);
  function invalidate(){active.current?.abort();setLoading(false);setResult(null);setError('');}
  useEffect(()=>{invalidate();},[after]);
  useEffect(()=>()=>{active.current?.abort();listRequest.current?.abort();},[]);
  async function load(){
    listRequest.current?.abort();const request=new AbortController();listRequest.current=request;setCatalogLoading(true);setCatalogError('');
    const timer=window.setTimeout(()=>request.abort('timeout'),10000);
    try{const response=await getProducts(request.signal);if(!request.signal.aborted){setCatalog(response);setSelected(response.products.map(p=>p.product_id));}}
    catch(cause){if(!request.signal.aborted||request.signal.reason==='timeout')setCatalogError(request.signal.reason==='timeout'?'상품 목록 응답 시간이 초과되었습니다. 다시 시도해 주세요.':cause instanceof ProductApiError?cause.message:'상품 자료 서버에 연결하지 못했습니다. 다시 시도해 주세요.');}
    finally{window.clearTimeout(timer);if(listRequest.current===request)setCatalogLoading(false);}
  }
  async function submit(event:React.FormEvent){
    event.preventDefault();invalidate();
    if(!payment.trim()||!months.trim()){setError('비교 월 납입액과 기간을 모두 입력해 주세요. 빈칸은 0이 아닙니다.');return;}
    if(!/^\d+$/.test(payment)||Number(payment)>1e12||!/^\d+$/.test(months)||Number(months)<1||Number(months)>120){setError('월 납입액은 0~1조 원 정수, 기간은 1~120개월 정수로 입력해 주세요.');return;}
    if(!selected.length){setError('비교할 상품을 하나 이상 선택해 주세요.');return;}
    const request=new AbortController();active.current=request;setLoading(true);const timer=window.setTimeout(()=>request.abort('timeout'),10000);
    try{const response=await compareProducts({profile:baseline.input_summary,...(after?{after_profile:after.input_summary}:{}),monthly_payment:Number(payment),term_months:Number(months),product_ids:selected},request.signal);if(!request.signal.aborted)setResult(response);}
    catch(cause){if(!request.signal.aborted||request.signal.reason==='timeout')setError(request.signal.reason==='timeout'?'상품 비교 응답 시간이 초과되었습니다. 다시 시도해 주세요.':cause instanceof ProductApiError?cause.message:'상품 비교 서버에 연결하지 못했습니다. 다시 시도해 주세요.');}
    finally{window.clearTimeout(timer);if(active.current===request)setLoading(false);}
  }
  return <section className="products-panel panel" aria-labelledby="products-heading">
    <div className="section-heading"><span className="step">05</span><div><h2 id="products-heading">공식 상품 조건 비교하기</h2><p>공식 자료의 기준일·조건과 현재 월 예산을 함께 확인합니다.</p></div></div>
    <p className="hint">기준일이 지난 상품 자료는 최신 금리가 아닙니다. 가입 자격은 별도로 확인해야 합니다.</p>
    {!catalog&&<button type="button" className="secondary-button" disabled={catalogLoading} onClick={load}>{catalogLoading?'공식 상품 목록 불러오는 중…':'공식 상품 목록 불러오기'}</button>}
    {catalogLoading&&<p role="status">공식 스냅샷을 불러오고 있어요.</p>}{catalogError&&<p role="alert" className="error-message">{catalogError}</p>}
    {catalog&&<>
      <p className="product-summary">공식 정보 {catalog.information_count}개 · 계산 가정 대응 {catalog.compatible_count}개</p>
      <p className="hint">{catalog.review_after_days}일 초과 자료는 ‘자료가 오래됨’으로 표시합니다. {catalog.review_policy}</p>
      <form onSubmit={submit} noValidate><div className="product-list">{catalog.products.map(product=><article className="official-product" key={product.product_id}>
        <p className="eyebrow">{product.institution} · 실제 상품의 과거 스냅샷</p><h3><label><input type="checkbox" checked={selected.includes(product.product_id)} onChange={e=>{invalidate();setSelected(old=>e.target.checked?[...old,product.product_id]:old.filter(id=>id!==product.product_id));}}/> {product.product_name}</label></h3>
        <div className="product-flags"><span>{product.calculation_status==='INFORMATION_ONLY'?'상품 정보만 표시':'계산 가정 대응'}</span>{product.freshness==='STALE'&&<span>자료가 오래됨</span>}<span>{product.subscription_status==='UNCONFIRMED'?'현재 가입 상태 미확인':product.subscription_status==='CLOSED_AS_OF_SOURCE'?'자료 기준 판매 종료':'자료 기준 판매중 · 현재 재확인 필요'}</span></div>
        <p>{product.term_description}</p><p className="hint">납입 범위 {money(product.minimum_monthly_payment)} ~ {money(product.maximum_monthly_payment)} / 월 · 단위 {money(product.payment_step)}</p>
        <div className="product-rates">{product.rate_options.map((band,i)=><div key={i}><strong>{band.min_months===band.max_months?band.min_months:`${band.min_months}~${band.max_months}`}개월 금리 구간</strong><span>기본 연 {rate(band.base_rate_percent)}</span><span>우대 포함 최고 연 {rate(band.max_total_rate_percent)}</span></div>)}</div>
        <p className="hint">최대 우대 가산 {product.max_preferential_bonus_percentage_points===null?'미확인':`${product.max_preferential_bonus_percentage_points}%p`} · 우대조건 충족을 가정하지 않습니다.</p>
        <details><summary>가입 대상·우대조건·확인하지 못한 정보</summary><p>자료의 가입 대상: {product.target}</p><ul>{product.preferential_conditions.map((text,i)=><li key={i}>{text}</li>)}</ul><p>미확인: {product.unknown_fields.join(', ')}</p><ul>{product.cross_check_notes.map((text,i)=><li key={i}>{text}</li>)}</ul></details>
        <Sources product={product} sources={catalog.sources}/>
      </article>)}</div>
      <div className="product-inputs"><div className="field"><label htmlFor="product-payment">상품 비교 월 납입액</label><div className="input-unit"><GroupedInput id="product-payment" inputMode="numeric" value={payment} onChange={e=>{invalidate();setPayment(e.target.value);}} autoComplete="off"/><span>원</span></div></div><div className="field"><label htmlFor="product-months">상품 비교 기간</label><div className="input-unit"><GroupedInput id="product-months" inputMode="numeric" value={months} onChange={e=>{invalidate();setMonths(e.target.value);}} autoComplete="off"/><span>개월</span></div></div></div>
      <p className="hint">현재 저축 투입 상한 {money(baseline.cashflow.savable_amount)}{after?` · What-if 변경 후 ${money(after.cashflow.savable_amount)}`:' · What-if 비교를 완료하면 변경 후 상한도 연결됩니다.'}</p>
      {error&&<p role="alert" className="error-message">{error}</p>}
      <button type="submit" className="submit" disabled={loading}>{loading?'공식 상품 비교 중…':'선택한 상품 조건 비교하기'}</button>{loading&&<p role="status">조건과 월 예산을 비교하고 있어요.</p>}
      </form>
      {result&&<div data-testid="product-comparison-result" className="product-result" aria-live="polite">
        <h3>입력 조건 비교 결과</h3><p>월 {money(result.monthly_payment)} · {result.term_months}개월 · 정보 {result.information_count}개 / 실제 계산 {result.calculated_count}개</p>
        <div className={result.budget.exceeds_budget_cap||result.budget.has_deficit?'savings-warning':'savings-budget'}><strong>현재 월 예산</strong><p>{result.budget.message}</p></div>
        {result.after_budget&&<div className={result.after_budget.exceeds_budget_cap||result.after_budget.has_deficit?'savings-warning':'savings-budget'}><strong>What-if 변경 후 월 예산</strong><p>저축 투입 상한 {money(result.after_budget.savable_amount_krw)}. {result.after_budget.message}</p></div>}
        {!result.direct_maturity_comparison_supported&&<p className="savings-warning">같은 조건으로 만기금액을 비교할 수 있는 상품이 부족합니다. 금리·만기금액 순위를 만들지 않습니다.</p>}
        {result.results.map(item=><article className="official-product" key={item.product_id}><h3>{item.product.product_name}</h3><p>선택 기간 기본 연 {rate(item.selected_base_rate_percent)} · 우대 포함 최고 연 {rate(item.selected_max_total_rate_percent)} (자동 적용 없음)</p>
          {item.calculation?<dl className="savings-amounts"><div><dt>총 납입원금</dt><dd>{money(item.calculation.total_principal_krw)}</dd></div><div><dt>예상 세전이자</dt><dd>{money(item.calculation.estimated_interest_before_tax_krw)}</dd></div><div><dt>예상 세전 만기금액</dt><dd>{money(item.calculation.estimated_maturity_before_tax_krw)}</dd></div></dl>:<><strong>현재 계산 방식 미지원 또는 추가 확인 필요</strong><p>총 납입원금·세전이자·만기금액: 계산하지 않음</p><ul>{item.reasons.map((reason,i)=><li key={i}>{reason}</li>)}</ul></>}
          <Sources product={item.product} sources={result.sources}/>
        </article>)}
        <p className="hint">계산 지원 시에만 매월 초 동일 납입·고정 단리·세전·기본금리를 적용합니다. 우대조건 충족·가입 자격은 확인하지 않습니다.</p><p className="hint">{result.comparison_note} {result.disclaimer}</p>
      </div>}
    </>}
  </section>;
}
