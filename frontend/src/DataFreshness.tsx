import products from './public-data/product-expanded.json';
import supports from './public-data/current-support-web.json';
import {useKoreaDay} from './SupportPlanner';
import './data-freshness.css';

/** Shows existing snapshot metadata. It never extends validity or changes a decision. */
export default function DataFreshness({scope}:{scope:'products'|'supports'}){
 const today=useKoreaDay();
 const financial=scope==='products';
 const verified=financial?products.catalog.reviewed_on:(supports.updated_on??supports.built_on);
 const expired=financial&&(today<products.built_on||today>products.valid_until);
 return <aside className={'data-freshness'+(expired?' needs-review':'')} aria-label={financial?'금융상품 자료 확인 안내':'지원사업 자료 확인 안내'}>
  <span className="freshness-symbol" aria-hidden="true">{expired?'!':'i'}</span>
  <div><strong>{expired?'추천 자료를 다시 확인할 시점이에요.':'확인한 자료를 바탕으로 비교해요.'}</strong>
   <p>자료 확인 <time dateTime={verified}>{verified}</time> · 화면 기준 <time dateTime={today}>{today}</time>{financial&&<> · 추천 자료 재확인 기한 <time dateTime={products.valid_until}>{products.valid_until}</time></>}</p>
   <small>{financial?(expired?'금액·기간 일치와 금리 추천을 보류합니다. 상품 설명과 공식 링크는 계속 볼 수 있어요.':'공개 금리는 확인일 기준입니다. 가입 전 현재 금리·우대조건을 은행에서 확인하세요.'):'실시간 접수 조회가 아닙니다. 공고 기간 안이어도 예산 소진·추가 공고·최종 자격은 공식 신청처에서 확인하세요.'}</small>
  </div>
 </aside>;
}
