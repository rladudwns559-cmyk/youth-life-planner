import GroupedInput from './GroupedInput';
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {readPreparedDecision} from './ProductExplorer';
import './finder-dialog.css';
import LocalNotice, {type LocalCounts} from './LocalNotice';
import {useKoreaDay,downloadCalendar} from './SupportPlanner';
import {comparePreparedRecommendations,verifiedBasicRate} from './RecommendationShelf';
import DataFreshness from './DataFreshness';
import {financialProducts} from './financial-snapshots';

type View = 'programs' | 'products' | 'compare';
export type FinderItem = {
  id:string; title:string; location:string; benefit:string; status:string;
  match:string; checks:string[]; reasons:string[]; url:string; recommendationLabel?:string;
  deadline?:{label:string; file:string; text:()=>string|null};
};
export type ExcludedItem={id:string; title:string; location:string; url:string; gaps:{key:string;label:string;text:string}[]};
function DeadlineButton({title,deadline}:{title:string;deadline:NonNullable<FinderItem['deadline']>}){
  const [message,setMessage]=useState('');
  return <div className="deadline-action"><span>{deadline.label}</span><button type="button" aria-label={title+' 마감일 캘린더에 추가'} onClick={()=>{const text=deadline.text();if(text)setMessage(downloadCalendar(text,deadline.file));}}>캘린더에 추가</button>{message&&<small role="status">{message}</small>}</div>;
}
function ExcludedList({items}:{items:ExcludedItem[]}){
  if(!items.length)return null;
  return <details className="finder-excluded"><summary>조건이 달라 뺀 사업 {items.length}개 · 무엇이 다른지 보기</summary>
    <p>나이·취업 상태·월세 거주 중 하나 이상이 공고 기준과 달라 결과에서 뺀 사업이에요. 어떤 조건이 얼마나 다른지 보고, 조건이 바뀌거나 다음 모집 때 다시 확인하세요.</p>
    <ul>{items.map(item=><li key={item.id}><div><strong>{item.title}</strong><small>{item.location}</small></div><ul>{item.gaps.map(g=><li key={g.key}><b>{g.label}</b> {g.text}</li>)}</ul><a href={item.url} target="_blank" rel="noopener noreferrer">공식 안내 ↗</a></li>)}</ul>
  </details>;
}
type Props = {
  initialView:View; context:string; localNotice:LocalCounts|null; scopeTools?:ReactNode; items:FinderItem[]; excluded?:ExcludedItem[]; help?:ReactNode; selected:string[];
  onSelect:(id:string)=>void; comparison:ReactNode; onClose:()=>void; favorites:string[]; onFavorite:(id:string)=>void; storageError?:string;
};

