vi.mock('./AssetAlerts',()=>({default:()=>null}));
vi.mock('./AssetPrograms',()=>({default:()=>null}));
import {act,fireEvent,render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {describe,expect,it,vi} from 'vitest';
import ProductComparisonPanel from './ProductComparisonPanel';
import App from './App';
import baselineFixture from './testing/comparison-fixture.json';
import catalog from './testing/products-fixture.json';
import comparison from './testing/products-comparison-fixture.json';
import type {SimulationResult} from './api';
const baseline=baselineFixture.before as SimulationResult;
const response=(value:unknown)=>({ok:true,json:async()=>value});
function setup(){const fetcher=vi.fn().mockImplementation((url)=>Promise.resolve(response(String(url).endsWith('/compare')?comparison:catalog)));vi.stubGlobal('fetch',fetcher);const view=render(<ProductComparisonPanel baseline={baseline}/>);return {fetcher,view};}
async function open(){await userEvent.click(screen.getByRole('button',{name:'공식 상품 목록 불러오기'}));await screen.findByText('공식 정보 3개 · 계산 가정 대응 0개');}
const run=()=>userEvent.click(screen.getByRole('button',{name:'선택한 상품 조건 비교하기'}));
const edit=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});

describe('official snapshot comparison',()=>{
  it('does not automatically send economic inputs or request a catalog',()=>{const {fetcher}=setup();expect(fetcher).not.toHaveBeenCalled();});
  it('lists three real historical products with distinct dates, rates and sources',async()=>{
    const {fetcher}=setup();await open();expect(screen.getAllByRole('checkbox')).toHaveLength(3);
    for(const product of catalog.products)expect(screen.getByRole('checkbox',{name:product.product_name})).toBeChecked();
    expect(screen.getAllByText(/기준일 2025-12-31 · 확인일 2026-10-25/)).toHaveLength(3);
    expect(screen.getByText('기본 연 2.50%')).toBeInTheDocument();expect(screen.getByText('우대 포함 최고 연 4.70%')).toBeInTheDocument();
    expect(screen.getAllByText('자료가 오래됨')).toHaveLength(3);expect(screen.getAllByText('현재 가입 상태 미확인')).toHaveLength(3);
    expect(screen.getAllByRole('link',{name:/공식 자료 · 중소기업은행/})).toHaveLength(3);
    expect(screen.getAllByRole('link',{name:/이용 조건: 이용허락범위 제한 없음/})).toHaveLength(3);
    expect(screen.getByText(/개별 상품 상세 링크 미확인/)).toBeInTheDocument();
    expect(fetcher.mock.calls[0][0]).toBe('/api/financial-products');expect(fetcher.mock.calls[0][1].body).toBeUndefined();
  });
  it('sends selected IDs, current profile and exact contribution without a rate override',async()=>{
    const {fetcher}=setup();await open();await userEvent.click(screen.getByRole('checkbox',{name:'IBK모으기통장'}));
    edit('상품 비교 월 납입액','400000');await run();await screen.findByTestId('product-comparison-result');
    const request=JSON.parse(fetcher.mock.calls[1][1].body);
    expect(request).toEqual({profile:baseline.input_summary,monthly_payment:400000,term_months:12,product_ids:['IBK-WORKER-SAVINGS','IBK-DDAY-SAVINGS']});
    expect(fetcher.mock.calls[1][0]).toBe('/api/financial-products/compare');
  });
  it('shows no maturity number or invented zero for incompatible products',async()=>{
    setup();await open();await run();const result=await screen.findByTestId('product-comparison-result');
    expect(within(result).getByText(/실제 계산 0개/)).toBeInTheDocument();
    expect(within(result).getAllByText('총 납입원금·세전이자·만기금액: 계산하지 않음')).toHaveLength(3);
    expect(within(result).getAllByText(/자유적립식 또는 적립방식 미확인/)).toHaveLength(3);
    expect(within(result).getByText(/금리·만기금액 순위를 만들지 않습니다/)).toBeInTheDocument();
    expect(within(result).queryByText('2,439,000원')).not.toBeInTheDocument();
    expect(within(result).getByText(/최대 월 납입액을 초과/)).toBeInTheDocument();
  });
  it('renders server-supplied calculated fields only for a synthetic supported-contract response',async()=>{
    const {fetcher}=setup();await open();
    fetcher.mockResolvedValueOnce(response({...comparison,information_count:1,calculated_count:1,results:[{...comparison.results[0],product:{...comparison.results[0].product,product_name:'합성 호환 계약 시험 전용'},calculation_supported:true,reasons:[],calculation:{total_principal_krw:111,estimated_interest_before_tax_krw:222,estimated_maturity_before_tax_krw:333}}]}));
    await run();const result=await screen.findByTestId('product-comparison-result');
    expect(within(result).getByText('111원')).toBeInTheDocument();expect(within(result).getByText('222원')).toBeInTheDocument();expect(within(result).getByText('333원')).toBeInTheDocument();
  });
  it('preserves unknown rates and never displays them as 0%',async()=>{
    const {fetcher}=setup();fetcher.mockResolvedValueOnce(response({...catalog,products:[{...catalog.products[0],rate_options:[{...catalog.products[0].rate_options[0],base_rate_percent:null,max_total_rate_percent:null}]}]}));
    await open();expect(screen.getByText('기본 연 미확인')).toBeInTheDocument();expect(screen.getByText('우대 포함 최고 연 미확인')).toBeInTheDocument();
  });
  it('links previous and changed budget after existing What-if and clears stale results on change',async()=>{
    const {fetcher,view}=setup();await open();view.rerender(<ProductComparisonPanel baseline={baseline} after={baselineFixture.after as SimulationResult}/>);
    edit('상품 비교 월 납입액','400000');await run();const result=await screen.findByTestId('product-comparison-result');
    expect(JSON.parse(fetcher.mock.calls[1][1].body).after_profile).toEqual(baselineFixture.after.input_summary);
    expect(within(result).getByText('What-if 변경 후 월 예산')).toBeInTheDocument();
    expect(within(result).getByText(/상한보다 100,000원 큽니다/)).toBeInTheDocument();
    view.rerender(<ProductComparisonPanel baseline={baseline}/>);expect(screen.queryByTestId('product-comparison-result')).not.toBeInTheDocument();
  });
  it.each(['상품 비교 월 납입액','상품 비교 기간'])('blocks blank %s',async(label)=>{const {fetcher}=setup();await open();edit(label,'');await run();expect(screen.getByRole('alert')).toHaveTextContent('모두 입력');expect(fetcher).toHaveBeenCalledTimes(1);});
  it.each([['상품 비교 월 납입액','-1'],['상품 비교 월 납입액','1_000'],['상품 비교 월 납입액','1000000000001'],['상품 비교 기간','0'],['상품 비교 기간','1.5'],['상품 비교 기간','121']])('blocks invalid %s: %s',async(label,value)=>{
    const {fetcher}=setup();await open();edit(label,value);await run();expect(screen.getByRole('alert')).toHaveTextContent('정수');expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('requires a product selection',async()=>{const {fetcher}=setup();await open();for(const box of screen.getAllByRole('checkbox'))await userEvent.click(box);await run();expect(screen.getByRole('alert')).toHaveTextContent('하나 이상');expect(fetcher).toHaveBeenCalledTimes(1);});
  it('can retry a catalog server error',async()=>{const {fetcher}=setup();fetcher.mockResolvedValueOnce({ok:false,status:503});await userEvent.click(screen.getByRole('button',{name:'공식 상품 목록 불러오기'}));expect(await screen.findByRole('alert')).toHaveTextContent('불러오지 못했습니다');await open();});
  it('handles catalog network failure separately',async()=>{const {fetcher}=setup();fetcher.mockRejectedValueOnce(new TypeError('network'));await userEvent.click(screen.getByRole('button',{name:'공식 상품 목록 불러오기'}));expect(await screen.findByRole('alert')).toHaveTextContent('연결하지 못했습니다');});
  it.each([422,503])('shows comparison HTTP error %s and retries',async(status)=>{const {fetcher}=setup();await open();fetcher.mockResolvedValueOnce({ok:false,status});await run();expect(await screen.findByRole('alert')).toHaveTextContent(status===422?'상품 선택':'불러오지 못했습니다');await run();expect(await screen.findByTestId('product-comparison-result')).toBeInTheDocument();});
  it('shows comparison network failure',async()=>{const {fetcher}=setup();await open();fetcher.mockRejectedValueOnce(new TypeError('network'));await run();expect(await screen.findByRole('alert')).toHaveTextContent('연결하지 못했습니다');});
  it('shows malformed JSON as server error',async()=>{const {fetcher}=setup();await open();fetcher.mockResolvedValueOnce({ok:true,json:async()=>{throw new SyntaxError('JSON');}});await run();expect(await screen.findByRole('alert')).toHaveTextContent('불러오지 못했습니다');});
  it('disables duplicate submission, aborts edit and ignores late response',async()=>{
    const {fetcher}=setup();await open();let resolve!:(value:unknown)=>void;fetcher.mockReturnValueOnce(new Promise(r=>{resolve=r;}));await run();
    expect(screen.getByRole('button',{name:'공식 상품 비교 중…'})).toBeDisabled();expect(screen.getByRole('status')).toHaveTextContent('비교');
    edit('상품 비교 기간','24');expect(fetcher.mock.calls[1][1].signal.aborted).toBe(true);await act(async()=>resolve(response(comparison)));
    expect(screen.queryByTestId('product-comparison-result')).not.toBeInTheDocument();
  });
  it('clears result on product selection changes',async()=>{setup();await open();await run();await screen.findByTestId('product-comparison-result');await userEvent.click(screen.getByRole('checkbox',{name:'IBK모으기통장'}));expect(screen.queryByTestId('product-comparison-result')).not.toBeInTheDocument();});
  it('aborts a slow comparison and reports timeout',async()=>{
    const {fetcher}=setup();await open();fetcher.mockImplementationOnce((_url,options)=>new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('abort','AbortError')))));
    vi.useFakeTimers();try{fireEvent.submit(screen.getByRole('button',{name:'선택한 상품 조건 비교하기'}).closest('form')!);await act(async()=>vi.advanceTimersByTimeAsync(10000));expect(screen.getByRole('alert')).toHaveTextContent('응답 시간이 초과');}finally{vi.useRealTimers();}
  });
  it('aborts requests on unmount',async()=>{const {fetcher,view}=setup();await open();view.unmount();expect(fetcher.mock.calls[0][1].signal.aborted).toBe(true);});
  it('integrates existing What-if result into product comparison without recalculating budgets in React',async()=>{
    const fetcher=vi.fn().mockImplementation(url=>Promise.resolve(response(String(url)==='/api/synthetic/simulate'?baseline:String(url)==='/api/synthetic/compare'?baselineFixture:String(url).endsWith('/compare')?comparison:catalog)));vi.stubGlobal('fetch',fetcher);renderBudgetApp();
    await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));await screen.findByTestId('disposable');
    await userEvent.click(screen.getByRole('button',{name:'현재 상황으로 비교 시작'}));edit('변경 월 생활비 소득','1800000');
    await userEvent.click(screen.getByRole('button',{name:'Before / After 비교하기'}));await screen.findByTestId('comparison-result');await go('savings');await userEvent.click(screen.getByText('이전 IBK 상품 자료 비교 · 2025년 기준'));await open();await run();await screen.findByTestId('product-comparison-result');
    const call=fetcher.mock.calls.find(([url])=>url==='/api/financial-products/compare');expect(JSON.parse(call![1].body).after_profile).toEqual(baselineFixture.after.input_summary);
    await go('budget');edit('변경 월세','600000');expect(screen.queryByTestId('product-comparison-result')).not.toBeInTheDocument();
  });
});

function renderBudgetApp(){window.history.replaceState(null,'','/#/budget');return render(<App/>);}
async function go(page:string){await userEvent.click(screen.getByRole('navigation',{name:'주요 메뉴'}).querySelector(`a[href="#/${page}"]`)!);if(page==='savings')await userEvent.click(screen.getByText('기존 계산 검증 자료 · 일반 상품 추천 아님'));}
