import {render,screen,fireEvent,within} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import ProductExplorer from './ProductExplorer';
import prepared from './public-data/product-expanded.json';
import rates from './public-data/product-recommendations.json';
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-02T03:00:00Z'));});
afterEach(()=>vi.useRealTimers());
function apply(monthly='300000',lump=''){
 fireEvent.change(screen.getByLabelText('매월 저축할 금액'),{target:{value:monthly}});
 fireEvent.change(screen.getByLabelText(/예금에 넣을 목돈/),{target:{value:lump}});
 fireEvent.click(screen.getByRole('button',{name:'추천 상품 보기'}));
}
const picks=()=>Array.from(document.querySelectorAll('[data-recommended-id]'));
it('shows a visible savings top three using verified basic rates rather than conditional maxima',()=>{
 render(<ProductExplorer/>);apply();
 expect(screen.getByRole('region',{name:'내 저축 계획에 맞는 추천 상품'})).toBeVisible();
 expect(picks().slice(0,3).map(p=>p.getAttribute('data-recommended-id'))).toEqual(['KAKAO-FREE-SAVINGS','NOV2-WOORI-TOGETHER2','KN-BETTER-SAVING']);
 expect(picks()[0]).toHaveTextContent('기본 연 3.85%');
 expect(picks()[0]).toHaveTextContent('입력한 금액 전액으로 비교 가능');
 expect(screen.queryByRole('heading',{name:'보유 목돈을 맡기는 예금 추천'})).toBeNull();
 expect(document.querySelector('[data-recommended-id="NOV2-KB-CHILDLOVE"]')).toBeNull();
});
it('separates deposits from savings and applies no monthly budget to a missing lump sum',()=>{
 render(<ProductExplorer/>);apply('300000','10000000');
 expect(screen.getByRole('heading',{name:'보유 목돈을 맡기는 예금 추천'})).toBeVisible();
 expect(picks()).toHaveLength(6);
 const deposit=picks().slice(3);
 expect(deposit.every(c=>prepared.catalog.products.find(p=>p.product_id===c.getAttribute('data-recommended-id'))?.kind==='DEPOSIT')).toBe(true);
});
it('hides previous recommendation cards while an edited input is not applied',()=>{
 render(<ProductExplorer/>);apply();expect(picks().length).toBeGreaterThan(0);
 fireEvent.change(screen.getByLabelText('매월 저축할 금액'),{target:{value:'500000'}});
 expect(picks()).toHaveLength(0);
 expect(screen.getByText(/입력값을 바꿨습니다/)).toBeVisible();
});
it('does not recommend zero budgets, children-only products or unverifiable interest',()=>{
 render(<ProductExplorer/>);apply('0','0');expect(picks()).toHaveLength(0);
 expect(screen.getByText(/이 입력에서 금리까지 검증된 추천 후보는 아직 없어요/)).toBeVisible();
 expect(rates.actual_product_calculation_count).toBe(0);
 for(const id of ['NOV2-KAKAO-CHILD','NOV2-KBANK-MYKIDS','NOV2-TOSS-PRENATAL','NOV2-OK-ROTATE6'])expect(rates.rate_by_product).not.toHaveProperty(id);
});
it('opens the chosen recommendation details without changing applied money',()=>{
 render(<ProductExplorer/>);apply();
 fireEvent.click(within(picks()[0] as HTMLElement).getByRole('button',{name:/조건 자세히 보기/}));
 expect(screen.getAllByTestId('discovery-card')).toHaveLength(1);
 expect(screen.getByLabelText('매월 저축할 금액')).toHaveValue('300,000');
 expect(screen.getByText(/선택한 상품:/)).toBeVisible();
});
it('does not retain rate recommendations after the review window expires',()=>{
 vi.setSystemTime(new Date('2026-11-20T03:00:00Z'));render(<ProductExplorer/>);apply();
 expect(picks()).toHaveLength(0);
 expect(screen.getByText(/자료 재검토 시점이 지나/)).toBeVisible();
});

