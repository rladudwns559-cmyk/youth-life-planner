import RecommendationShelf,{verifiedBasicRate,preparedRecommendationRank} from './RecommendationShelf';
import GroupedInput from './GroupedInput';
import {lazy,Suspense,useEffect,useMemo,useState} from 'react';
import prepared from './public-data/product-expanded.json';
import './product-explorer.css';
import {useKoreaDay} from './SupportPlanner';

const DisclosureDirectory=lazy(()=>import('./DisclosureDirectory'));

type Kind='SAVINGS'|'DEPOSIT';
type Code='FIT'|'PARTIAL'|'TERM'|'BUDGET'|'INPUT'|'SCHEDULE'|'REVIEW'|'STALE'|'MISSING'|'UNSET';
type Product=typeof prepared.catalog.products[number];
const promotionReady=(p:Product)=>p.disclosure_ids.length>0&&!p.reference_only&&!p.comparison_hold_reason&&p.maximum_kind!=='UNKNOWN'&&p.minimum!==null;
const disclosureLinks=Object.fromEntries(prepared.catalog.products.filter(promotionReady).flatMap(p=>p.disclosure_ids.map(id=>[id,{product_id:p.product_id,name:p.product_name,institution:p.institution,reviewed_on:p.sources.map(s=>s.reviewed_on).sort().at(-1)!,source_url:p.sources[0].url}])));
const promotedCount=prepared.catalog.products.filter(promotionReady).length;
const publicData=prepared as unknown as {valid_until:string;built_on:string;codebook:Code[];tables:Record<Kind,{product_ids:string[];boundaries:number[];months:Record<string,number>;patterns:number[][][]}>};
const money=(n:number|null)=>n===null?'공식 페이지 확인':n.toLocaleString('ko-KR')+'원';
const labels:Record<Code,string>={FIT:'금액·기간 비교 가능',PARTIAL:'일부 금액으로 비교 가능',TERM:'목표 기간과 다름',BUDGET:'납입 예산 부족',INPUT:'예치할 목돈 입력 필요',SCHEDULE:'납입 일정 추가 확인',REVIEW:'자료 추가 확인',STALE:'자료 재검토 시점',MISSING:'공식 조건 미확인',UNSET:'조건을 입력해 비교하세요'};
function today(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
export function readPreparedDecision(p:Product,amount:number|null,months:number,day=today()):Code{
  if(day<publicData.built_on||day>publicData.valid_until)return 'STALE';
  const t=publicData.tables[p.kind as Kind];
  const row=amount===null?t.boundaries.length:t.boundaries.reduce((found,b,i)=>b<=amount?i:found,0);
  const code=t.patterns[t.months[String(months)]]?.[row]?.[t.product_ids.indexOf(p.product_id)];
  return typeof code==='number'?publicData.codebook[code]??'MISSING':'MISSING';
}
const strength:Record<Code,number>={FIT:0,PARTIAL:1,UNSET:2,INPUT:3,SCHEDULE:4,TERM:5,BUDGET:6,MISSING:7,REVIEW:8,STALE:9};
function payment(p:Product){
  if(p.minimum===null)return p.payment_note;
  if(p.schedule==='QUARTERLY')return '분기 '+money(p.minimum)+' ~ '+money(p.maximum);
  if(p.schedule==='WEEKLY_STEP')return '매주 증액 · 시작액 1천~1만원';
  if(p.schedule==='DAILY')return '하루 '+money(p.minimum)+' ~ '+money(p.maximum);
  if(p.schedule==='CUSTOM_DATE')return p.payment_note;
  return (p.kind==='DEPOSIT'?'목돈 ':'월 ')+money(p.minimum)+(p.maximum_kind==='UNLIMITED'?' 이상 · 상한 없음':p.maximum===null?' 이상 · 상한 확인 필요':' ~ '+money(p.maximum));
}
function period(p:Product){return p.allowed_months?.length?p.allowed_months.join('·')+'개월':p.min_months===null||p.max_months===null?p.term_note:p.min_months===p.max_months?`${p.min_months}개월`:`${p.min_months}~${p.max_months}개월`;}
function reason(p:Product,code:Code){
  if(code==='PARTIAL')return `전체 저축액을 한 상품에 넣을 필요는 없어요. 이 상품은 ${p.kind==='DEPOSIT'?'예치':'월 납입'} ${money(p.maximum)} 한도 안에서 일부 금액을 납입하는 선택지입니다. 나머지 예산은 따로 계획하세요.`;
  if(code==='FIT')return '입력한 금액과 기간이 확보한 공시 범위에 들어갑니다. 가입 대상과 우대조건 충족 여부는 아직 확인하지 않았습니다.';
  if(code==='TERM')return `선택한 기간과 상품 기간이 다릅니다. ${period(p)} 조건을 확인하세요.`;
  if(code==='BUDGET')return `입력한 금액으로 최소 납입 조건을 충족하지 못하거나 저축 예산이 0원입니다.`;
  if(code==='SCHEDULE')return p.payment_note+' '+p.term_note;
  if(code==='REVIEW')return p.reference_reason??'현재 판매 조건을 은행에서 다시 확인해야 합니다.';
  if(code==='STALE')return '자료 검토일로부터 정한 재검토 시점이 지났거나 기기 날짜가 맞지 않습니다. 조건 일치 표시를 보류하고 공식 페이지로 안내합니다.';
  if(code==='INPUT')return p.kind==='DEPOSIT'?'매월 저축액과 이미 보유한 목돈은 다릅니다. 예금에 넣을 목돈을 별도로 입력하세요.':'매월 납입할 저축액을 입력하면 공시 금액 범위를 비교할 수 있습니다.';
  if(code==='MISSING'&&p.comparison_hold_reason)return p.comparison_hold_reason;
  if(code==='MISSING'&&p.amount_increment&&p.amount_increment>1)return `공식 납입 단위가 ${money(p.amount_increment)}입니다. 현재 범위 비교만으로 납입 단위 충족을 확인하지 않아 조건 일치 표시를 보류합니다.`;
  if(code==='MISSING')return p.schedule==='DAILY'?p.term_note+' '+p.payment_note:'한도·일정 등 필수 조건을 확정하지 못해 조건 일치로 표시하지 않습니다.';
  return '저축할 금액과 기간을 입력하면 비교 가능한 상품과 추가 확인할 상품을 나눠 보여드려요.';
}
function ProductCard({product:p,code,selected,onSelect,comparisonFull,favorite,onFavorite,rateMonths,asOf}:{product:Product;code:Code;selected:boolean;onSelect:()=>void;comparisonFull:boolean;favorite:boolean;onFavorite:()=>void;rateMonths:number|null;asOf:string}){
  const [detailsOpen,setDetailsOpen]=useState(false);
  const currentRate=rateMonths===null?null:verifiedBasicRate(p.product_id,rateMonths,asOf);
  const shown=code==='UNSET'&&p.reference_only?'REVIEW':code;
  return <article className="discovery-card" data-testid="discovery-card" data-product-id={p.product_id}>
    <div className="discovery-card-top"><span className="discovery-bank" aria-hidden="true">{p.institution.slice(0,1)}</span><div><p>{p.institution} · {p.kind==='SAVINGS'?'적금':'정기예금'}</p><h3 id={'discovery-product-'+p.product_id} tabIndex={-1}>{p.product_name}</h3></div><label className="discovery-compare"><input type="checkbox" checked={selected} disabled={!selected&&comparisonFull} onChange={onSelect} aria-label={p.product_name+' 비교 선택'}/><span>비교</span></label><button type="button" className="discovery-favorite" aria-label={p.product_name+' 관심상품'} aria-pressed={favorite} onClick={onFavorite}><span aria-hidden="true">{favorite?'★':'☆'}</span></button></div>
    {promotionReady(p)&&<span className="discovery-verified">공시에서 공식 조건 추가 확인</span>}
    <span className={`discovery-status code-${shown.toLowerCase()}`}>{shown==='INPUT'&&p.kind==='SAVINGS'?'월 저축액 입력 필요':labels[shown]}</span>
    {currentRate&&<p className="discovery-basic-rate">입력한 {rateMonths}개월 · <strong>기본 연 {currentRate.base_rate_percent}%</strong>{currentRate.max_total_rate_percent!==null&&<small>조건 충족 최고 연 {currentRate.max_total_rate_percent}%</small>}</p>}
    <dl className="discovery-spec"><div><dt>{p.kind==='DEPOSIT'?'한 번에 예치':'납입 조건'}</dt><dd>{payment(p)}</dd></div><div><dt>가입 기간</dt><dd>{period(p)}</dd></div></dl>
    <p className="discovery-eligibility"><strong>가입 대상</strong> {p.eligibility_note}</p>
    <p className="discovery-reason">{reason(p,shown)}</p>
    <details onToggle={e=>setDetailsOpen(e.currentTarget.open)}><summary>가입 대상·우대조건·공식 근거 자세히</summary>{detailsOpen&&<><dl className="discovery-detail"><div><dt>납입 방식</dt><dd>{p.payment_note}</dd></div><div><dt>기간·만기</dt><dd>{p.term_note}</dd></div><div><dt>가입 대상</dt><dd>{p.eligibility_note}</dd></div><div><dt>특징</dt><dd><ul>{p.features.map((v,i)=><li key={i}>{v}</li>)}</ul></dd></div><div><dt>우대조건</dt><dd><ul>{p.preferential_conditions.map((v,i)=><li key={i}>{v}</li>)}</ul></dd></div><div><dt>가입 채널</dt><dd>{p.channels.join(' · ')}</dd></div><div><dt>중도해지</dt><dd>{p.early_exit_note}</dd></div><div><dt>추가 확인</dt><dd><ul>{p.required_checks.map((v,i)=><li key={i}>{v}</li>)}</ul></dd></div></dl>
      {p.rates.length>0?<div className="discovery-rates"><strong>공시된 기간별 금리 · 세전</strong><p>아래 공시 기준일의 값이며 현재 가입 금리나 본인의 우대 적용 금리가 아닙니다.</p><table><thead><tr><th>기간</th><th>기본 연이율</th><th>조건 충족 시 최고</th></tr></thead><tbody>{p.rates.map((r,i)=><tr key={i}><td>{r.min_months}~{r.max_months}개월</td><td>{r.base_rate_percent===null?'미확인':r.base_rate_percent+'%'}</td><td>{r.max_total_rate_percent===null?'미확인':r.max_total_rate_percent+'%'}</td></tr>)}</tbody></table></div>:<p className="discovery-no-rate">현재 적용 금리는 은행 공식 페이지에서 확인해 주세요. 확인하지 못한 최고금리나 예상 만기금액을 만들지 않습니다.</p>}
      <ul className="discovery-sources">{p.sources.map((s,i)=><li key={i}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.title} ↗</a><small>자료 검토 {s.reviewed_on} · 공시 기준 {s.basis_date??'페이지에 별도 기준일 없음'} · {s.mode==='PREVIOUS_VERIFIED_SNAPSHOT'?'기존 공식 확인 자료':s.mode==='OFFICIAL_INDEXED_PAGE'?'공식 페이지의 검색 색인 자료':s.mode==='OFFICIAL_DOCUMENT'?'공식 문서':'공식 페이지'}</small></li>)}</ul>
      <p>가입 자격: 추가 확인 필요 · 실제 만기금액 계산 미제공</p></>}
    </details>
    <a className="discovery-official" href={p.sources[0].url} target="_blank" rel="noopener noreferrer">은행 공식 정보 확인 <span aria-hidden="true">↗</span></a>
  </article>;
}
function Comparison({products,onClose}:{products:Product[];onClose:()=>void}){
  return <section className="discovery-comparison" aria-labelledby="discovery-comparison-title"><div><h3 id="discovery-comparison-title">선택한 상품 나란히 비교</h3><button type="button" onClick={onClose}>비교 선택 지우기</button></div><div className="discovery-table-scroll" tabIndex={0} role="region" aria-label="선택 상품 비교 표"><table><thead><tr><th scope="col">비교 항목</th>{products.map(p=><th scope="col" key={p.product_id}>{p.institution}<br/>{p.product_name}</th>)}</tr></thead><tbody>{[['납입 조건',(p:Product)=>payment(p)],['기간',(p:Product)=>period(p)],['가입 대상',(p:Product)=>p.eligibility_note],['우대조건',(p:Product)=>p.preferential_conditions.join(' ')],['공시 금리',(p:Product)=>p.rates.length?p.rates.map(r=>`${r.min_months}~${r.max_months}개월: 기본 ${r.base_rate_percent??'미확인'}% / 조건 충족 최고 ${r.max_total_rate_percent??'미확인'}%`).join(' · '):'공식 페이지 추가 확인'],['자료 확인일',(p:Product)=>p.sources.map(s=>s.reviewed_on).sort()[0]],['금리 기준일',(p:Product)=>[...new Set(p.sources.map(s=>s.basis_date??'미표시'))].join(' · ')],['추가 확인',(p:Product)=>p.required_checks.join(' ')]] .map(([title,get])=><tr key={String(title)}><th scope="row">{String(title)}</th>{products.map(p=><td key={p.product_id}>{(get as (p:Product)=>string)(p)}</td>)}</tr>)}</tbody></table></div><p>금리는 표시한 공시 기준일의 세전 연이율입니다. 현재 적용금리·우대조건은 공식 안내에서 다시 확인하세요. 상품별 대안 비교이며 동시에 같은 예산을 중복 배분한 결과가 아닙니다.</p></section>;
}
export const FAVORITES_KEY='aix_product_favorites_v1';
function readFavorites():string[]{try{const raw=localStorage.getItem(FAVORITES_KEY);if(!raw||raw.length>16384)return [];const ids=JSON.parse(raw);return Array.isArray(ids)?[...new Set(ids.filter((id):id is string=>typeof id==='string'&&prepared.catalog.products.some(p=>p.product_id===id)))].slice(0,prepared.catalog.products.length):[];}catch{return [];}}
export function channelMatches(p:Product,channel:string){if(channel==='ALL')return true;const text=p.channels.filter(c=>!c.includes('확인')&&!c.includes('여부')).join(' ');return channel==='ONLINE'?/인터넷|스마트|모바일|비대면|스타뱅킹|i-ONE|하나원큐|NH올원|JB뱅크|앱/.test(text):/영업점/.test(text);}
const searchText=(s:string)=>s.normalize('NFKC').toLocaleLowerCase('ko-KR').replace(/\s+/g,' ').trim();
export default function ProductExplorer({monthlyAmount,termMonths,afterAmount}:{monthlyAmount?:number|null;termMonths?:number|null;afterAmount?:number|null}){
  const [monthly,setMonthly]=useState(monthlyAmount===null||monthlyAmount===undefined?'':String(monthlyAmount));
  const [months,setMonths]=useState(String(termMonths??12)),[lump,setLump]=useState('');
  const [applied,setApplied]=useState<{monthly:number|null;months:number;lump:number|null}|null>(monthlyAmount===null||monthlyAmount===undefined?null:{monthly:monthlyAmount,months:termMonths??12,lump:null});
  const [error,setError]=useState(''),[kind,setKind]=useState('ALL'),[bank,setBank]=useState('ALL'),[query,setQuery]=useState(''),[onlyFit,setOnlyFit]=useState(false),[selection,setSelection]=useState<string[]>([]);
  const [tab,setTab]=useState<'DETAIL'|'DISCLOSURE'>('DETAIL'),[channel,setChannel]=useState('ALL'),[schedule,setSchedule]=useState('ALL'),[order,setOrder]=useState('MATCH');
  const [favorites,setFavorites]=useState<string[]>(readFavorites),[favoriteOnly,setFavoriteOnly]=useState(false),[storageError,setStorageError]=useState('');
  const [onlyVerified,setOnlyVerified]=useState(false),[linkedProduct,setLinkedProduct]=useState<string|null>(null);
  const [page,setPage]=useState(1),[pageSize,setPageSize]=useState(12);
  useEffect(()=>{if(tab==='DETAIL'&&linkedProduct){const heading=document.getElementById('discovery-product-'+linkedProduct);const detail=heading?.closest('article')?.querySelector('details');if(detail)detail.open=true;heading?.focus({preventScroll:true});if(heading&&typeof heading.scrollIntoView==='function')heading.scrollIntoView({block:'center',behavior:'auto'});}},[linkedProduct,tab]);
  useEffect(()=>{if(monthlyAmount!==null&&monthlyAmount!==undefined){setMonthly(String(monthlyAmount));setMonths(String(termMonths??12));setApplied({monthly:monthlyAmount,months:termMonths??12,lump:null});}},[monthlyAmount,termMonths]);
  const day=useKoreaDay(),stale=day<publicData.built_on||day>publicData.valid_until;
  const rows=useMemo(()=>prepared.catalog.products.map(p=>({p,code:applied?readPreparedDecision(p,p.kind==='DEPOSIT'?applied.lump:applied.monthly,applied.months,day):stale?'STALE' as Code:'UNSET' as Code})),[applied,day,stale]);
  const banks=[...new Set(prepared.catalog.products.map(p=>p.institution))].sort((a,b)=>a.localeCompare(b,'ko'));
  const needle=searchText(query);
  const visible=rows.filter(({p,code})=>(!onlyVerified||promotionReady(p))&&(!linkedProduct||p.product_id===linkedProduct)&&(kind==='ALL'||p.kind===kind)&&(bank==='ALL'||p.institution===bank)&&(schedule==='ALL'||p.schedule===schedule)&&channelMatches(p,channel)&&(!onlyFit||code==='FIT'||code==='PARTIAL')&&(!favoriteOnly||favorites.includes(p.product_id))&&(!needle||searchText([p.product_name,p.institution,p.eligibility_note,...p.features,...p.preferential_conditions].join(' ')).includes(needle))).sort((a,b)=>{
    const byName=a.p.product_name.localeCompare(b.p.product_name,'ko')||a.p.institution.localeCompare(b.p.institution,'ko');
    if(order==='NAME')return byName;
    if(order==='MINIMUM')return (a.p.minimum??Infinity)-(b.p.minimum??Infinity)||byName;
    if(order==='TERM')return (a.p.min_months??Infinity)-(b.p.min_months??Infinity)||byName;
    if(order==='MATCH'&&applied){
      const base=strength[a.code]-strength[b.code];
      if(base)return base;
      if(a.p.kind!==b.p.kind)return a.p.kind==='SAVINGS'?-1:1;
      return preparedRecommendationRank(a.p.product_id,a.p.kind,applied.months)-preparedRecommendationRank(b.p.product_id,b.p.kind,applied.months)||byName;
    }
    return strength[a.code]-strength[b.code]||a.p.institution.localeCompare(b.p.institution,'ko')||byName;
  });
  useEffect(()=>{setPage(1);},[kind,bank,query,onlyFit,favoriteOnly,channel,schedule,order,pageSize,applied,onlyVerified,linkedProduct]);
  const pages=pageSize===0?1:Math.max(1,Math.ceil(visible.length/pageSize)),currentPage=Math.min(page,pages);
  const paged=pageSize===0?visible:visible.slice((currentPage-1)*pageSize,currentPage*pageSize);
  const recommended=applied?visible.filter(r=>r.code==='FIT'||r.code==='PARTIAL').map(({p,code})=>({id:p.product_id,name:p.product_name,institution:p.institution,kind:p.kind,code,rate:verifiedBasicRate(p.product_id,applied.months,day),payment:payment(p),checks:p.required_checks,eligibility:p.eligibility_note})).filter((p):p is typeof p & {rate:NonNullable<typeof p.rate>}=>p.rate!==null).sort((a,b)=>Number(a.code==='PARTIAL')-Number(b.code==='PARTIAL')||preparedRecommendationRank(a.id,a.kind,applied.months)-preparedRecommendationRank(b.id,b.kind,applied.months)):[];
  const draftChanged=!!applied&&(monthly!==(applied.monthly===null?'':String(applied.monthly))||months!==String(applied.months)||lump!==(applied.lump===null?'':String(applied.lump)));
  function toggleFavorite(id:string){const next=favorites.includes(id)?favorites.filter(v=>v!==id):[...favorites,id];setFavorites(next);try{if(next.length)localStorage.setItem(FAVORITES_KEY,JSON.stringify(next));else localStorage.removeItem(FAVORITES_KEY);setStorageError('');}catch{setStorageError('이 브라우저에서는 관심상품 저장을 사용할 수 없어 현재 화면에서만 유지합니다.');}}
  function resetFilters(){setOnlyVerified(false);setLinkedProduct(null);setKind('ALL');setBank('ALL');setQuery('');setOnlyFit(false);setFavoriteOnly(false);setChannel('ALL');setSchedule('ALL');setOrder('MATCH');setPage(1);}

  function viewVerifiedProduct(id:string){if(!prepared.catalog.products.some(p=>p.product_id===id&&promotionReady(p)))return;resetFilters();setLinkedProduct(id);setTab('DETAIL');}
  function apply(e:React.FormEvent){e.preventDefault();const whole=(s:string)=>/^\d+$/.test(s)&&Number.isSafeInteger(Number(s));if((monthly===''&&lump==='')||(monthly!==''&&(!whole(monthly)||Number(monthly)>1_000_000_000_000))||!whole(months)||Number(months)<1||Number(months)>120||lump!==''&&(!whole(lump)||Number(lump)>1_000_000_000_000)){setError('월 저축액 또는 목돈을 0~1조원 범위의 정수로 입력해 주세요. 기간은 1~120개월입니다.');return;}setError('');setApplied({monthly:monthly===''?null:Number(monthly),months:Number(months),lump:lump===''?null:Number(lump)});}
  return <section className="product-discovery" aria-labelledby="discovery-heading"><div className="discovery-intro"><div><p className="eyebrow">공식 예·적금 탐색</p><h2 id="discovery-heading">내 조건으로 넓게 살펴보기</h2><p>월 저축액과 기간을 입력하고, 한 번에 비교해 보세요.</p></div><span>{banks.length}개 은행 · {prepared.catalog.products.length}개 상품</span></div>
    <div className="discovery-tabs" role="group" aria-label="상품 자료 범위"><button type="button" aria-pressed={tab==='DETAIL'} onClick={()=>setTab('DETAIL')}>상세 조건 비교 · {rows.length}개</button><button type="button" aria-pressed={tab==='DISCLOSURE'} onClick={()=>setTab('DISCLOSURE')}>은행·저축은행 공시 더 보기</button></div>
    {tab==='DISCLOSURE'?<Suspense fallback={<p role="status">공시 참고 자료를 여는 중입니다.</p>}><DisclosureDirectory links={disclosureLinks} onViewProduct={viewVerifiedProduct}/></Suspense>:<>
    <form className="discovery-form" onSubmit={apply} noValidate><div><label htmlFor="discovery-monthly">매월 저축할 금액</label><div className="discovery-unit"><GroupedInput id="discovery-monthly" value={monthly} onChange={e=>setMonthly(e.target.value)} inputMode="numeric" autoComplete="off" placeholder="예: 300,000"/><span>원</span></div></div><div><label htmlFor="discovery-months">목표 기간</label><div className="discovery-unit"><GroupedInput id="discovery-months" value={months} onChange={e=>setMonths(e.target.value)} inputMode="numeric" autoComplete="off"/><span>개월</span></div></div><div><label htmlFor="discovery-lump">예금에 넣을 목돈 <small>선택</small></label><div className="discovery-unit"><GroupedInput id="discovery-lump" value={lump} onChange={e=>setLump(e.target.value)} inputMode="numeric" autoComplete="off" placeholder="이미 모아둔 금액"/><span>원</span></div></div><button type="submit">추천 상품 보기 <span aria-hidden="true">→</span></button><p className="discovery-privacy">입력은 이 화면에서만 사용합니다. 외부 전송·영구 저장·유료 서비스 연결 없이 비교합니다.</p></form>
    {afterAmount!==undefined&&afterAmount!==null&&<button type="button" className="discovery-use-after" onClick={()=>{setMonthly(String(afterAmount));setMonths(String(termMonths??12));setApplied({monthly:afterAmount,months:termMonths??12,lump:applied?.lump??null});}}>What-if 변경 후 저축 상한 {money(afterAmount)}으로 보기</button>}
    {draftChanged&&<p role="status" className="discovery-draft">입력값을 바꿨습니다. ‘추천 상품 보기’를 누르면 아래 결과에 반영됩니다.</p>}
    {error&&<p role="alert" className="error-message">{error}</p>}
    <p className="discovery-scope">자료 검토 {prepared.catalog.reviewed_on} · {prepared.catalog.coverage_note} 가입 대상·우대조건은 추가 확인이 필요합니다.</p>
    {stale&&<p role="status" className="savings-warning">자료 재검토 시점이 지나 조건 일치 표시를 보류합니다. 목록과 공식 출처는 계속 확인할 수 있습니다.</p>}
    <div className="discovery-stats" aria-live="polite"><span>등록 상품 <b>{rows.length}</b></span><span>금액·기간 비교 가능 <b>{rows.filter(r=>r.code==='FIT').length}</b></span><span>일부 금액 선택지 <b>{rows.filter(r=>r.code==='PARTIAL').length}</b></span><span>정부·지자체 지원은 <a href="#/programs">청년 지원사업에서 확인 ↗</a></span></div>
    {applied&&<p className="discovery-applied">적용한 조건: 월 {applied.monthly===null?'미입력':money(applied.monthly)} · {applied.months}개월 · 목돈 {applied.lump===null?'미입력':money(applied.lump)}. 추천은 검증된 기본금리 기준이며 가입 자격·우대조건은 추가 확인합니다.</p>}
    {applied&&!draftChanged&&<RecommendationShelf items={recommended} months={applied.months} onView={id=>{setLinkedProduct(id);setTab('DETAIL');}}/>}
    <div className="discovery-filters"><label>상품 종류<select value={kind} onChange={e=>setKind(e.target.value)}><option value="ALL">적금·예금 전체</option><option value="SAVINGS">적금</option><option value="DEPOSIT">정기예금</option></select></label><label>은행<select value={bank} onChange={e=>setBank(e.target.value)}><option value="ALL">모든 등록 은행</option>{banks.map(b=><option key={b}>{b}</option>)}</select></label><label className="discovery-search">상품·조건 검색<GroupedInput mode="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="은행, 상품명, 급여, 여행, 청년…" autoComplete="off"/></label><label>가입방법<select value={channel} onChange={e=>setChannel(e.target.value)}><option value="ALL">전체 채널</option><option value="ONLINE">온라인·모바일 확인</option><option value="BRANCH">영업점 확인</option></select></label><label>납입 방식<select value={schedule} onChange={e=>setSchedule(e.target.value)}><option value="ALL">모든 납입 방식</option><option value="MONTHLY">월 납입</option><option value="LUMP_SUM">목돈 예치</option><option value="QUARTERLY">분기 한도</option><option value="DAILY">일 납입</option><option value="WEEKLY_STEP">주간 증액</option><option value="CUSTOM_DATE">날짜 지정</option></select></label><label>정렬<select value={order} onChange={e=>setOrder(e.target.value)}><option value="MATCH">추천순 · 전액 납입·기본금리</option><option value="NAME">상품 이름 순</option><option value="MINIMUM">최소 납입금 낮은 순</option><option value="TERM">짧은 가입기간 순</option></select></label></div>
    {linkedProduct&&<p className="discovery-linked" role="status">선택한 상품: {prepared.catalog.products.find(p=>p.product_id===linkedProduct)?.product_name} · 입력한 금액·기간으로 비교합니다. <button type="button" onClick={resetFilters}>선택 해제하고 전체 보기</button></p>}
    <div className="discovery-switches"><label><input type="checkbox" checked={onlyVerified} onChange={e=>setOnlyVerified(e.target.checked)}/>공식 조건 추가 확인 상품만 ({promotedCount})</label><label><input type="checkbox" checked={onlyFit} onChange={e=>setOnlyFit(e.target.checked)}/>금액·기간 비교 가능만</label><label><input type="checkbox" checked={favoriteOnly} onChange={e=>setFavoriteOnly(e.target.checked)}/>관심상품만 ({favorites.length})</label><button type="button" onClick={resetFilters}>필터 초기화</button></div>
    <p className="discovery-storage">별표를 누르면 상품 ID만 이 브라우저에 저장합니다. 소득·저축액은 저장하지 않으며 알림 구독 기능은 아닙니다.</p>
    {storageError&&<p role="status">{storageError}</p>}
    <div className="discovery-list-heading"><p role="status">{visible.length}개 상품 검색됨 · 현재 {paged.length}개 표시 · 등록한 전체 목록 안에서 검색합니다.</p><label>표시 개수<select value={pageSize} onChange={e=>setPageSize(Number(e.target.value))}><option value={12}>12개씩</option><option value={24}>24개씩</option><option value={0}>전체 보기</option></select></label><p>최대 3개를 선택해 비교하세요.</p></div>
    {selection.length>0&&<Comparison products={prepared.catalog.products.filter(p=>selection.includes(p.product_id))} onClose={()=>setSelection([])}/>}
    {visible.length===0&&<div className="matching-empty"><strong>선택한 검색 조건에 맞는 상품이 없습니다.</strong><p>등록된 자료 안에서의 결과입니다. 다른 은행에도 상품이 없다는 뜻은 아닙니다.</p><button type="button" onClick={resetFilters}>검색 조건 지우고 전체 보기</button></div>}
    <div className="discovery-grid">{paged.map(({p,code})=><ProductCard key={p.product_id} product={p} code={code} rateMonths={applied?.months??null} asOf={day} favorite={favorites.includes(p.product_id)} onFavorite={()=>toggleFavorite(p.product_id)} selected={selection.includes(p.product_id)} comparisonFull={selection.length>=3} onSelect={()=>setSelection(old=>old.includes(p.product_id)?old.filter(id=>id!==p.product_id):old.length<3?[...old,p.product_id]:old)}/>)}</div>
    {pages>1&&<nav className="discovery-pagination" aria-label="상품 목록 페이지"><button type="button" disabled={currentPage===1} onClick={()=>setPage(currentPage-1)}>이전</button><span aria-live="polite">{currentPage} / {pages} 페이지</span><button type="button" disabled={currentPage===pages} onClick={()=>setPage(currentPage+1)}>다음</button></nav>}
    <div className="discovery-bottom-note"><strong>더 많은 상품을 찾고 계신가요?</strong><p>현재는 공식 근거를 확보한 상품부터 제공합니다. 모든 은행·저축은행·특판까지 포함한 전수 목록은 아직 아닙니다. 정부 지원금과 실제 상품의 만기금액은 이 비교에서 계산하지 않습니다.</p></div>
    </>}
  </section>;
}
