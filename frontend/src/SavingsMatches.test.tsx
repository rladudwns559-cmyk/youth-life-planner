vi.mock('./AssetAlerts',()=>({default:()=>null}));
vi.mock('./AssetPrograms',()=>({default:()=>null}));
import {act,fireEvent,render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {describe,it,expect,vi} from 'vitest';
import SavingsMatches from './SavingsMatches';
import App from './App';
import baselineFixture from './testing/comparison-fixture.json';
import matchingFixture from './testing/savings-matching-fixture.json';
import type {SimulationResult} from './api';
import {requestSavingsMatches,type SavingsMatchesResponse,type MatchingScenario} from './savings-matching-api';

const baseline=baselineFixture.before as SimulationResult;
const after=baselineFixture.after as SimulationResult;
const fixture=()=>structuredClone(matchingFixture) as SavingsMatchesResponse & {after_example:MatchingScenario};
const reply=(data:unknown)=>({ok:true,json:async()=>data});
function setup(months:number|null=12){const fetcher=vi.fn().mockResolvedValue(reply(fixture()));vi.stubGlobal('fetch',fetcher);const view=render(<SavingsMatches baseline={baseline} termMonths={months}/>);return {fetcher,view};}

describe('official savings automatic amount/term matching',()=>{
  it('waits for an explicit goal period without sending a request',()=>{
    const {fetcher}=setup(null);expect(fetcher).not.toHaveBeenCalled();expect(screen.getByRole('link',{name:'목표 기간 입력하기 →'})).toHaveAttribute('href','#saving-period');
  });
  it('automatically displays all matched banks and separates basic/conditional rates',async()=>{
    const {fetcher}=setup();const result=await screen.findByTestId('savings-matches-result');
    expect(within(result).getByText('4개 조건 일치 / 4개 확인')).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'카카오뱅크 자유적금'})).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'토스뱅크 자유적금'})).toBeInTheDocument();
    expect(screen.getByText('3.85%')).toBeInTheDocument();expect(screen.getByText('4.05%')).toBeInTheDocument();expect(screen.getByText('별도 우대금리 미반영 · 세전')).toBeInTheDocument();
    expect(screen.getAllByText(/가입 자격·우대조건은 별도 확인/)).toHaveLength(4);
    expect(fetcher).toHaveBeenCalledTimes(1);
    const [url,options]=fetcher.mock.calls[0];expect(url).toBe('/api/financial-products/match');expect(options.cache).toBe('no-store');
    expect(JSON.parse(options.body)).toEqual({profile:baseline.input_summary,term_months:12});
    expect(JSON.parse(options.body)).not.toHaveProperty('monthly_amount');
  });
  it('provides official links with source dates and does not invent maturity values',async()=>{
    setup();await screen.findByTestId('savings-matches-result');
    expect(screen.getAllByRole('link',{name:/공식 상품 보기/})).toHaveLength(4);
    expect(screen.getAllByText(/자료 확인 2026-10-30/)).toHaveLength(4);
    expect(screen.getByText(/실제 만기금액은 계산하지 않습니다/)).toBeInTheDocument();
    expect(screen.queryByTestId('savings-maturity')).not.toBeInTheDocument();
  });
  it('automatically compares the after budget and explains excluded products',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(reply({...fixture(),after:matchingFixture.after_example,changes:{added:[],removed:['KBANK-CODEK-SAVINGS'],retained:[]}})));
    render(<SavingsMatches baseline={baseline} after={after} termMonths={12}/>);await screen.findByTestId('savings-matches-result');
    await userEvent.click(screen.getByRole('button',{name:'변경 후 예산 기준'}));
    expect(screen.getByText('3개 조건 일치 / 4개 확인')).toBeInTheDocument();
    expect(screen.getByText(/변경 후 조건과 맞지 않는 상품: 코드K 자유적금/)).toBeInTheDocument();
    expect(screen.getByText('금액·기간이 맞지 않는 상품 1개 보기')).toBeInTheDocument();
  });
  it('shows zero savings as a distinct no-match state',async()=>{
    const data=fixture();data.current={...data.current,monthly_amount:0,matches:[],matched_count:0,excluded_count:4};
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(reply(data)));render(<SavingsMatches baseline={baseline} termMonths={12}/>);
    expect(await screen.findByText('현재 저축 투입 상한이 0원이에요.')).toBeInTheDocument();
  });
  it('keeps stale or unknown-source products out of matched cards',async()=>{
    const data=fixture();data.current.review_required=data.current.matches.map(r=>({...r,reasons:['공식 자료를 다시 확인해야 하는 시점입니다.'],reason_codes:['SOURCE_REVIEW_REQUIRED']}));
    data.current.matches=[];data.current.matched_count=0;data.current.review_count=4;
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(reply(data)));render(<SavingsMatches baseline={baseline} termMonths={12}/>);
    expect(await screen.findByText('자료 재확인 필요 4개')).toBeInTheDocument();expect(screen.queryByRole('link',{name:/공식 상품 보기/})).not.toBeInTheDocument();
  });
  it('offers retry after a failed catalog request',async()=>{
    const fetcher=vi.fn().mockResolvedValueOnce({ok:false,status:503}).mockResolvedValueOnce(reply(fixture()));vi.stubGlobal('fetch',fetcher);
    render(<SavingsMatches baseline={baseline} termMonths={12}/>);expect(await screen.findByRole('alert')).toHaveTextContent('불러오지 못했습니다');
    await userEvent.click(screen.getByRole('button',{name:'적금 다시 조회'}));expect(await screen.findByTestId('savings-matches-result')).toBeInTheDocument();
  });
  it.each([{},null,{...matchingFixture,current:{}}])('rejects malformed matching response',async(data)=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(reply(data)));await expect(requestSavingsMatches(baseline.input_summary,12,null,new AbortController().signal)).rejects.toThrow('응답 형식');
  });
  it('rejects a response for the wrong goal period',async()=>{
    const data=fixture();data.current.term_months=6;vi.stubGlobal('fetch',vi.fn().mockResolvedValue(reply(data)));
    await expect(requestSavingsMatches(baseline.input_summary,12,null,new AbortController().signal)).rejects.toThrow('응답 형식');
  });
  it('ignores a late previous-period response',async()=>{
    let resolve!:(v:unknown)=>void;
    const next=fixture();next.current.term_months=6;next.current.matches=next.current.matches.slice(0,1);next.current.matched_count=1;
    vi.stubGlobal('fetch',vi.fn().mockReturnValueOnce(new Promise(r=>{resolve=r;})).mockResolvedValueOnce(reply(next)));
    const view=render(<SavingsMatches baseline={baseline} termMonths={12}/>);view.rerender(<SavingsMatches baseline={baseline} termMonths={6}/>);
    await screen.findByText('1개 조건 일치 / 4개 확인');await act(async()=>resolve(reply(fixture())));
    expect(screen.queryByText('4개 조건 일치 / 4개 확인')).not.toBeInTheDocument();
  });
  it('clears results when the period is removed',async()=>{
    const {view}=setup();await screen.findByTestId('savings-matches-result');view.rerender(<SavingsMatches baseline={baseline} termMonths={null}/>);
    expect(screen.queryByTestId('savings-matches-result')).not.toBeInTheDocument();expect(screen.getByText('얼마 동안 모으고 싶으세요?')).toBeInTheDocument();
  });
  it('preserves the screen deadline without retrying automatically',async()=>{
    vi.useFakeTimers();
    try{
      const fetcher=vi.fn().mockImplementation((_url,options)=>new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError')))));
      vi.stubGlobal('fetch',fetcher);render(<SavingsMatches baseline={baseline} termMonths={12}/>);
      await act(async()=>{await vi.advanceTimersByTimeAsync(10001);});
      expect(screen.getByRole('alert')).toHaveTextContent('조회 시간이 초과');expect(fetcher).toHaveBeenCalledTimes(1);
    }finally{vi.useRealTimers();}
  });
  it('integrates goal input without changing the policy/cashflow profile',async()=>{
    const fetcher=vi.fn().mockImplementation((url)=>Promise.resolve(reply(String(url).endsWith('/match')?fixture():baseline)));
    vi.stubGlobal('fetch',fetcher);renderBudgetApp();
    fireEvent.change(screen.getByLabelText(/목표 저축 기간/),{target:{value:'12'}});
    await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));await screen.findByTestId('disposable');await go('savings');await screen.findByTestId('savings-matches-result');
    const simulation=JSON.parse(fetcher.mock.calls[0][1].body);expect(simulation).not.toHaveProperty('term_months');
    expect(fetcher.mock.calls[1][0]).toBe('/api/financial-products/match');
  });
  it('does not query on an invalid goal and preserves the base calculation',async()=>{
    const fetcher=vi.fn().mockResolvedValue(reply(baseline));vi.stubGlobal('fetch',fetcher);renderBudgetApp();
    fireEvent.change(screen.getByLabelText(/목표 저축 기간/),{target:{value:'1.5'}});
    await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));await screen.findByTestId('disposable');
    expect(fetcher).toHaveBeenCalledTimes(1);expect(screen.getByText('기간은 1~120 사이의 정수로 입력해 주세요.')).toBeInTheDocument();
  });
});

function renderBudgetApp(){window.history.replaceState(null,'','/#/budget');return render(<App/>);}
async function go(page:string){await userEvent.click(screen.getByRole('navigation',{name:'주요 메뉴'}).querySelector(`a[href="#/${page}"]`)!);if(page==='savings')await userEvent.click(screen.getByText('기존 계산 검증 자료 · 일반 상품 추천 아님'));}