function ProductResults(){
  const asOf=useKoreaDay();
  const [kind,setKind]=useState('SAVINGS');
  const [monthly,setMonthly]=useState(''),[lump,setLump]=useState(''),[term,setTerm]=useState('12');
  const [limit,setLimit]=useState(8);
  const amount=kind==='SAVINGS'?monthly:lump;
  const valid=/^\d+$/.test(amount)&&Number(amount)>0&&Number(amount)<=1e12&&/^\d+$/.test(term)&&Number(term)>=1&&Number(term)<=120;
  const matches=valid?financialProducts(asOf).filter(p=>p.kind===kind).map(product=>({
    product,code:readPreparedDecision(product,Number(amount),Number(term),asOf)
  })).filter(r=>r.code==='FIT'||r.code==='PARTIAL').sort((a,b)=>comparePreparedRecommendations({id:a.product.product_id,kind:a.product.kind,code:a.code},{id:b.product.product_id,kind:b.product.kind,code:b.code},Number(term),asOf)):[];
  const picks=matches.filter(r=>verifiedBasicRate(r.product.product_id,Number(term),asOf)!==null).slice(0,3).map(r=>r.product.product_id);
  return <section className="finder-products"><h3>내 금액과 기간으로 찾기</h3>
    <p>금융상품은 납입 금액과 기간으로 비교합니다. 적금은 매달 넣을 금액을, 예금은 지금 예치할 목돈을 입력하세요.</p>
    <DataFreshness scope="products"/>
    <div className="finder-money">
      <label>저축 방식<select value={kind} onChange={e=>{setKind(e.target.value);setLimit(8);}}><option value="SAVINGS">적금 · 매월 납입</option><option value="DEPOSIT">예금 · 목돈 예치</option></select></label>
      <label>{kind==='SAVINGS'?'월 납입액 (원)':'예치할 목돈 (원)'}<GroupedInput inputMode="numeric" placeholder="예: 200,000" value={amount} onChange={e=>{(kind==='SAVINGS'?setMonthly:setLump)(e.target.value);setLimit(8);}}/></label>
      <label>저축 기간 (개월)<GroupedInput inputMode="numeric" value={term} onChange={e=>{setTerm(e.target.value);setLimit(8);}}/></label>
    </div>
    <p role="status">{!valid?'1원~1조원 사이의 금액과 1~120개월의 기간을 정수로 입력하세요.':`금액·기간 비교 결과 ${matches.length}개 · 가입 대상과 우대조건은 추가 확인`}</p>
    {valid&&<p>전액 납입 가능성을 먼저 보고, 같은 종류·기간에서 확인된 기본금리가 높은 순서입니다. 우대 최고금리·만기이자 순위가 아니며, 금리 미확인 후보에는 추천 순위를 붙이지 않습니다.</p>}
    {matches.slice(0,limit).map(({product:p,code})=>{const rate=verifiedBasicRate(p.product_id,Number(term),asOf);const rank=picks.indexOf(p.product_id);return <article className={'finder-row'+(rank>=0?' finder-recommended':'')} data-product-id={p.product_id} key={p.product_id}>{rank>=0&&<span className="finder-recommendation-badge">우선 추천 {String(rank+1).padStart(2,'0')} · 전액 납입·기본금리 기준</span>}<small>{p.institution} · {code==='FIT'?'금액·기간 일치':'상품 한도 안에서 일부 금액 납입'}</small><h4>{p.product_name}</h4>{rate&&<p className="finder-product-rate">{term}개월 · <strong>기본 연 {rate.base_rate_percent}%</strong><small>금리 확인 {rate.sources.map(s=>s.reviewed_on).sort()[0]}</small></p>}<p>{p.payment_note} · {p.term_note}</p><p>가입 대상 · {p.eligibility_note}</p><a href={p.sources[0].url} target="_blank" rel="noopener noreferrer">은행 공식 안내 ↗</a></article>;})}
    {limit<matches.length&&<button type="button" onClick={()=>setLimit(limit+8)}>상품 더 보기</button>}
  </section>;
}

