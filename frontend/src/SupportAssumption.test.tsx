import {render,screen,fireEvent,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
vi.hoisted(()=>vi.stubEnv('VITE_PUBLIC_BACKEND_PENDING','true'));
vi.mock('./RegionalPrograms',()=>({default:()=> <h2>공식 청년 지원사업</h2>}));
import App from './App';
import {calculateCashflow} from './cashflow';
import {assumeSupport} from './support-assumption';

const fill=(prefix:string,values:Record<string,string>)=>{for(const [key,value] of Object.entries(values))fireEvent.change(document.getElementById(`${prefix}-${key}`)!,{target:{value}});};
const base={monthly_income:'1500000',monthly_rent:'450000',monthly_fixed_expenses:'200000',other_monthly_expenses:'350000'};
const cash=(over:Partial<Parameters<typeof calculateCashflow>[0]>={})=>calculateCashflow({monthly_income:1_500_000,monthly_rent:450_000,monthly_fixed_expenses:200_000,other_monthly_expenses:350_000,user_savings_capacity:null,...over});

beforeEach(()=>{window.history.replaceState(null,'','/#/budget');vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-14T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('Unexpected network');}));});
afterEach(()=>vi.useRealTimers());

describe('assumeSupport',()=>{
  it('adds the assumed support on top of the real result without changing it',()=>{
    const real=cash();
    const a=assumeSupport(real,200_000,12);
    expect(real.policy_benefit_applied).toBe(0);
    expect(real.disposable_after_policy).toBe(500_000);
    expect(a).toMatchObject({disposable_now:500_000,disposable_assumed:700_000,savable_now:500_000,savable_assumed:700_000,monthly_gain:200_000,total_gain:2_400_000,capped:false});
  });
  it('keeps the savings limit and reports the part it held back',()=>{
    const a=assumeSupport(cash({user_savings_capacity:600_000}),200_000,12);
    expect(a).toMatchObject({savable_now:500_000,savable_assumed:600_000,monthly_gain:100_000,total_gain:1_200_000,capped:true});
  });
  it('fills a deficit first, so savings grow only by what is left',()=>{
    const a=assumeSupport(cash({monthly_income:900_000}),200_000,6);  // −100,000 a month now
    expect(a).toMatchObject({disposable_now:-100_000,disposable_assumed:100_000,savable_now:0,savable_assumed:100_000,monthly_gain:100_000,total_gain:600_000});
  });
  it('rejects amounts or periods outside the allowed range',()=>{
    expect(()=>assumeSupport(cash(),-1,12)).toThrow('INVALID_SUPPORT');
    expect(()=>assumeSupport(cash(),1.5,12)).toThrow('INVALID_SUPPORT');
    expect(()=>assumeSupport(cash(),100_000,0)).toThrow('INVALID_MONTHS');
    expect(()=>assumeSupport(cash(),100_000,61)).toThrow('INVALID_MONTHS');
  });
});

it('shows the assumption beside the real result and leaves product search on the real amount',async()=>{
  render(<App/>);fill('budget',base);
  await userEvent.click(screen.getByRole('button',{name:/여유자금 계산하기/}));
  const box=screen.getByRole('region',{name:'지원을 받는다고 가정하면?'});
  expect(within(box).queryByRole('table')).toBeNull();
  await userEvent.click(within(box).getByRole('button',{name:'월 20만원'}));
  expect(within(box).getByRole('button',{name:'월 20만원'})).toHaveAttribute('aria-pressed','true');
  const table=within(box).getByRole('table');
  expect(within(table).getByRole('row',{name:/한 달 여유자금/})).toHaveTextContent('+500,000원+700,000원+200,000원');
  expect(within(table).getByRole('row',{name:/저축에 쓸 수 있는 금액/})).toHaveTextContent('500,000원700,000원+200,000원');
  expect(within(box).getByText('총 2,400,000원')).toBeVisible();
  fireEvent.change(within(box).getByLabelText('받는 기간'),{target:{value:'6'}});
  expect(within(box).getByText('총 1,200,000원')).toBeVisible();
  // The real result and the product hand-off are untouched.
  expect(screen.getByTestId('public-disposable')).toHaveTextContent('+500,000원');
  expect(screen.getByRole('link',{name:/월 500,000원으로 상품 찾기/})).toBeVisible();
});

it('asks for a valid amount and period instead of guessing',async()=>{
  render(<App/>);fill('budget',base);
  await userEvent.click(screen.getByRole('button',{name:/여유자금 계산하기/}));
  const box=screen.getByRole('region',{name:'지원을 받는다고 가정하면?'});
  fireEvent.change(within(box).getByLabelText('매달 받는 지원금 (가정)'),{target:{value:'abc'}});
  expect(within(box).getByText('1원~1억 원 사이의 원 단위 정수로 넣어 주세요.')).toBeVisible();
  fireEvent.change(within(box).getByLabelText('매달 받는 지원금 (가정)'),{target:{value:'100000'}});
  fireEvent.change(within(box).getByLabelText('받는 기간'),{target:{value:'0'}});
  expect(within(box).getByText('1~60개월로 넣어 주세요.')).toBeVisible();
  expect(within(box).queryByRole('table')).toBeNull();
});
