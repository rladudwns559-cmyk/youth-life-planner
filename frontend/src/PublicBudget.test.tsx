import {render,screen,fireEvent,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
vi.hoisted(()=>vi.stubEnv('VITE_PUBLIC_BACKEND_PENDING','true'));
vi.mock('./RegionalPrograms',()=>({default:()=> <h2>공식 청년 지원사업</h2>}));
import App from './App';

const fill=(prefix:string,values:Record<string,string>)=>{for(const [key,value] of Object.entries(values))fireEvent.change(document.getElementById(`${prefix}-${key}`)!,{target:{value}});};
const base={monthly_income:'1500000',monthly_rent:'450000',monthly_fixed_expenses:'200000',other_monthly_expenses:'350000'};

beforeEach(()=>{window.history.replaceState(null,'','/#/budget');vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-03T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('Public budget inputs must stay local');}));});
afterEach(()=>vi.useRealTimers());

describe('public budget and what-if',()=>{
  it('calculates the monthly room to save in the browser and hands it to product search',async()=>{
    render(<App/>);fill('budget',base);
    await userEvent.click(screen.getByRole('button',{name:/여유자금 계산하기/}));
    expect(screen.getByTestId('public-disposable')).toHaveTextContent('+500,000원');
    expect(screen.getByTestId('public-savable')).toHaveTextContent('500,000원');
    expect(screen.getByText(/정책 지원금은 자동으로 더하지 않아요/)).toBeVisible();
    await userEvent.click(screen.getByRole('link',{name:/월 500,000원으로 상품 찾기/}));
    expect(await screen.findByLabelText('매월 저축할 금액')).toHaveValue('500,000');
    expect(fetch).not.toHaveBeenCalled();
  });
  it('compares a changed condition with the current one using the same calculation',async()=>{
    render(<App/>);fill('budget',{...base,user_savings_capacity:'300000'});
    await userEvent.click(screen.getByRole('button',{name:/여유자금 계산하기/}));
    expect(screen.getByTestId('public-savable')).toHaveTextContent('300,000원');
    await userEvent.click(screen.getByRole('button',{name:'월세 20만원 줄면'}));
    expect(document.getElementById('whatif-monthly_rent')).toHaveValue('250,000');
    fill('whatif',{user_savings_capacity:''});
    await userEvent.click(screen.getByRole('button',{name:/바꿔서 비교하기/}));
    const table=within(screen.getByTestId('public-budget-compare'));
    const row=(name:string)=>within(table.getByRole('row',{name:new RegExp(name)})).getAllByRole('cell').map(cell=>cell.textContent);
    expect(row('지출 합계')).toEqual(['1,000,000원','800,000원','−200,000원']);
    expect(row('한 달 여유자금')).toEqual(['500,000원','700,000원','+200,000원']);
    expect(row('저축에 쓸 수 있는 금액')).toEqual(['300,000원','700,000원','+400,000원']);
    expect(fetch).not.toHaveBeenCalled();
  });
  it('shows a deficit as a deficit and does not send zero to product search',async()=>{
    render(<App/>);fill('budget',{monthly_income:'1000000',monthly_rent:'700000',monthly_fixed_expenses:'300000',other_monthly_expenses:'200000'});
    await userEvent.click(screen.getByRole('button',{name:/여유자금 계산하기/}));
    expect(screen.getByTestId('public-disposable')).toHaveTextContent('−200,000원');
    expect(screen.getByTestId('public-savable')).toHaveTextContent('0원');
    expect(screen.queryByRole('link',{name:/으로 상품 찾기/})).not.toBeInTheDocument();
  });
  it('asks for missing or invalid amounts instead of guessing',async()=>{
    render(<App/>);fill('budget',{monthly_income:'1500000',monthly_rent:'45만원'});
    await userEvent.click(screen.getByRole('button',{name:/여유자금 계산하기/}));
    expect(screen.queryByTestId('public-budget-result')).not.toBeInTheDocument();
    expect(screen.getByText(/월세은\(는\) 0 이상의 원 단위 정수/)).toBeVisible();
    expect(screen.getByText(/월 고정지출을\(를\) 입력해 주세요/)).toBeVisible();
  });
  it('clears an old result when an input changes',async()=>{
    render(<App/>);fill('budget',base);
    await userEvent.click(screen.getByRole('button',{name:/여유자금 계산하기/}));
    fill('budget',{monthly_rent:'500000'});
    expect(screen.queryByTestId('public-budget-result')).not.toBeInTheDocument();
  });
});