export default function FinderDialog({initialView,context,localNotice,scopeTools,items,excluded=[],help,selected,onSelect,comparison,onClose,favorites,onFavorite,storageError}:Props){
  const ref=useRef<HTMLDialogElement>(null);
  const [view,setView]=useState<View>(initialView),[limit,setLimit]=useState(8);
  const [productsVisited,setProductsVisited]=useState(false);
  function selectView(next:View){
    if(next==='products')setProductsVisited(true);
    setView(next);
  }
  useEffect(()=>{
    const dialog=ref.current!;
    const trigger=document.activeElement instanceof HTMLElement?document.activeElement:null;
    const previous=document.body.style.overflow;
    if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','');
    document.body.style.overflow='hidden';
    return ()=>{if(typeof dialog.close==='function'&&dialog.open)dialog.close();document.body.style.overflow=previous;trigger?.focus({preventScroll:true});};
  },[]);
  useEffect(()=>{
    window.addEventListener('hashchange',onClose);
    return ()=>window.removeEventListener('hashchange',onClose);
  },[onClose]);
  return <dialog ref={ref} className="finder-dialog" aria-labelledby="finder-title" onCancel={e=>{e.preventDefault();onClose();}}>
    <div className="finder-head"><div><small>청년 경제생활 / 조건 탐색</small><h2 id="finder-title">내 조건으로 찾은 결과</h2></div><button type="button" autoFocus onClick={onClose} aria-label="결과 창 닫기">닫기 ×</button></div>
    <p className="finder-context">{context}</p>
    {localNotice&&view!=='products'&&<LocalNotice {...localNotice}/>}
    <div className="finder-tabs" aria-label="결과 종류">{([['programs',`지원사업 전체 ${items.length}`],['products','적금·예금 찾기'],['compare',`선택 비교 ${selected.length}/3`]] as const).map(([key,label])=><button type="button" aria-pressed={view===key} key={key} onClick={()=>selectView(key)}>{label}</button>)}</div>
    <div className="finder-body">
      {storageError&&<p role="status">{storageError}</p>}
      {view==='programs'&&<><DataFreshness scope="supports"/>{scopeTools}{!scopeTools&&<p>공식 모집 상태와 입력 조건을 함께 확인하세요. 비교할 사업은 최대 3개까지 고를 수 있어요.</p>}
        <p>입력 조건의 일치는 신청·수급 가능 확정이 아닙니다. 소득·재산·거주기간 등 모르는 조건은 추가 확인으로 남깁니다. 관심 저장은 사업 ID만 이 기기에 보관합니다.</p>
        {!items.length&&<div className="finder-empty"><h3>현재 필터에 맞는 안내가 없어요.</h3><p>조건을 수정하거나 분야와 모집 상태의 범위를 넓혀보세요.</p></div>}
        {items.slice(0,limit).map(item=><article key={item.id} className={"finder-row"+(item.recommendationLabel?" finder-recommended":"")}>{item.recommendationLabel&&<span className="finder-recommendation-badge">{item.recommendationLabel} · 모집·지역·입력조건 기준</span>}<div className="finder-meta"><small>{item.status}</small><span>{item.location}</span></div><h3>{item.title}</h3><p>{item.benefit}</p><strong>{item.match}</strong><p>{item.reasons.join(' · ')}</p>{item.deadline&&<DeadlineButton title={item.title} deadline={item.deadline}/>}<p>추가 확인 · {item.checks.join(' · ')}</p><div className="finder-links"><button type="button" className="finder-save" aria-label={item.title+' 관심사업'} aria-pressed={favorites.includes(item.id)} onClick={()=>onFavorite(item.id)}>{favorites.includes(item.id)?'★ 저장됨':'☆ 관심 저장'}</button><label><input type="checkbox" checked={selected.includes(item.id)} disabled={selected.length>=3&&!selected.includes(item.id)} onChange={()=>onSelect(item.id)}/>비교에 담기<span className="sr-only"> {item.title}</span></label><a href={item.url} target="_blank" rel="noopener noreferrer">공식 안내 ↗</a></div></article>)}
        {limit<items.length&&<button type="button" onClick={()=>setLimit(limit+8)}>지원사업 더 보기</button>}
        <ExcludedList items={excluded}/>{help}</>}
      {view==='compare'&&(selected.length?comparison:<div className="finder-empty"><h3>어떤 사업을 비교할까요?</h3><p>추천 결과에서 ‘비교에 담기’를 누르면 모집 일정과 확인할 조건을 나란히 볼 수 있어요.</p><button type="button" onClick={()=>setView('programs')}>비교할 지원사업 고르기</button></div>)}
      <div hidden={view!=='products'}>{productsVisited&&<ProductResults/>}</div>
    </div><footer><button type="button" onClick={onClose}>조건 다시 설정</button>{view==='programs'&&selected.length>0&&<button className="finder-primary" type="button" onClick={()=>setView('compare')}>담은 사업 비교하기 ({selected.length})</button>}</footer>
  </dialog>;
}
