vi.mock('./AssetAlerts',()=>({default:()=>null}));
vi.mock('./AssetPrograms',()=>({default:()=>null}));
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import { defaults, parseForm } from './form';

const response = {
  synthetic: true, test_only: true, dataset_version: 'synthetic-v1', evaluation_date: '2026-10-20',
  input_summary: parseForm(defaults).input,
  policies: ['PASS','FAIL','UNKNOWN'].map((status,i) => ({
    policy_id: `SAMPLE-00${i+1}`, policy_name:`합성 테스트 00${i+1}`,overall_status:status,
    display_status:['이용 가능성 높음','현재 조건과 맞지 않음','추가 확인 필요'][i],
    missing_fields:i===2?['household_income']:[],rule_results:i===2?[{
      rule_id:'S003-INCOME',status:'UNKNOWN',reason_code:'MISSING_FIELD',evaluated_value:null,
      expected_condition:{field:'household_income',operator:'lte',value:3000000},missing_fields:['household_income'],evidence_refs:['data/synthetic/README.md#sample-003'],
    }]:[],
  })),
  cashflow:{monthly_income:1500000,total_monthly_income:1500000,total_monthly_expenses:1000000,disposable_after_policy:500000,savable_amount:300000,policy_benefit_applied:0},
};
function mockFetch() {
  const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>response});
  vi.stubGlobal('fetch',fetcher);
  return fetcher;
}

describe('form contract',()=>{
  it.each(['-1','1.5','1_000','1e6','1000000000001','','Infinity'])('rejects invalid money %s',(value)=>{
    expect(parseForm({...defaults,monthly_income:value}).input).toBeUndefined();
  });
  it('distinguishes blank optional values and zero',()=>{
    expect(parseForm({...defaults,age:'',region:'',employment_status:'',student_status:'',user_savings_capacity:''}).input).toMatchObject({age:null,region:null,employment_status:null,student_status:null,user_savings_capacity:null});
    expect(parseForm({...defaults,user_savings_capacity:'0'}).input?.user_savings_capacity).toBe(0);
  });
});
describe('working screen',()=>{
  it('does not send information before submission',()=>{
    const fetcher=mockFetch();renderBudgetApp();expect(fetcher).not.toHaveBeenCalled();
    expect(screen.getByText('공식 정보 · 계산 시연')).toBeInTheDocument();
  });
  it('validates input before HTTP',async()=>{
    const fetcher=mockFetch();renderBudgetApp();
    fireEvent.change(screen.getByLabelText('월세'),{target:{value:'-5'}});
    await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));
    expect(screen.getByRole('alert')).toHaveTextContent('입력값을 확인');
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('sends the independent profile and renders statuses, missing info and cashflow',async()=>{
    const fetcher=mockFetch();renderBudgetApp();
    await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));
    expect(await screen.findByTestId('disposable')).toHaveTextContent('500,000원');
    expect(screen.getByTestId('savable')).toHaveTextContent('300,000원');
    for(const status of ['PASS','FAIL','UNKNOWN']) expect(screen.getByText(status)).toBeInTheDocument();
    expect(screen.getByText(/추가 확인: 정책 기준의 가구소득/)).toBeInTheDocument();
    const [url,options]=fetcher.mock.calls[0];
    expect(url).toBe('/api/synthetic/simulate');
    expect(JSON.parse(options.body)).toEqual(parseForm(defaults).input);
    expect(JSON.parse(options.body)).not.toHaveProperty('household_income');
    expect(JSON.parse(options.body)).not.toHaveProperty('monthly_policy_cash_benefit');
  });
  it('clears stale results when input changes',async()=>{
    mockFetch();renderBudgetApp();await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));
    await screen.findByTestId('disposable');
    fireEvent.change(screen.getByLabelText('월세'),{target:{value:'500000'}});
    expect(screen.queryByTestId('disposable')).not.toBeInTheDocument();
  });
  it('renders negative amounts without zero-clamping',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({...response,cashflow:{...response.cashflow,disposable_after_policy:-900000,savable_amount:0}})}));
    renderBudgetApp();await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));
    expect(await screen.findByTestId('disposable')).toHaveTextContent('-900,000원');
    expect(screen.getByTestId('savable')).toHaveTextContent('0원');
  });
  it('shows network failure and retries',async()=>{
    const fetcher=vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValueOnce({ok:true,json:async()=>response});
    vi.stubGlobal('fetch',fetcher);renderBudgetApp();
    await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('계산 서버에 연결하지 못했습니다');
    await userEvent.click(screen.getByRole('button',{name:'다시 시도'}));
    expect(await screen.findByTestId('disposable')).toHaveTextContent('500,000원');
  });
  it('shows server input errors',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:422}));renderBudgetApp();
    await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('입력 형식과 범위');
  });
  it('disables repeated submission during calculation',async()=>{
    let resolve!:(value:unknown)=>void;
    vi.stubGlobal('fetch',vi.fn().mockReturnValue(new Promise(r=>{resolve=r;})));renderBudgetApp();
    await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));
    expect(screen.getByRole('button',{name:'계산하고 있어요…'})).toBeDisabled();
    resolve({ok:true,json:async()=>response});
    await waitFor(()=>expect(screen.getByTestId('disposable')).toBeInTheDocument());
  });
});

function renderBudgetApp(){window.history.replaceState(null,'','/#/budget');return render(<App/>);}
