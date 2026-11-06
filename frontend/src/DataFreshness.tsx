import supports from './public-data/current-support-web.json';
import {useKoreaDay} from './SupportPlanner';
import './data-freshness.css';
import {financialFreshness,discontinuedRechecks} from './financial-snapshots';

/** Shows existing snapshot metadata. It never extends validity or changes a decision. */
export default function DataFreshness({scope}:{scope:'products'|'supports'}){
 const today=useKoreaDay();
 const financial=scope==='products';
 const freshness=financialFreshness(today);
 const verified=financial?freshness.verifiedOn:(supports.updated_on??supports.built_on);
 const expired=financial&&freshness.expired;
 return <aside className={'data-freshness'+(expired?' needs-review':'')} aria-label={financial?'금융상품 자료 확인 안내':'지원사업 자료 확인 안내'}>
  <span className="freshness-symbol" aria-hidden="true">{expired?'!':'i'}</span>
  <div><strong>{expired?'추천 자료를 다시 확인할 시점이에요.':'확인한 자료를 바탕으로 비교해요.'}</strong>
   <p>자료 확인 <time dateTime={verified}>{verified}</time> · 화면 기준 <time dateTime={today}>{today}</time>{financial&&<> · {freshness.hasRechecks?'가장 가까운 재검토 기한':'추천 자료 재확인 기한'} <time dateTime={freshness.validUntil}>{freshness.validUntil}</time></>}</p>
   {financial&&freshness.hasRechecks&&<><p className="freshness-summary">재확인 유효 {freshness.active}개 · 기본금리 근거 {freshness.rateVerified}개</p><ul className="freshness-stats" aria-label="자료 확인 현황"><li><b>{freshness.active}</b><span>재확인 유효</span></li><li><b>{freshness.rateVerified}</b><span>기본금리 근거</span></li><li><b>{freshness.held}</b><span>검토 보류</span></li><li><b>{freshness.notRechecked}</b><span>이번 재확인 전 자료</span></li></ul><details className="freshness-detail"><summary>추천 후보는 어떻게 정해지나요?</summary><p>상품별 확인일·기한과 입력 금액·기간에 따라 추천 후보가 달라집니다. 기한이 지났거나 판매 미확인·종료 상품은 추천하지 않습니다. 납입 상한이 공시에 없는 상품은 금리를 확인했어도 추천 후보에서 제외됩니다.</p></details></>}
   <small>{financial?(expired?'금액·기간 일치와 금리 추천을 보류합니다. 상품 설명과 공식 링크는 계속 볼 수 있어요.':'공개 금리는 확인일 기준입니다. 가입 전 현재 금리·우대조건을 은행에서 확인하세요.'):'실시간 접수 조회가 아닙니다. 공고 기간 안이어도 예산 소진·추가 공고·최종 자격은 공식 신청처에서 확인하세요.'}</small>
   {financial&&freshness.hasRechecks&&discontinuedRechecks(today).length>0&&<details className="freshness-ended"><summary>판매 종료로 제외된 상품 확인</summary>{discontinuedRechecks(today).map(p=><p key={p.product_id}>{p.institution} {p.product_name} · 판매 종료 시행 {p.effective_on} · 공식 공지 재확인 {p.checked_on}. 기존부터 제외된 상품이며 신규 판매종료 건수로 집계하지 않습니다. <a href={p.source.url} target="_blank" rel="noopener noreferrer">은행 공식 종료 공지 ↗</a></p>)}</details>}
  </div>
 </aside>;
}
