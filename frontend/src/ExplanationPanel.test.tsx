import {act,fireEvent,render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {describe,it,expect,vi} from 'vitest';
import ExplanationPanel from './ExplanationPanel';
import WhatIf from './WhatIf';
import comparisonFixture from './testing/comparison-fixture.json';
import explanationFixture from './testing/explanation-fixture.json';
import type {ComparisonResult} from './comparison-api';
import {requestExplanation} from './explanation-api';

const comparison=comparisonFixture as ComparisonResult;
const response=(value:unknown=explanationFixture)=>({ok:true,json:async()=>value});
const click=()=>userEvent.click(screen.getByRole('button',{name:'한국어 설명 생성'}));

describe('M3.6 explanation UI and actual HTTP client boundary',()=>{
  it('does not automatically call a model or API',()=>{
    const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher);render(<ExplanationPanel comparison={comparison}/>);
    expect(screen.getByText(/외부 AI로 전송하지 않으며/)).toBeInTheDocument();expect(fetcher).not.toHaveBeenCalled();
  });
  it('posts original profiles only and identifies deterministic fallback',async()=>{
    const fetcher=vi.fn().mockResolvedValue(response());vi.stubGlobal('fetch',fetcher);render(<ExplanationPanel comparison={comparison}/>);await click();
    expect(await screen.findByTestId('explanation-result')).toHaveTextContent('정형 설명으로 대체');
    const [url,options]=fetcher.mock.calls[0];expect(url).toBe('/api/synthetic/explain');expect(options.cache).toBe('no-store');
    expect(JSON.parse(options.body)).toEqual({before:comparison.before.input_summary,after:comparison.after.input_summary,mode:'ai_if_available'});
    expect(screen.getByText('실제 AI 모델이 설정되지 않았습니다. 기존 Python 결과로 작성했습니다.')).toBeInTheDocument();
    expect(screen.getByText(/실제 AI 실행: 아니요/)).toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('shows money reasons, policy transitions, UNKNOWN and next actions',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response()));render(<ExplanationPanel comparison={comparison}/>);await click();
    const output=await screen.findByTestId('explanation-result');
    expect(output).toHaveTextContent('월소득: 1,500,000원 → 1,800,000원');
    expect(output).toHaveTextContent('월세: 450,000원 → 550,000원');
    expect(output).toHaveTextContent('고정지출: 200,000원 → 200,000원');
    expect(output).toHaveTextContent('현재 조건과 맞지 않음');expect(output).toHaveTextContent('정책 기준의 가구소득');
    expect(output).toHaveTextContent('SAMPLE-003');expect(output).toHaveTextContent('실제 정책');
    expect(within(output).getByText(/0원이며 실제 금융상품/)).toBeInTheDocument();
  });
  it('shows loading and leaves the surrounding comparison visible',async()=>{
    let resolve!:(x:unknown)=>void;vi.stubGlobal('fetch',vi.fn().mockReturnValue(new Promise(r=>{resolve=r;})));
    render(<><p>현재 월 여유자금 700,000원</p><ExplanationPanel comparison={comparison}/></>);await click();
    expect(screen.getByRole('status')).toHaveTextContent('위 비교 결과를 계속 확인');
    expect(screen.getByText('현재 월 여유자금 700,000원')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'설명을 준비하고 있어요…'})).toBeDisabled();
    await act(async()=>resolve(response()));expect(await screen.findByTestId('explanation-result')).toBeInTheDocument();
  });
  it('permits one explicit re-request without an automatic retry',async()=>{
    const f=vi.fn().mockResolvedValue(response());vi.stubGlobal('fetch',f);render(<ExplanationPanel comparison={comparison}/>);await click();
    await screen.findByTestId('explanation-result');await userEvent.click(screen.getByRole('button',{name:'설명 다시 생성'}));
    await screen.findByTestId('explanation-result');expect(f).toHaveBeenCalledTimes(2);
  });
  it('distinguishes network error and explicit retry',async()=>{
    const f=vi.fn().mockRejectedValueOnce(new TypeError('fail')).mockResolvedValueOnce(response());vi.stubGlobal('fetch',f);
    render(<ExplanationPanel comparison={comparison}/>);await click();expect(await screen.findByRole('alert')).toHaveTextContent('연결하지 못했습니다');
    expect(f).toHaveBeenCalledTimes(1);await userEvent.click(screen.getByRole('button',{name:'설명 다시 시도'}));await screen.findByTestId('explanation-result');
    expect(f).toHaveBeenCalledTimes(2);
  });
  it.each([[422,'입력의 형식과 범위'],[500,'설명 서버']])('handles HTTP %s',async(status,text)=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status}));render(<ExplanationPanel comparison={comparison}/>);await click();
    expect(await screen.findByRole('alert')).toHaveTextContent(String(text));
  });
  it('rejects malformed JSON responses',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>{throw new Error();}}));
    render(<ExplanationPanel comparison={comparison}/>);await click();expect(await screen.findByRole('alert')).toHaveTextContent('응답을 읽지 못했습니다');
  });
  it('rejects a response missing the explanation contract',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({synthetic:true,document:{summary:'가'}})));
    await expect(requestExplanation(comparison.before.input_summary,comparison.after.input_summary)).rejects.toThrow('형식');
  });
  it('clears old text on a changed comparison and rejects a late success',async()=>{
    const pending:((x:unknown)=>void)[]=[];const signals:AbortSignal[]=[];
    vi.stubGlobal('fetch',vi.fn().mockImplementation((_u,o)=>{signals.push(o.signal);return new Promise(resolve=>pending.push(resolve));}));
    const view=render(<ExplanationPanel comparison={comparison}/>);await click();
    view.rerender(<ExplanationPanel comparison={structuredClone(comparison)}/>);expect(signals[0].aborted).toBe(true);await click();
    await act(async()=>pending[1](response({...explanationFixture,document:{...explanationFixture.document,summary:'최신 설명입니다.'}})));
    expect(await screen.findByText('최신 설명입니다.')).toBeInTheDocument();
    await act(async()=>pending[0](response({...explanationFixture,document:{...explanationFixture.document,summary:'오래된 설명입니다.'}})));
    expect(screen.queryByText('오래된 설명입니다.')).not.toBeInTheDocument();
    view.rerender(<ExplanationPanel comparison={structuredClone(comparison)}/>);expect(screen.queryByTestId('explanation-result')).not.toBeInTheDocument();
  });
  it('ignores late errors after input changed',async()=>{
    let reject!:(e:Error)=>void;vi.stubGlobal('fetch',vi.fn().mockReturnValue(new Promise((_r,j)=>{reject=j;})));
    const view=render(<ExplanationPanel comparison={comparison}/>);await click();view.rerender(<ExplanationPanel comparison={structuredClone(comparison)}/>);
    await act(async()=>reject(new TypeError('old')));expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
  it('aborts on unmount',async()=>{
    let signal!:AbortSignal;vi.stubGlobal('fetch',vi.fn().mockImplementation((_u,o)=>{signal=o.signal;return new Promise(()=>{});}));
    const view=render(<ExplanationPanel comparison={comparison}/>);await click();view.unmount();expect(signal.aborted).toBe(true);
  });
  it('reports timeout separately without erasing existing comparison',async()=>{
    vi.useFakeTimers();try{
      vi.stubGlobal('fetch',vi.fn().mockImplementation((_u,o)=>new Promise((_r,j)=>o.signal.addEventListener('abort',()=>j(new DOMException('Aborted','AbortError'))))));
      render(<ExplanationPanel comparison={comparison}/>);fireEvent.click(screen.getByRole('button',{name:'한국어 설명 생성'}));
      await act(async()=>{await vi.advanceTimersByTimeAsync(12000);});expect(screen.getByRole('alert')).toHaveTextContent('시간이 초과');
      expect(screen.getByRole('button',{name:'설명 다시 시도'})).toBeEnabled();
    }finally{vi.useRealTimers();}
  });
  it('labels generated AI separately (mock metadata, not a real model run)',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({...explanationFixture,explanation_source:'llm',fallback:false,ai_executed:true,ai_success:true})));
    render(<ExplanationPanel comparison={comparison}/>);await click();expect(await screen.findByText('생성형 AI 설명')).toBeInTheDocument();
    expect(screen.queryByText('정형 설명으로 대체')).not.toBeInTheDocument();
  });
  it('renders text as text rather than HTML',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({...explanationFixture,document:{...explanationFixture.document,summary:'<img src=x onerror=alert(1)>'}})));
    render(<ExplanationPanel comparison={comparison}/>);await click();expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeInTheDocument();
    expect(document.querySelector('.explanation-summary img')).toBeNull();
  });
  it('does not label a different dataset version as the displayed comparison',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({...explanationFixture,facts:{...explanationFixture.facts,dataset_version:'other'}})));
    render(<ExplanationPanel comparison={comparison}/>);await click();expect(await screen.findByRole('alert')).toHaveTextContent('다시 비교');
    expect(screen.queryByTestId('explanation-result')).not.toBeInTheDocument();
  });
  it('integrates below What-if and clears explanation on After edit',async()=>{
    const f=vi.fn().mockImplementation(url=>Promise.resolve(response(String(url).includes('/explain')?explanationFixture:comparison)));
    vi.stubGlobal('fetch',f);render(<WhatIf baseline={comparison.before}/>);
    await userEvent.click(screen.getByRole('button',{name:'현재 상황으로 비교 시작'}));
    await userEvent.click(screen.getByRole('button',{name:'Before / After 비교하기'}));await screen.findByTestId('comparison-result');await click();
    await screen.findByTestId('explanation-result');expect(screen.getByTestId('comparison-result')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('변경 월세'),{target:{value:'100000'}});
    expect(screen.queryByTestId('explanation-result')).not.toBeInTheDocument();expect(screen.queryByTestId('comparison-result')).not.toBeInTheDocument();
  });
});
