import {fireEvent,render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import ProductExplorer from './ProductExplorer';
import catalog from './public-data/product-expanded.json';
const card=(pid:string)=>document.querySelector(`[data-product-id="${pid}"]`)! as HTMLElement;
const edit=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});
async function apply(monthly='300000'){edit('매월 저축할 금액',monthly);await userEvent.click(screen.getByRole('button',{name:'추천 상품 보기'}));}
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-03T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('Do not transmit input');}));});
afterEach(()=>vi.useRealTimers());
describe('verified disclosure promotion to real product comparison',()=>{
 it('shows all thirteen new alternatives through actual prepared Python decisions',async()=>{
  render(<ProductExplorer/>);await userEvent.click(screen.getByRole('checkbox',{name:'공식 조건 추가 확인 상품만 (13)'}));edit('표시 개수','0');await apply();
  expect(screen.getAllByTestId('discovery-card')).toHaveLength(13);expect(screen.getAllByTestId('discovery-card').every(c=>c.querySelector('.code-fit,.code-partial'))).toBe(true);
  expect(within(card('WELCOME-WALKING')).getByText('일부 금액으로 비교 가능')).toBeVisible();expect(within(card('PEPPER-2030')).getByText('금액·기간 비교 가능')).toBeVisible();expect(fetch).not.toHaveBeenCalled();
 });
 it('honors a published minimum and never changes individual eligibility',async()=>{
  render(<ProductExplorer/>);edit('상품·조건 검색','iM함께');await apply('99999');expect(within(card('IM-TOGETHER-SAVINGS')).getByText('납입 예산 부족')).toBeVisible();await apply('100000');expect(within(card('IM-TOGETHER-SAVINGS')).getByText('금액·기간 비교 가능')).toBeVisible();
  await userEvent.click(within(card('IM-TOGETHER-SAVINGS')).getByText('가입 대상·우대조건·공식 근거 자세히'));expect(within(card('IM-TOGETHER-SAVINGS')).getByText('가입 자격: 추가 확인 필요 · 실제 만기금액 계산 미제공')).toBeVisible();
 });
 it('makes special eligibility visible on the card and preserves missing eligibility',async()=>{
  render(<ProductExplorer/>);edit('상품·조건 검색','아이사랑');await apply('100000');expect(card('WELCOME-CHILDLOVE').querySelector('.discovery-eligibility')).toHaveTextContent('만16세이하');expect(within(card('WELCOME-CHILDLOVE')).getByText('금액·기간 비교 가능')).toBeVisible();
 });
 it('links the original disclosure to one verified product while retaining applied inputs',async()=>{
  render(<ProductExplorer/>);await apply('300000');await userEvent.click(screen.getByRole('button',{name:'은행·저축은행 공시 더 보기'}));await screen.findByLabelText('공시 상품 검색');edit('공시 상품 검색','페퍼스2030');
  expect(screen.getByText(/이 공시 중 14개 항목/)).toBeVisible();await userEvent.click(screen.getByRole('button',{name:'추천 상품 보기 · 페퍼스2030적금'}));expect(screen.getAllByTestId('discovery-card')).toHaveLength(1);expect(card('PEPPER-2030')).toBeVisible();expect(card('PEPPER-2030').querySelector('h3')).toHaveFocus();expect(screen.getByLabelText('매월 저축할 금액')).toHaveValue('300,000');expect(within(card('PEPPER-2030')).getByText('금액·기간 비교 가능')).toBeVisible();
  await userEvent.click(screen.getByRole('button',{name:'선택 해제하고 전체 보기'}));edit('표시 개수','0');expect(screen.getAllByTestId('discovery-card')).toHaveLength(catalog.catalog.products.length);expect(fetch).not.toHaveBeenCalled();
 });
 it('does not show a direct comparison action for an unverified source row',async()=>{
  render(<ProductExplorer/>);await userEvent.click(screen.getByRole('button',{name:'은행·저축은행 공시 더 보기'}));await screen.findByLabelText('공시 상품 검색');edit('공시 상품 검색','Fi 시드머니');expect(screen.getAllByTestId('disclosure-product')).toHaveLength(1);expect(screen.queryByRole('button',{name:/추천 상품 보기 ·/})).not.toBeInTheDocument();expect(screen.getByText(/현재 판매·납입한도 추가 확인/)).toBeVisible();
 });
 it('has exactly one product record for two related Pepper disclosures',()=>{
  const p=catalog.catalog.products.filter(p=>p.product_id==='PEPPER-REGULAR');expect(p).toHaveLength(1);expect(p[0].disclosure_ids).toHaveLength(2);
 });
});
