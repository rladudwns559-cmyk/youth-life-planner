vi.mock('./AssetAlerts',()=>({default:()=>null}));
vi.mock('./AssetPrograms',()=>({default:()=>null}));
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import WhatIf from './WhatIf';
import App from './App';
import fixture from './testing/comparison-fixture.json';
import type { SimulationResult } from './api';
import { compare, ComparisonApiError, type ComparisonResult } from './comparison-api';

const baseline=fixture.before as SimulationResult;
const output=fixture as ComparisonResult;
const response=(value:unknown=output)=>({ok:true,json:async()=>value});
async function open() {
  render(<WhatIf baseline={baseline}/>);
  await userEvent.click(screen.getByRole('button',{name:'현재 상황으로 비교 시작'}));
}
const run=()=>userEvent.click(screen.getByRole('button',{name:'Before / After 비교하기'}));
function mockFetch() {const fetcher=vi.fn().mockResolvedValue(response());vi.stubGlobal('fetch',fetcher);return fetcher;}
function changes() {
  fireEvent.change(screen.getByLabelText('변경 월 생활비 소득'),{target:{value:'1800000'}});
  fireEvent.change(screen.getByLabelText('변경 월세'),{target:{value:'550000'}});
  fireEvent.change(screen.getByLabelText('변경 사용자 저축 상한',{exact:false}),{target:{value:'500000'}});
  fireEvent.change(screen.getByLabelText('변경 취업 상태'),{target:{value:'employed'}});
}

