import GroupedInput from './GroupedInput';
import {useEffect,useRef,useState,type ReactNode} from 'react';
import savings from './public-data/product-expanded.json';
import {readPreparedDecision} from './ProductExplorer';
import './finder-dialog.css';
import LocalNotice, {type LocalCounts} from './LocalNotice';

type View = 'programs' | 'products' | 'compare';
export type FinderItem = {
  id:string; title:string; location:string; benefit:string; status:string;
  match:string; checks:string[]; reasons:string[]; url:string;
};
type Props = {
  initialView:View; context:string; localNotice:LocalCounts|null; scopeTools?:ReactNode; items:FinderItem[]; selected:string[];
  onSelect:(id:string)=>void; comparison:ReactNode; onClose:()=>void;
};

function ProductResults(){
  const [kind,setKind]=useState('SAVINGS');
  const [monthly,setMonthly]=useState(''),[lump,setLump]=useState(''),[term,setTerm]=useState('12');
  const [limit,setLimit]=useState(8);
  const amount=kind==='SAVINGS'?monthly:lump;
  const valid=/^\d+$/.test(amount)&&Number(amount)>0&&Number(amount)<=1e12&&/^\d+$/.test(term)&&Number(term)>=1&&Number(term)<=120;
  const matches=valid?savings.catalog.products.filter(p=>p.kind===kind).map(product=>({
    product,code:readPreparedDecision(product,Number(amount),Number(term))
  })).filter(r=>r.code==='FIT'||r.code==='PARTIAL').sort((a,b)=>Number(a.code==='PARTIAL')-Number(b.code==='PARTIAL')):[];
  return <section className="finder-products"><h3>내 금액과 기간으로 찾기</h3>
    <p>금융상품은 납입 금액과 기간으로 비교합니다. 적금은 매달 넣을 금액을, 예금은 지금 예치할 목돈을 입력하세요.</p>
    <div className="finder-money">
      <label>저축 방식<select value={kind} onChange={e=>{setKind(e.target.value);setLimit(8);}}><option value="SAVINGS">적금 · 매월 납입</option><option value="DEPOSIT">예금 · 목돈 예치</option></select></label>
      <label>{kind==='SAVINGS'?'월 납입액 (원)':'예치할 목돈 (원)'}<GroupedInput inputMode="numeric" placeholder="예: 200,000" value={amount} onChange={e=>{(kind==='SAVINGS'?setMonthly:setLump)(e.target.value);setLimit(8);}}/></label>
      <label>저축 기간 (개월)<GroupedInput inputMode="numeric" value={term} onChange={e=>{setTerm(e.target.value);setLimit(8);}}/></label>
    </div>
    <p role="status">{!valid?'1원~1조원 사이의 금액과 1~120개월의 기간을 정수로 입력하세요.':`금액·기간 비교 결과 ${matches.length}개 · 가입 대상과 우대조건은 추가 확인`}</p>
    {matches.slice(0,limit).map(({product:p,code})=><article className="finder-row" key={p.product_id}><small>{p.institution} · {code==='FIT'?'금액·기간 일치':'상품 한도 안에서 일부 금액 납입'}</small><h4>{p.product_name}</h4><p>{p.payment_note} · {p.term_note}</p><p>가입 대상 · {p.eligibility_note}</p><a href={p.sources[0].url} target="_blank" rel="noopener noreferrer">은행 공식 안내 ↗</a></article>)}
    {limit<matches.length&&<button type="button" onClick={()=>setLimit(limit+8)}>상품 더 보기</button>}
  </section>;
}

export default function FinderDialog({initialView,context,localNotice,scopeTools,items,selected,onSelect,comparison,onClose}:Props){
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
      {view==='programs'&&<>{scopeTools}{!scopeTools&&<p>공식 모집 상태와 입력 조건을 함께 확인하세요. 비교할 사업은 최대 3개까지 고를 수 있어요.</p>}
        {!items.length&&<div className="finder-empty"><h3>현재 필터에 맞는 안내가 없어요.</h3><p>조건을 수정하거나 분야와 모집 상태의 범위를 넓혀보세요.</p></div>}
        {items.slice(0,limit).map(item=><article key={item.id} className="finder-row"><div className="finder-meta"><small>{item.status}</small><span>{item.location}</span></div><h3>{item.title}</h3><p>{item.benefit}</p><strong>{item.match}</strong><p>{item.reasons.join(' · ')}</p><p>추가 확인 · {item.checks.join(' · ')}</p><div className="finder-links"><label><input type="checkbox" checked={selected.includes(item.id)} disabled={selected.length>=3&&!selected.includes(item.id)} onChange={()=>onSelect(item.id)}/>비교에 담기<span className="sr-only"> {item.title}</span></label><a href={item.url} target="_blank" rel="noopener noreferrer">공식 안내 ↗</a></div></article>)}
        {limit<items.length&&<button type="button" onClick={()=>setLimit(limit+8)}>지원사업 더 보기</button>}</>}
      {view==='compare'&&(selected.length?comparison:<div className="finder-empty"><h3>어떤 사업을 비교할까요?</h3><p>추천 결과에서 ‘비교에 담기’를 누르면 모집 일정과 확인할 조건을 나란히 볼 수 있어요.</p><button type="button" onClick={()=>setView('programs')}>비교할 지원사업 고르기</button></div>)}
      <div hidden={view!=='products'}>{productsVisited&&<ProductResults/>}</div>
    </div><footer><button type="button" onClick={onClose}>조건 다시 설정</button>{view==='programs'&&selected.length>0&&<button className="finder-primary" type="button" onClick={()=>setView('compare')}>담은 사업 비교하기 ({selected.length})</button>}</footer>
  </dialog>;
}
