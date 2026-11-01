import GroupedInput from './GroupedInput';
import {useEffect,useMemo,useState} from 'react';
import data from './public-data/disclosure-directory.json';

// This is a dated, bank-republished FSS disclosure directory, not primary bank
// contract verification. It never accepts a profile or returns a FIT decision.
export type DisclosureLink={product_id:string;name:string;institution:string;reviewed_on:string;source_url:string};
export default function DisclosureDirectory({links={},onViewProduct}:{links?:Record<string,DisclosureLink>;onViewProduct?:(id:string)=>void}={}){
  const [query,setQuery]=useState(''),[sector,setSector]=useState('ALL'),[bank,setBank]=useState('ALL'),[page,setPage]=useState(1);
  const banks=useMemo(()=>[...new Set(data.products.filter(p=>sector==='ALL'||p.sector===sector).map(p=>p.institution))].sort((a,b)=>a.localeCompare(b,'ko')),[sector]);
  const needle=query.normalize('NFKC').toLocaleLowerCase('ko-KR').trim();
  const filtered=data.products.filter(p=>(sector==='ALL'||p.sector===sector)&&(bank==='ALL'||p.institution===bank)&&(!needle||[p.institution,p.product_name].join(' ').normalize('NFKC').toLocaleLowerCase('ko-KR').includes(needle))).sort((a,b)=>a.institution.localeCompare(b.institution,'ko')||a.product_name.localeCompare(b.product_name,'ko'));
  useEffect(()=>setPage(1),[query,sector,bank]);
  const pages=Math.max(1,Math.ceil(filtered.length/20)),current=Math.min(page,pages),shown=filtered.slice((current-1)*20,current*20);
  function reset(){setQuery('');setSector('ALL');setBank('ALL');setPage(1);}
  return <section className="disclosure-directory" aria-labelledby="disclosure-title"><h3 id="disclosure-title">은행·저축은행 적금 공시 넓게 보기</h3><p>{data.institutions}개 금융회사 · 상품명 기준 {data.unique_products}개 · 원문 {data.raw_rows}개 공시 행</p><p>{data.coverage_note}</p>
    <p className="disclosure-evidence"><a href={data.source_url} target="_blank" rel="noopener noreferrer">케이뱅크 공식 블로그의 금융감독원 공시 재게재 원문 ↗</a><br/>공시 기준 {data.basis_date} · 자료 확인 {data.reviewed_on}. 발행 은행의 개별 약관을 직접 확인한 자료와 증거 수준이 다릅니다. 같은 금융회사·상품명의 적립·이자 방식은 한 항목에 모았습니다. 상세 조건 비교 목록과 겹치는 상품이 있으므로 두 목록의 수를 합산하지 않습니다.</p>
    {Object.keys(links).length>0&&<p className="disclosure-promoted">이 공시 중 {Object.keys(links).length}개 항목을 발행 금융회사 공식 상세에 연결했습니다. 연결 상품의 내 조건 비교는 과거 공시금리 대신 별도 확인한 납입범위·기간을 사용합니다.</p>}
    <div className="disclosure-filters"><label>공시 상품 검색<GroupedInput mode="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="금융회사 또는 상품 이름" autoComplete="off"/></label><label>금융권<select value={sector} onChange={e=>{setSector(e.target.value);setBank('ALL');}}><option value="ALL">은행·저축은행 전체</option><option value="BANK">은행</option><option value="SAVINGS_BANK">저축은행</option></select></label><label>공시 금융회사<select value={bank} onChange={e=>setBank(e.target.value)}><option value="ALL">모든 공시 금융회사</option>{banks.map(b=><option key={b}>{b}</option>)}</select></label></div>
    <div className="discovery-list-heading"><p role="status">공시 참고 {filtered.length}개 검색됨 · {shown.length}개 표시</p><button type="button" className="discovery-use-after" onClick={reset}>공시 검색 초기화</button></div>
    {filtered.length===0&&<p>검색 결과가 없습니다. 이 공시 목록 밖에도 상품이 있을 수 있습니다.</p>}
    <ul className="disclosure-list">{shown.map(p=><li key={p.product_id} data-testid="disclosure-product"><small>{p.institution} · {p.sector==='BANK'?'은행':'저축은행'} · {links[p.product_id]?'발행 금융회사 공식 상세 연결':'현재 판매·납입한도 추가 확인'}</small><h4>{p.product_name}</h4>{links[p.product_id]&&<div className="disclosure-promotion"><span>공식 조건 확인 {links[p.product_id].reviewed_on} · 개인 가입자격은 추가 확인</span><a href={links[p.product_id].source_url} target="_blank" rel="noopener noreferrer">발행 금융회사 공식 상품 확인 ↗</a>{onViewProduct&&<button type="button" onClick={()=>onViewProduct(links[p.product_id].product_id)}>내 조건으로 비교 · {links[p.product_id].name}</button>}</div>}<details><summary>12개월 공시 금리·적립 방식 참고</summary><div className="disclosure-options"><table><thead><tr><th>기간</th><th>적립</th><th>이자 방식</th><th>원문 기본금리</th><th>원문 우대금리</th></tr></thead><tbody>{p.options.map((o,i)=><tr key={i}><td>{o.months}개월</td><td>{o.method}</td><td>{o.interest_type}</td><td>{o.base_rate_percent}%</td><td>{o.source_preferential_rate_percent}%</td></tr>)}</tbody></table></div><p className="disclosure-note">{data.basis_date} 공시의 원문 열 이름을 유지한 참고값입니다. 우대금리를 기본금리에 더하거나 본인의 보장금리로 사용하지 않습니다. 같은 적립·이자 방식에 다른 금리가 있으면 원문의 차이를 그대로 표시하며 하나를 임의 채택하지 않습니다. 실제 금리·판매 여부·대상·한도는 해당 은행에서 확인하세요.</p><a href={data.source_url} target="_blank" rel="noopener noreferrer">공시 재게재 원문에서 확인 ↗</a></details></li>)}</ul>
    {pages>1&&<nav className="discovery-pagination" aria-label="공시 목록 페이지"><button type="button" disabled={current===1} onClick={()=>setPage(current-1)}>공시 이전</button><span aria-live="polite">{current} / {pages} 페이지</span><button type="button" disabled={current===pages} onClick={()=>setPage(current+1)}>공시 다음</button></nav>}
    <p>공시 자료에 없는 납입한도·가입대상을 추정하지 않습니다. 이 목록은 내 조건 일치·정책 자격 판정·실제 만기금액 계산에 사용하지 않습니다.</p>
  </section>;
}