describe('What-if actual input path',()=>{
  it('starts from current values without sending HTTP until submitted',async()=>{
    const fetcher=mockFetch();await open();
    expect(screen.getByLabelText('변경 월 생활비 소득')).toHaveValue('1,500,000');
    expect(screen.getByLabelText('변경 월세')).toHaveValue('450,000');
    expect(screen.getByLabelText('변경 사용자 저축 상한',{exact:false})).toHaveValue('300,000');
    expect(screen.getByLabelText('변경 취업 상태')).toHaveValue('unemployed');
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('supports four simultaneous changes and preserves independent Before input',async()=>{
    const fetcher=mockFetch();await open();changes();await run();
    await screen.findByTestId('comparison-result');
    const [url,options]=fetcher.mock.calls[0];const request=JSON.parse(options.body);
    expect(url).toBe('/api/synthetic/compare');expect(options.method).toBe('POST');
    expect(request.before).toEqual(baseline.input_summary);
    expect(request.after).toEqual(output.after.input_summary);
    expect(request.before.student_status).toBe(true);expect(request.after.student_status).toBe(true);
    expect(request.after).not.toHaveProperty('household_income');
    expect(request.after).not.toHaveProperty('monthly_policy_cash_benefit');
  });
  it('permits unchanged comparison',async()=>{
    const fetcher=mockFetch();await open();await run();await screen.findByTestId('comparison-result');
    const request=JSON.parse(fetcher.mock.calls[0][1].body);expect(request.before).toEqual(request.after);
  });
  it('permits a single change',async()=>{
    const fetcher=mockFetch();await open();fireEvent.change(screen.getByLabelText('변경 월세'),{target:{value:'0'}});
    await run();await screen.findByTestId('comparison-result');
    expect(JSON.parse(fetcher.mock.calls[0][1].body).after).toEqual({...baseline.input_summary,monthly_rent:0});
  });
  it('renders server numeric deltas, transitions and UNKNOWN facts',async()=>{
    mockFetch();await open();changes();await run();
    expect(await screen.findByTestId('disposable-delta')).toHaveTextContent('+200,000원');
    expect(screen.getByTestId('savable-delta')).toHaveTextContent('+200,000원');
    const second=screen.getByText('합성 테스트 002').closest('article')!;
    expect(within(second).getByText('PASS')).toBeInTheDocument();expect(within(second).getByText('FAIL')).toBeInTheDocument();
    expect(within(second).getByText(/취업상태 입력이 미취업에서 취업/,{selector:'p.transition-explanation'})).toBeInTheDocument();
    expect(screen.getByText(/SAMPLE-003: 현재 정책 기준의 가구소득/)).toBeInTheDocument();
    expect(screen.getByText(/월 여유자금이 200,000원 증가/)).toBeInTheDocument();
    expect(screen.getByText(/합성 데이터 비교입니다/)).toBeInTheDocument();
  });
  it('displays server delta without recomputing it in React',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({...output,numeric_deltas:{...output.numeric_deltas,disposable_after_policy:123456}})));
    await open();await run();expect(await screen.findByTestId('disposable-delta')).toHaveTextContent('+123,456원');
  });
  it('resets only After values and clears comparison',async()=>{
    const fetcher=mockFetch();await open();changes();await run();await screen.findByTestId('comparison-result');
    await userEvent.click(screen.getByRole('button',{name:'현재 값으로 다시 설정'}));
    expect(screen.queryByTestId('comparison-result')).not.toBeInTheDocument();
    expect(screen.getByLabelText('변경 월세')).toHaveValue('450,000');
    expect(screen.getByLabelText('변경 취업 상태')).toHaveValue('unemployed');
    await run();await screen.findByTestId('comparison-result');const request=JSON.parse(fetcher.mock.calls[1][1].body);
    expect(request.before).toEqual(baseline.input_summary);expect(request.after).toEqual(request.before);
  });
  it.each(['-1','1.5','1_000','1e6','1000000000001'])('rejects invalid After money %s',async(value)=>{
    const fetcher=mockFetch();await open();fireEvent.change(screen.getByLabelText('변경 월세'),{target:{value}});await run();
    expect(screen.getByRole('alert')).toHaveTextContent('입력 오류');expect(fetcher).not.toHaveBeenCalled();
  });
  it('distinguishes blank savings cap and zero and independently edits student status',async()=>{
    const fetcher=mockFetch();await open();
    fireEvent.change(screen.getByLabelText('변경 사용자 저축 상한',{exact:false}),{target:{value:''}});await run();await screen.findByTestId('comparison-result');
    expect(JSON.parse(fetcher.mock.calls[0][1].body).after.user_savings_capacity).toBeNull();
    await userEvent.click(screen.getByText('나이·지역·재학·그 외 지출도 변경하기'));
    fireEvent.change(screen.getByLabelText('변경 재학 상태'),{target:{value:'false'}});
    fireEvent.change(screen.getByLabelText('변경 사용자 저축 상한',{exact:false}),{target:{value:'0'}});await run();await screen.findByTestId('comparison-result');
    expect(JSON.parse(fetcher.mock.calls[1][1].body).after).toMatchObject({user_savings_capacity:0,student_status:false,employment_status:'unemployed'});
  });
  it('clears stale comparison on input change',async()=>{
    mockFetch();await open();await run();await screen.findByTestId('comparison-result');
    fireEvent.change(screen.getByLabelText('변경 월세'),{target:{value:'0'}});
    expect(screen.queryByTestId('comparison-result')).not.toBeInTheDocument();
  });
  it('shows negative cashflow and negative deltas as normal results',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({...output,after:{...output.after,cashflow:{...output.after.cashflow,disposable_after_policy:-900000,savable_amount:0}},numeric_deltas:{...output.numeric_deltas,disposable_after_policy:-1400000,savable_amount:-300000}})));
    await open();await run();expect(await screen.findByTestId('disposable-delta')).toHaveTextContent('-1,400,000원');
    expect(screen.getByText('-900,000원')).toBeInTheDocument();expect(screen.getByText(/적자는 정상적인 계산 결과/)).toBeInTheDocument();expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
  it.each([[422,'입력 오류'],[500,'서버 오류']])('distinguishes HTTP %s errors',async(status,label)=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status}));await open();await run();
    expect(await screen.findByRole('alert')).toHaveTextContent(String(label));expect(screen.queryByTestId('comparison-result')).not.toBeInTheDocument();
  });
  it('shows a network error and retries',async()=>{
    const fetcher=vi.fn().mockRejectedValueOnce(new TypeError('fetch failed')).mockResolvedValueOnce(response());vi.stubGlobal('fetch',fetcher);
    await open();await run();expect(await screen.findByRole('alert')).toHaveTextContent('네트워크 오류');
    await userEvent.click(screen.getByRole('button',{name:'비교 다시 시도'}));expect(await screen.findByTestId('comparison-result')).toBeInTheDocument();
  });
  it('cancels a previous request and ignores its late result',async()=>{
    const pending:{resolve:(x:unknown)=>void;signal:AbortSignal}[]=[];
    vi.stubGlobal('fetch',vi.fn().mockImplementation((_url,options)=>new Promise(resolve=>pending.push({resolve,signal:options.signal}))));
    await open();await run();expect(screen.getByRole('status')).toHaveTextContent('각각 계산');
    fireEvent.change(screen.getByLabelText('변경 월세'),{target:{value:'550000'}});expect(pending[0].signal.aborted).toBe(true);await run();
    await act(async()=>pending[1].resolve(response()));expect(await screen.findByTestId('disposable-delta')).toHaveTextContent('+200,000원');
    await act(async()=>pending[0].resolve(response({...output,numeric_deltas:{...output.numeric_deltas,disposable_after_policy:999}})));
    expect(screen.getByTestId('disposable-delta')).toHaveTextContent('+200,000원');
  });
  it('clears a pending request on reset and ignores late failure',async()=>{
    let reject!:(error:Error)=>void;
    vi.stubGlobal('fetch',vi.fn().mockReturnValue(new Promise((_resolve,r)=>{reject=r;})));await open();await run();
    await userEvent.click(screen.getByRole('button',{name:'현재 값으로 다시 설정'}));await act(async()=>reject(new TypeError('late failure')));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();expect(screen.queryByTestId('comparison-result')).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Before / After 비교하기'})).toBeEnabled();
  });
  it('shows a timeout separately and releases the submit button',async()=>{
    await open();vi.useFakeTimers();
    vi.stubGlobal('fetch',vi.fn().mockImplementation((_url,options)=>new Promise((_resolve,reject)=>{
      options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')));
    })));
    try {
      fireEvent.click(screen.getByRole('button',{name:'Before / After 비교하기'}));
      await act(async()=>{vi.advanceTimersByTime(10000);});
      expect(screen.getByRole('alert')).toHaveTextContent('요청 시간 초과');
      expect(screen.getByRole('button',{name:'Before / After 비교하기'})).toBeEnabled();
    } finally {vi.useRealTimers();}
  });
  it('integrates with M3.0 and closes comparison when current input changes',async()=>{
    const fetcher=vi.fn().mockResolvedValueOnce(response(baseline)).mockResolvedValueOnce(response());vi.stubGlobal('fetch',fetcher);renderBudgetApp();
    await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));await screen.findByTestId('disposable');
    await userEvent.click(screen.getByRole('button',{name:'현재 상황으로 비교 시작'}));changes();await run();await screen.findByTestId('comparison-result');
    fireEvent.change(screen.getByLabelText('월세',{exact:true}),{target:{value:'600000'}});
    expect(screen.queryByTestId('comparison-result')).not.toBeInTheDocument();expect(screen.queryByLabelText('변경 월세')).not.toBeInTheDocument();
    expect(screen.queryByTestId('disposable')).not.toBeInTheDocument();
  });
  it('handles an invalid server JSON response',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>{throw new SyntaxError();}}));
    await expect(compare(baseline.input_summary,output.after.input_summary)).rejects.toBeInstanceOf(ComparisonApiError);
  });
  it('provides a semantic four-column comparison table for responsive rendering',async()=>{
    mockFetch();await open();await run();await screen.findByTestId('comparison-result');
    const table=screen.getByRole('table',{name:'월 예산 Before After 변화량 비교'});
    expect(within(table).getAllByRole('columnheader')).toHaveLength(4);
    expect(within(table).getByRole('rowheader',{name:'월 여유자금'})).toBeInTheDocument();
  });
});

function renderBudgetApp(){window.history.replaceState(null,'','/#/budget');return render(<App/>);}
