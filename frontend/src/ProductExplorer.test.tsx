import type {ReactElement} from 'react';
import {fireEvent,render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import ProductExplorer,{readPreparedDecision} from './ProductExplorer';
import prepared from './public-data/product-expanded.json';

beforeEach(()=>{vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-03T03:00:00Z'));localStorage.clear();vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('No network allowed for discovery');}));});
afterEach(()=>vi.useRealTimers());
function renderExplorer(view:ReactElement,all=false){const result=render(view);if(all)fireEvent.change(screen.getByLabelText('표시 개수'),{target:{value:'0'}});return result;}
// Keep per-product assertions on the actual search path instead of rendering74hidden-detail cards for every input edit.
const card=(id:string)=>{let found=document.querySelector(`[data-product-id="${id}"]`);if(!found){const product=prepared.catalog.products.find(p=>p.product_id===id)!;fireEvent.change(screen.getByLabelText('상품·조건 검색'),{target:{value:product.product_name}});found=document.querySelector(`[data-product-id="${id}"]`);}return found! as HTMLElement;};
const edit=(id:string,value:string)=>fireEvent.change(screen.getByLabelText(id),{target:{value}});
async function apply(monthly='300000',months='12',lump=''){edit('매월 저축할 금액',monthly);edit('목표 기간',months);edit(/예금에 넣을 목돈/ as unknown as string,lump);await userEvent.click(within(screen.getByLabelText('매월 저축할 금액').closest('form')!).getByRole('button',{name:'추천 상품 보기'}));}

describe('free public product discovery',()=>{
  it('shows the expanded catalog before any profile or server request',()=>{
    renderExplorer(<ProductExplorer/>,true);expect(screen.getAllByTestId('discovery-card')).toHaveLength(prepared.catalog.products.length);expect(screen.getByText('38개 은행 · 256개 상품')).toBeVisible();
    expect(screen.getByText(/국내 모든 은행·저축은행·특판을 전수 수집한 목록이 아닙/)).toBeVisible();expect(fetch).not.toHaveBeenCalled();
    expect(screen.getByLabelText('매월 저축할 금액')).toHaveValue('');expect(within(card('KAKAO-FREE-SAVINGS')).queryByText('금액·기간 비교 가능')).not.toBeInTheDocument();
  });
  it('compares supplied money and period while preserving unknown eligibility',async()=>{
    renderExplorer(<ProductExplorer/>);await apply();
    expect(within(card('KB-MY-SAVING')).getByText('금액·기간 비교 가능')).toBeVisible();
    await userEvent.click(within(card('KB-MY-SAVING')).getByText('가입 대상·우대조건·공식 근거 자세히'));
    expect(within(card('KB-MY-SAVING')).getByText(/가입 자격: 추가 확인 필요/)).toBeVisible();expect(fetch).not.toHaveBeenCalled();expect(Object.keys(localStorage)).toEqual([]);
  });
  it('keeps smaller-cap products visible as explicit partial alternatives',async()=>{
    renderExplorer(<ProductExplorer/>);await apply('500000');
    const c=within(card('KBANK-CODEK-SAVINGS'));expect(c.getByText('일부 금액으로 비교 가능')).toBeVisible();expect(c.getByText(/나머지 예산은 따로 계획/)).toBeVisible();
    expect(screen.getByLabelText('매월 저축할 금액')).toHaveValue('500,000');
  });
  it('does not borrow monthly saving capacity as an existing deposit balance',async()=>{
    renderExplorer(<ProductExplorer/>);await apply('2000000');expect(within(card('KAKAO-DEPOSIT')).getByText('예치할 목돈 입력 필요')).toBeVisible();
    await apply('2000000','12','999999');expect(within(card('KAKAO-DEPOSIT')).getByText('납입 예산 부족')).toBeVisible();
    await apply('2000000','12','1000000');expect(within(card('KAKAO-DEPOSIT')).getByText('금액·기간 비교 가능')).toBeVisible();
  });
  it('allows deposit-only comparison without inventing a monthly budget',async()=>{
    renderExplorer(<ProductExplorer/>);await apply('','12','2000000');expect(within(card('KAKAO-DEPOSIT')).getByText('금액·기간 비교 가능')).toBeVisible();
    expect(within(card('KB-MY-SAVING')).getByText('월 저축액 입력 필요')).toBeVisible();expect(screen.getByText(/적용한 조건: 월 미입력/)).toBeVisible();
  });
  it('preserves discrete periods, quarterly caps and historical evidence boundaries',async()=>{
    renderExplorer(<ProductExplorer/>);await apply('300000','13');
    expect(within(card('KB-CLEAR-SKY')).getByText('목표 기간과 다름')).toBeVisible();
    expect(within(card('SHINHAN-SOL')).getByText('자료 추가 확인')).toBeVisible();
    await apply('300000','12');expect(within(card('HANA-SALARY')).getByText('납입 일정 추가 확인')).toBeVisible();
    expect(within(card('HANA-SALARY')).getAllByText(/월 한도가 아닌 분기 한도/).some(e=>e.classList.contains('discovery-reason'))).toBe(true);
  });
  it('keeps daily and stepped weekly schedules out of monthly fits',async()=>{
    renderExplorer(<ProductExplorer/>);await apply('300000','6');expect(within(card('KAKAO-26W')).getByText('납입 일정 추가 확인')).toBeVisible();
    await apply('300000','1');expect(within(card('KAKAO-31D')).getByText('공식 조건 미확인')).toBeVisible();
  });
  it.each(['-1','1.5','1_000','1e6','1000000000001'])('rejects invalid money %s without a request',async(amount)=>{
    renderExplorer(<ProductExplorer/>);await apply(amount);expect(screen.getByRole('alert')).toHaveTextContent('정수');expect(fetch).not.toHaveBeenCalled();
  });
  it('searches across banks and types and restores all results',async()=>{
    renderExplorer(<ProductExplorer/>,true);await userEvent.selectOptions(screen.getByLabelText('은행'),'하나은행');expect(screen.getAllByTestId('discovery-card')).toHaveLength(prepared.catalog.products.filter(p=>p.institution==='하나은행').length);
    await userEvent.selectOptions(screen.getByLabelText('상품 종류'),'DEPOSIT');expect(screen.getAllByTestId('discovery-card')).toHaveLength(prepared.catalog.products.filter(p=>p.institution==='하나은행'&&p.kind==='DEPOSIT').length);
    edit('상품·조건 검색','존재하지않는상품');expect(screen.queryAllByTestId('discovery-card')).toHaveLength(0);
    await userEvent.click(screen.getByRole('button',{name:'검색 조건 지우고 전체 보기'}));expect(screen.getAllByTestId('discovery-card')).toHaveLength(prepared.catalog.products.length);
  });
  it('uses an explicit fit-only switch without hiding all other products by default',async()=>{
    renderExplorer(<ProductExplorer/>);await apply('500000');await userEvent.click(screen.getByRole('checkbox',{name:'금액·기간 비교 가능만'}));
    const cards=screen.getAllByTestId('discovery-card');expect(cards.length).toBeGreaterThan(4);expect(cards.every(c=>c.querySelector('.code-fit,.code-partial'))).toBe(true);
  });
  it('provides at most three comparison alternatives and no joint budget allocation',async()=>{
    render(<ProductExplorer/>);const boxes=screen.getAllByRole('checkbox',{name:/비교 선택$/});
    for(const b of boxes.slice(0,3))await userEvent.click(b);
    expect(boxes[3]).toBeDisabled();expect(screen.getByRole('heading',{name:'선택한 상품 나란히 비교'})).toBeVisible();
    expect(screen.getByText(/동시에 같은 예산을 중복 배분한 결과가 아닙니다/)).toBeVisible();
    await userEvent.click(screen.getByRole('button',{name:'비교 선택 지우기'}));expect(boxes[3]).toBeEnabled();
  });
  it('shows dated official sources and avoids fabricated rate or maturity numbers',async()=>{
    renderExplorer(<ProductExplorer/>);const c=within(card('HANA-RICH'));await userEvent.click(c.getByText('가입 대상·우대조건·공식 근거 자세히'));
    expect(c.getByText(/현재 적용 금리는 은행 공식 페이지/)).toBeVisible();expect(c.getByRole('link',{name:/부자씨 적금 상품 안내/})).toHaveAttribute('href',expect.stringContaining('kebhana.com'));
    expect(screen.queryByTestId('savings-maturity')).not.toBeInTheDocument();
  });
  it('suppresses positive comparisons after the immutable review window',async()=>{
    vi.setSystemTime(new Date('2026-11-08T03:00:00Z'));renderExplorer(<ProductExplorer/>);await apply();edit('표시 개수','0');
    expect(document.querySelector('.code-fit')).not.toBeInTheDocument();expect(document.querySelector('.code-partial')).not.toBeInTheDocument();expect(screen.getAllByTestId('discovery-card')).toHaveLength(prepared.catalog.products.length);
  });
  it('prefills only the Python-provided budget and uses Python What-if values',async()=>{
    renderExplorer(<ProductExplorer monthlyAmount={300000} termMonths={12} afterAmount={500000}/>);expect(screen.getByLabelText('매월 저축할 금액')).toHaveValue('300,000');
    await userEvent.click(screen.getByRole('button',{name:/What-if 변경 후 저축 상한 500,000원으로 보기/}));expect(screen.getByLabelText('매월 저축할 금액')).toHaveValue('500,000');
    expect(within(card('KBANK-CODEK-SAVINGS')).getByText('일부 금액으로 비교 가능')).toBeVisible();expect(fetch).not.toHaveBeenCalled();
  });
  it('reads the prepared table at the exact cap boundary rather than deriving a new formula',()=>{
    const p=prepared.catalog.products.find(p=>p.product_id==='KB-CLEAR-SKY')!;
    expect(readPreparedDecision(p,1000000,12,'2026-11-03')).toBe('FIT');expect(readPreparedDecision(p,1000001,12,'2026-11-03')).toBe('PARTIAL');expect(readPreparedDecision(p,10000,13,'2026-11-03')).toBe('TERM');
  });
});
