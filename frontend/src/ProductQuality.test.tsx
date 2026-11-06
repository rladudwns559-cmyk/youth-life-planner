import {render,screen,fireEvent,within} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
// This file preserves the original Nov 3 snapshot's expiry contract.
// Live rechecks are exercised separately in FinancialRenewals.test.tsx.
vi.mock('./public-data/financial-renewals.json',()=>({default:{built_on:'2026-11-06',records:{},recommendations:{rate_by_product:{},order_calendar:{},order_pool:[]}}}));
import DataFreshness from './DataFreshness';
import ProductExplorer from './ProductExplorer';
import RegionalPrograms from './RegionalPrograms';
import {ServiceGuide} from './ServiceShell';
import ErrorBoundary from './ErrorBoundary';
import release from './public-data/release-summary.json';

beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-06T03:00:00Z'));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});

it('keeps the verification date distinct from today and expires at the existing boundary',()=>{
 render(<DataFreshness scope="products"/>);
 const note=screen.getByRole('complementary',{name:'금융상품 자료 확인 안내'});
 expect(note).toHaveTextContent('자료 확인 2026-11-03');
 expect(note).toHaveTextContent('화면 기준 2026-11-06');
 expect(note).not.toHaveClass('needs-review');
 vi.setSystemTime(new Date('2026-11-07T00:00:00Z'));fireEvent(window,new Event('focus'));
 expect(note).toHaveClass('needs-review');expect(note).toHaveTextContent('금액·기간 일치와 금리 추천을 보류');
});

it('shows source-driven guide totals and distinguishes product/channel cards from full coverage',()=>{
 render(<ServiceGuide/>);fireEvent.click(screen.getByText('모든 금융상품을 볼 수 있나요?'));
 const detail=screen.getByText('모든 금융상품을 볼 수 있나요?').closest('details')!;
 expect(detail).toHaveTextContent(`${release.institutions}개 금융회사`);
 expect(detail).toHaveTextContent(`상세 ${release.product_count}개`);
 expect(detail).toHaveTextContent(`모집 안내 ${release.support_count}개`);
 expect(detail).not.toHaveTextContent('상세 상품 113개');
 expect(detail).toHaveTextContent('전수 수집한 목록은 아닙니다');
});

it('gives the finder the same independently fixed top-three as the product page',()=>{
 const first=render(<ProductExplorer/>);
 fireEvent.change(screen.getByLabelText('매월 저축할 금액'),{target:{value:'300000'}});
 fireEvent.click(screen.getByRole('button',{name:'추천 상품 보기'}));
 const expected=['NOV3-SB-BULIM-TOK-SAVE','NOV3-SB-MOA-E-SAVE','KAKAO-FREE-SAVINGS'];
 expect(Array.from(document.querySelectorAll('[data-recommended-id]'),p=>p.getAttribute('data-recommended-id'))).toEqual(expected);
 first.unmount();render(<RegionalPrograms browse={false}/>);
 fireEvent.click(screen.getByRole('button',{name:'사업 비교하기 (0/3)'}));
 const dialog=screen.getByRole('dialog');const d=within(dialog);
 fireEvent.click(d.getByRole('button',{name:'적금·예금 찾기'}));
 fireEvent.change(d.getByLabelText('월 납입액 (원)'),{target:{value:'300000'}});
 const cards=Array.from(dialog.querySelectorAll('[data-product-id]'));
 expect(cards.slice(0,3).map(c=>c.getAttribute('data-product-id'))).toEqual(expected);
 expect(cards[0]).toHaveTextContent('기본 연 4.20%');
 expect(cards[0]).toHaveTextContent('가입 대상');
 expect(d.getByText(/가입 대상과 우대조건은 추가 확인/)).toBeVisible();
 expect(localStorage.length).toBe(0);
});

it('removes every finder recommendation on expiry without silently extending the snapshot',()=>{
 vi.setSystemTime(new Date('2026-11-07T03:00:00Z'));render(<RegionalPrograms browse={false}/>);
 fireEvent.click(screen.getByRole('button',{name:'사업 비교하기 (0/3)'}));const d=within(screen.getByRole('dialog'));
 fireEvent.click(d.getByRole('button',{name:'적금·예금 찾기'}));
 fireEvent.change(d.getByLabelText('월 납입액 (원)'),{target:{value:'300000'}});
 expect(d.getByRole('status')).toHaveTextContent('0개');
 expect(d.queryByText(/우선 추천 01/)).toBeNull();
 expect(d.getByText('추천 자료를 다시 확인할 시점이에요.')).toBeVisible();
});

it('keeps the page usable after an actual render error with an explicit recovery action',()=>{
 vi.spyOn(console,'error').mockImplementation(()=>{});
 function Broken():never{throw new Error('Synthetic render failure');}
 render(<ErrorBoundary><Broken/></ErrorBoundary>);
 expect(screen.getByRole('alert')).toHaveTextContent('새로고침하면 입력한 조건은 초기화됩니다');
 expect(screen.getByRole('button',{name:'화면 다시 불러오기'})).toBeVisible();
 expect(screen.getByRole('link',{name:/온통청년 공식 정책 검색/})).toHaveAttribute('href','https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch');
 expect(screen.queryByText('Synthetic render failure')).toBeNull();
});
