vi.mock('./AssetAlerts',()=>({default:()=>null}));
vi.mock('./AssetPrograms',()=>({default:()=>null}));
import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import SavingsPanel from './SavingsPanel';
import App from './App';
import fixture from './testing/comparison-fixture.json';
import type { SimulationResult } from './api';
import output from './testing/savings-fixture.json';
import {calculateSavings,SavingsApiError} from './savings-api';

const baseline=fixture.before as SimulationResult;
const response=(value:unknown=output)=>({ok:true,json:async()=>value});
function setup(value:unknown=output){const fetcher=vi.fn().mockResolvedValue(response(value));vi.stubGlobal('fetch',fetcher);render(<SavingsPanel baseline={baseline}/>);return fetcher;}
const run=()=>userEvent.click(screen.getByRole('button',{name:'적금 만기 계산하기'}));
const edit=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});

describe('synthetic recurring savings',()=>{
  it('has explicit assumptions and defaults without automatic HTTP',()=>{
    const fetcher=setup();expect(screen.getByLabelText('적금 월 납입액')).toHaveValue('200,000');
    expect(screen.getByLabelText('적금 기간')).toHaveValue('12');expect(screen.getByLabelText('적금 연 기본금리')).toHaveValue('3');
    expect(screen.getByText(/매월 초 같은 금액 납입/)).toBeInTheDocument();expect(fetcher).not.toHaveBeenCalled();
  });
  it('sends exact API contract and renders all server amounts',async()=>{
    const fetcher=setup();await run();
    expect(await screen.findByTestId('savings-principal')).toHaveTextContent('2,400,000원');
    expect(screen.getByTestId('savings-interest')).toHaveTextContent('39,000원');
    expect(screen.getByTestId('savings-maturity')).toHaveTextContent('2,439,000원');
    const [url,options]=fetcher.mock.calls[0];expect(url).toBe('/api/synthetic/savings/recurring');
    expect(JSON.parse(options.body)).toEqual({profile:baseline.input_summary,monthly_payment:200000,term_months:12,annual_base_rate_percent:'3'});
    expect(options.cache).toBe('no-store');expect(screen.getByText(/총이자를 계산한 뒤 마지막/)).toBeInTheDocument();
    expect(screen.getByText('복리')).toBeInTheDocument();expect(screen.getByText('세후 실수령액')).toBeInTheDocument();
  });
  it('uses server values without a browser interest formula',async()=>{
    setup({...output,total_principal_krw:111,estimated_interest_before_tax_krw:222,estimated_maturity_before_tax_krw:333});await run();
    expect(await screen.findByTestId('savings-principal')).toHaveTextContent('111원');
    expect(screen.getByTestId('savings-interest')).toHaveTextContent('222원');expect(screen.getByTestId('savings-maturity')).toHaveTextContent('333원');
  });
  it('warns over cap but preserves requested contribution',async()=>{
    const fetcher=setup({...output,monthly_payment:400000,budget_comparison:{...output.budget_comparison,exceeds_budget_cap:true,excess_krw:100000,message:'상한보다 100,000원 큽니다. 납입액은 자동으로 줄이지 않았습니다.'}});
    edit('적금 월 납입액','400000');await run();await screen.findByTestId('savings-result');
    expect(screen.getByRole('alert')).toHaveTextContent('저축 투입 상한 초과');
    expect(screen.getByLabelText('적금 월 납입액')).toHaveValue('400,000');expect(JSON.parse(fetcher.mock.calls[0][1].body).monthly_payment).toBe(400000);
  });
  it('shows deficit warning even at zero contribution',async()=>{
    setup({...output,budget_comparison:{...output.budget_comparison,has_deficit:true,exceeds_budget_cap:false,message:'현재 월 예산은 적자이며 저축 투입 상한은 0원입니다.'}});await run();await screen.findByTestId('savings-result');
    expect(screen.getByRole('alert')).toHaveTextContent('현재 월 예산 적자');
  });
  it.each([null,0])('distinguishes baseline cap %s',(cap)=>{
    render(<SavingsPanel baseline={{...baseline,input_summary:{...baseline.input_summary,user_savings_capacity:cap}}}/>);
    expect(screen.getByText(cap===null?/사용자 상한 미지정/:/사용자 상한 0원으로 지정/)).toBeInTheDocument();
  });
  it.each(['적금 월 납입액','적금 기간','적금 연 기본금리'])('blocks empty %s without treating as zero',async(label)=>{
    const fetcher=setup();edit(label,'');await run();expect(screen.getByText('값을 입력해 주세요.')).toBeInTheDocument();expect(fetcher).not.toHaveBeenCalled();
  });
  it.each([['적금 월 납입액','-1'],['적금 월 납입액','1_000'],['적금 월 납입액','1e4'],['적금 월 납입액','1000000000001'],['적금 기간','0'],['적금 기간','1.5'],['적금 기간','121'],['적금 연 기본금리','3.00001'],['적금 연 기본금리','100.0001'],['적금 연 기본금리','NaN']])('blocks invalid %s: %s',async(label,value)=>{
    const fetcher=setup();edit(label,value);await run();expect(screen.getByRole('alert')).toHaveTextContent('적금 입력값');expect(fetcher).not.toHaveBeenCalled();
  });
  it('permits zero contribution and decimal percent string',async()=>{
    const fetcher=setup();edit('적금 월 납입액','0');edit('적금 연 기본금리','3.1250');await run();await screen.findByTestId('savings-result');
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({monthly_payment:0,annual_base_rate_percent:'3.1250'});
  });
  it.each([422,500])('distinguishes HTTP failure %s and can retry',async(status)=>{
    const fetcher=setup();fetcher.mockResolvedValueOnce({ok:false,status});await run();
    expect(await screen.findByRole('alert')).toHaveTextContent(status===422?'입력 형식':'서버에서 오류');
    await run();expect(await screen.findByTestId('savings-result')).toBeInTheDocument();
  });
  it('handles network failure',async()=>{
    const fetcher=setup();fetcher.mockRejectedValueOnce(new TypeError('Failed to fetch'));await run();expect(await screen.findByRole('alert')).toHaveTextContent('연결하지 못했습니다');
  });
  it('classifies malformed JSON as server failure',async()=>{
    const fetcher=setup();fetcher.mockResolvedValueOnce({ok:true,json:async()=>{throw new SyntaxError('broken JSON');}});
    await run();expect(await screen.findByRole('alert')).toHaveTextContent('서버에서 오류');
  });
  it('does not duplicate submission while loading and ignores stale response after edit',async()=>{
    let resolve!:(value:unknown)=>void;const fetcher=setup();fetcher.mockReturnValueOnce(new Promise(r=>{resolve=r;}));await run();
    expect(screen.getByRole('button',{name:'적금 계산 중…'})).toBeDisabled();expect(screen.getByRole('status')).toHaveTextContent('서버에서');
    edit('적금 기간','24');expect(fetcher.mock.calls[0][1].signal.aborted).toBe(true);
    await act(async()=>resolve(response()));expect(screen.queryByTestId('savings-result')).not.toBeInTheDocument();expect(screen.getByLabelText('적금 기간')).toHaveValue('24');
  });
  it('clears old result on editing and aborts on unmount',async()=>{
    const fetcher=vi.fn().mockResolvedValue(response());vi.stubGlobal('fetch',fetcher);const view=render(<SavingsPanel baseline={baseline}/>);
    await run();await screen.findByTestId('savings-result');edit('적금 연 기본금리','4');expect(screen.queryByTestId('savings-result')).not.toBeInTheDocument();
    view.unmount();expect(fetcher.mock.calls[0][1].signal.aborted).toBe(true);
  });
  it('aborts timeout and displays explicit retry message',async()=>{
    setup();const fetcher=vi.mocked(fetch);fetcher.mockImplementationOnce((_url,options)=>new Promise((_resolve,reject)=>{options?.signal?.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError')));}));
    vi.useFakeTimers();
    try {
      fireEvent.submit(screen.getByRole('button',{name:'적금 만기 계산하기'}).closest('form')!);
      await act(async()=>{await vi.advanceTimersByTimeAsync(10000);});
      expect(screen.getByRole('alert')).toHaveTextContent('응답 시간이 초과');
      expect(screen.getByRole('button',{name:'적금 만기 계산하기'})).not.toBeDisabled();
    } finally {vi.useRealTimers();}
  });
  it('integrates into existing current-input flow without an extra automatic request',async()=>{
    const fetcher=vi.fn().mockResolvedValue(response(baseline));vi.stubGlobal('fetch',fetcher);renderBudgetApp();
    expect(screen.queryByLabelText('적금 월 납입액')).not.toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));
    await screen.findByTestId('disposable');expect(screen.getByRole('button',{name:'현재 상황으로 비교 시작'})).toBeInTheDocument();await go('savings');
    expect(await screen.findByLabelText('적금 월 납입액')).toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('API error class retains category',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:422}));
    await expect(calculateSavings({profile:baseline.input_summary,monthly_payment:1,term_months:1,annual_base_rate_percent:'0'})).rejects.toBeInstanceOf(SavingsApiError);
  });
});

function renderBudgetApp(){window.history.replaceState(null,'','/#/budget');return render(<App/>);}
async function go(page:string){await userEvent.click(screen.getByRole('navigation',{name:'주요 메뉴'}).querySelector(`a[href="#/${page}"]`)!);if(page==='savings')await userEvent.click(screen.getByText('기존 계산 검증 자료 · 일반 상품 추천 아님'));}
