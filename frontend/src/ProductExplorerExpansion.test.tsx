import {fireEvent,render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import ProductExplorer,{FAVORITES_KEY,channelMatches} from './ProductExplorer';
import prepared from './public-data/product-expanded.json';
const id=(name:string)=>document.querySelector(`[data-product-id="${name}"]`)! as HTMLElement;
const edit=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});
function all(){edit('표시 개수','0');}
beforeEach(()=>{vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-03T03:00:00Z'));localStorage.clear();vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('Economic inputs must not leave browser');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});
describe('expanded product discovery',()=>{
 it('paginates without dropping searchable products',async()=>{
  render(<ProductExplorer/>);expect(screen.getAllByTestId('discovery-card')).toHaveLength(12);const first=screen.getAllByTestId('discovery-card')[0].getAttribute('data-product-id');
  expect(screen.getByRole('button',{name:/^이전$/})).toBeDisabled();await userEvent.click(screen.getByRole('button',{name:/^다음$/}));expect(screen.getAllByTestId('discovery-card')[0].getAttribute('data-product-id')).not.toBe(first);
  expect(screen.getByText('2 / '+Math.ceil(prepared.catalog.products.length/12)+' 페이지')).toBeVisible();edit('상품·조건 검색','NH1934');expect(screen.getAllByTestId('discovery-card')).toHaveLength(1);expect(id('NH-1934-COMPOUND')).toBeVisible();
  await userEvent.click(screen.getByRole('button',{name:'필터 초기화'}));all();expect(screen.getAllByTestId('discovery-card')).toHaveLength(prepared.catalog.products.length);
 });
 it('stores only an explicitly favorited product ID and restores it after remount',async()=>{
  const view=render(<ProductExplorer/>);edit('매월 저축할 금액','123456');edit('목표 기간','24');const p=prepared.catalog.products[0];edit('상품·조건 검색',p.product_name);await userEvent.click(screen.getByRole('button',{name:p.product_name+' 관심상품'}));
  expect(JSON.parse(localStorage.getItem(FAVORITES_KEY)!)).toEqual([p.product_id]);expect(localStorage.getItem(FAVORITES_KEY)).not.toContain('123456');
  view.unmount();render(<ProductExplorer/>);await userEvent.click(screen.getByRole('checkbox',{name:'관심상품만 (1)'}));expect(screen.getAllByTestId('discovery-card')).toHaveLength(1);expect(id(p.product_id)).toBeVisible();
  await userEvent.click(screen.getByRole('button',{name:p.product_name+' 관심상품'}));expect(screen.queryAllByTestId('discovery-card')).toHaveLength(0);expect(localStorage.getItem(FAVORITES_KEY)).toBeNull();
 });
 it('ignores malformed or unknown favorite IDs without crashing or fetching',()=>{
  localStorage.setItem(FAVORITES_KEY,'not json');const view=render(<ProductExplorer/>);expect(screen.getAllByTestId('discovery-card')).toHaveLength(12);view.unmount();
  localStorage.setItem(FAVORITES_KEY,JSON.stringify(['unknown',null,{},prepared.catalog.products[0].product_id,prepared.catalog.products[0].product_id]));render(<ProductExplorer/>);expect(screen.getByRole('checkbox',{name:'관심상품만 (1)'})).toBeVisible();expect(fetch).not.toHaveBeenCalled();
 });
 it('falls back to memory if browser storage is denied',async()=>{
  render(<ProductExplorer/>);vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new DOMException('blocked');});const btn=screen.getAllByRole('button',{name:/관심상품$/})[0];await userEvent.click(btn);
  expect(btn).toHaveAttribute('aria-pressed','true');expect(screen.getByText(/현재 화면에서만 유지/)).toBeVisible();
 });
 it('filters only explicitly verified channels and payment schedules',async()=>{
  render(<ProductExplorer/>);edit('가입방법','ONLINE');all();expect(screen.getAllByTestId('discovery-card').every(c=>channelMatches(prepared.catalog.products.find(p=>p.product_id===c.getAttribute('data-product-id'))!,'ONLINE'))).toBe(true);
  expect(channelMatches(prepared.catalog.products.find(p=>p.product_id==='KAKAO-FREE-SAVINGS')!,'ONLINE')).toBe(false);
  edit('납입 방식','DAILY');edit('가입방법','ALL');expect(screen.getAllByTestId('discovery-card')).toHaveLength(3);expect(document.querySelector('.code-fit')).not.toBeInTheDocument();
 });
 it('sorts by name and minimum amount without ranking unsupported yields',async()=>{
  render(<ProductExplorer/>);edit('정렬','MINIMUM');all();let cards=screen.getAllByTestId('discovery-card');const mins=cards.map(c=>prepared.catalog.products.find(p=>p.product_id===c.getAttribute('data-product-id'))!.minimum??Infinity);expect(mins).toEqual([...mins].sort((a,b)=>a-b));
  edit('정렬','NAME');cards=screen.getAllByTestId('discovery-card');const names=cards.map(c=>c.querySelector('h3')!.textContent!);expect(names).toEqual([...names].sort((a,b)=>a.localeCompare(b,'ko')));expect(within(screen.getByLabelText('정렬')).queryByRole('option',{name:/최고금리/})).not.toBeInTheDocument();
 });
 it('clearly separates draft input from the applied comparison',async()=>{
  render(<ProductExplorer/>);edit('매월 저축할 금액','300000');await userEvent.click(within(screen.getByLabelText('매월 저축할 금액').closest('form')!).getByRole('button',{name:'추천 상품 보기'}));edit('매월 저축할 금액','500000');
  expect(screen.getByText(/입력값을 바꿨습니다/)).toBeVisible();expect(screen.getByText(/적용한 조건: 월 300,000원/)).toBeVisible();await userEvent.click(within(screen.getByLabelText('매월 저축할 금액').closest('form')!).getByRole('button',{name:'추천 상품 보기'}));expect(screen.queryByText(/입력값을 바꿨습니다/)).not.toBeInTheDocument();expect(screen.getByText(/적용한 조건: 월 500,000원/)).toBeVisible();
 });
 it('describes a deposit partial allocation as a deposit rather than a monthly cap',async()=>{
  render(<ProductExplorer/>);edit('상품·조건 검색',prepared.catalog.products.find(p=>p.product_id==='IBK-FAMILY-DEPOSIT')!.product_name);edit('예금에 넣을 목돈 선택','100000001');await userEvent.click(within(screen.getByLabelText('매월 저축할 금액').closest('form')!).getByRole('button',{name:'추천 상품 보기'}));const c=within(id('IBK-FAMILY-DEPOSIT'));
  expect(c.getByText('일부 금액으로 비교 가능')).toBeVisible();expect(c.getByText(/예치 100,000,000원 한도/)).toBeVisible();expect(c.queryByText(/월 납입 100,000,000원/)).not.toBeInTheDocument();
 });
 it('holds unsupported increments and combined schedules instead of claiming a fit',async()=>{
  render(<ProductExplorer/>);edit('은행','NH농협은행');all();edit('매월 저축할 금액','300001');await userEvent.click(within(screen.getByLabelText('매월 저축할 금액').closest('form')!).getByRole('button',{name:'추천 상품 보기'}));
  const c=within(id('NH-ALLONE-E-SAVINGS'));expect(c.getByText('공식 조건 미확인')).toBeVisible();expect(c.getByText(/공식 납입 단위가 1,000원/)).toBeVisible();expect(within(id('NH-CHAEUM')).getByText('공식 조건 미확인')).toBeVisible();
 });
 it('opens the broad disclosure directory without sending the entered amount',async()=>{
  render(<ProductExplorer/>);edit('매월 저축할 금액','345678');await userEvent.click(screen.getByRole('button',{name:'은행·저축은행 공시 더 보기'}));expect(await screen.findByRole('heading',{name:'은행·저축은행 적금 공시 넓게 보기'})).toBeVisible();expect(screen.queryByLabelText('매월 저축할 금액')).not.toBeInTheDocument();expect(fetch).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button',{name:'상세 조건 비교 · '+prepared.catalog.products.length+'개'}));expect(screen.getByLabelText('매월 저축할 금액')).toHaveValue('345,678');expect(localStorage.length).toBe(0);
 });
});
