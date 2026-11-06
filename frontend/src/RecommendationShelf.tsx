import {useEffect,useId,useRef} from 'react';
import rates from './public-data/product-recommendations.json';
import {renewedRate,renewedRank} from './financial-snapshots';
export type BasicRate={base_rate_percent:string;max_total_rate_percent:string|null;evidence_locator:string;sources:{url:string;title:string;reviewed_on:string;basis_date:string|null}[]};
const data=rates as unknown as {built_on:string;valid_until:string;rate_by_product:Record<string,Record<string,BasicRate>>;order_calendar:Record<string,Record<string,number>>;order_pool:string[][];disclosure:string};
export function verifiedBasicRate(id:string,months:number,asOf:string):BasicRate|null{
 const renewed=renewedRate(id,months,asOf);if(renewed!==undefined)return renewed;
 if(asOf<data.built_on||asOf>data.valid_until)return null;
 return data.rate_by_product[id]?.[String(months)]??null;
}
export function preparedRecommendationRank(id:string,kind:string,months:number,asOf=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())):number{
 const renewed=renewedRank(id,kind,months,asOf);if(renewed!==null)return renewed;
 const pool=data.order_pool[data.order_calendar[kind]?.[String(months)]??-1]??[];
 const i=pool.indexOf(id);return i<0?Number.MAX_SAFE_INTEGER:i;
}

type RankedProduct={id:string;kind:string;code:string};
/** Reuses the Python-prepared order; no browser interest calculation. */
export function comparePreparedRecommendations(a:RankedProduct,b:RankedProduct,months:number,asOf:string){
 const amount=Number(a.code==='PARTIAL')-Number(b.code==='PARTIAL');if(amount)return amount;
 if(a.kind!==b.kind)return a.kind==='SAVINGS'?-1:1;
 const aRate=verifiedBasicRate(a.id,months,asOf),bRate=verifiedBasicRate(b.id,months,asOf);
 return Number(bRate!==null)-Number(aRate!==null)||
  (aRate&&bRate?preparedRecommendationRank(a.id,a.kind,months,asOf)-preparedRecommendationRank(b.id,b.kind,months,asOf):0)||a.id.localeCompare(b.id);
}
type Pick={id:string;name:string;institution:string;kind:string;code:string;rate:BasicRate;payment:string;checks:string[];eligibility:string};
export default function RecommendationShelf({items,months,onView}:{items:Pick[];months:number;onView:(id:string)=>void}){
 const titleId=useId(); const ref=useRef<HTMLElement>(null);
 useEffect(()=>{const node=ref.current;if(!node)return;const reduced=typeof window.matchMedia==="function"&&window.matchMedia("(prefers-reduced-motion: reduce)").matches;if(typeof node.scrollIntoView==="function")node.scrollIntoView({block:"start",behavior:reduced?"auto":"smooth"});node.querySelector<HTMLElement>("h3")?.focus({preventScroll:true});},[]);
 return <section ref={ref} className="recommendation-shelf" aria-labelledby={titleId}>
 <div className="recommendation-heading"><div><span>내 입력에 따른 우선 추천</span><h3 id={titleId} tabIndex={-1}>내 저축 계획에 맞는 추천 상품</h3></div><strong>{months}개월 기준</strong></div>
 <p className="recommendation-method">전액 납입 가능성을 먼저 보고, 같은 종류·기간에서 <b>확인된 기본금리가 높은 순</b>으로 추천합니다. 우대조건을 충족했다고 가정하지 않아요.</p>
 {(['SAVINGS','DEPOSIT'] as const).map(kind=>{
  const picks=items.filter(p=>p.kind===kind).slice(0,3);
  return picks.length?<div className="recommendation-group" key={kind}><h4>{kind==='SAVINGS'?'매달 모으는 적금 추천':'보유 목돈을 맡기는 예금 추천'}</h4><div className="recommendation-grid">{picks.map((p,i)=><article key={p.id} className={'recommendation-card'+(i===0?' is-first':'')} data-recommended-id={p.id}>
   <div className="recommendation-card-top"><strong>{i===0?'우선 추천':'추천'} {String(i+1).padStart(2,'0')}</strong><span>{p.institution}</span></div>
   <h5>{p.name}</h5><p className="recommendation-rate"><small>기본 연</small> {p.rate.base_rate_percent}<small>%</small></p>
   <p className="recommendation-extra">{p.rate.max_total_rate_percent!==null?'우대조건 충족 시 최고 연 '+p.rate.max_total_rate_percent+'%':'우대 적용 금리는 추가 확인'}</p>
   {p.code==='FIT'?<ul className="recommendation-fit"><li>{months}개월 기간 일치 · 입력한 금액 전액으로 비교 가능</li></ul>:<ul><li>{months}개월 기간 조건 일치</li><li>상품 한도 내 일부 금액으로 비교 가능</li><li>입력 예산 전체에 이 금리를 적용하지 않음</li></ul>}
   <p className="recommendation-limit">{p.payment}</p>
   <p className="recommendation-audience"><b>가입 대상</b> {p.eligibility}</p><p className="recommendation-check">가입 대상·우대조건은 추가 확인</p>
   <small className="recommendation-source">금리 확인 {p.rate.sources.map(s=>s.reviewed_on).sort()[0]} · 기준 {p.rate.sources.map(s=>s.basis_date??'페이지 별도 표시 없음').join(' / ')}</small>
   <button type="button" onClick={()=>onView(p.id)}>{p.name} 조건 자세히 보기 <span aria-hidden="true">↗</span></button>
  </article>)}</div></div>:null;
 })}
 {!items.length&&<div className="recommendation-no-rate"><strong>이 입력에서 금리까지 검증된 추천 후보는 아직 없어요.</strong><p>아래에서 금액·기간 후보와 공식 안내를 비교할 수 있습니다. 금리 근거를 확인하지 못한 상품에 임의 순위를 붙이지 않습니다.</p></div>}
 <p className="recommendation-footnote">금리는 세전 연이율이며 상품별 만기이자·실수령액 순위가 아닙니다. 적금과 예금은 각각 비교합니다. 잔여 예산·개인 자격·현재 적용금리는 은행에서 확인하세요.</p>
 </section>;
}
