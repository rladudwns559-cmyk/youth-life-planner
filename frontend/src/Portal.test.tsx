import {act,fireEvent,render,screen,within,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import App from './App';
import {resolveRoute} from './portal-routing';
import fixture from './testing/comparison-fixture.json';
vi.mock('./RegionalPrograms',()=>({default:()=> <h2>지원사업 목록</h2>}));
vi.mock('./AssetAlerts',()=>({default:()=> <h2>내 관심 알림</h2>}));
vi.mock('./ProductExplorer',()=>({default:()=> <h2>공식 상품 목록</h2>}));
vi.mock('./SavingsMatches',()=>({default:()=> <h2>적금 후보 목록</h2>}));
vi.mock('./SavingsPanel',()=>({default:()=> <h2>가상 적금 계산</h2>}));
vi.mock('./ProductComparisonPanel',()=>({default:()=> <h2>지난 상품 자료</h2>}));
let animate:ReturnType<typeof vi.fn>,cancel:ReturnType<typeof vi.fn>;
const original=HTMLElement.prototype.animate;
beforeEach(()=>{
  window.history.replaceState(null,'','/#/');localStorage.clear();cancel=vi.fn();animate=vi.fn(()=>({cancel}));
  Object.defineProperty(HTMLElement.prototype,'animate',{configurable:true,writable:true,value:animate});
  vi.stubGlobal('matchMedia',vi.fn(()=>({matches:false})));
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>fixture.before})));
});
afterEach(()=>{Object.defineProperty(HTMLElement.prototype,'animate',{configurable:true,writable:true,value:original});});
async function go(name:string){await userEvent.click(within(screen.getByRole('navigation',{name:'주요 메뉴'})).getByRole('link',{name}));}
describe('separate portal pages and motion',()=>{
  it('keeps the home clean and ends the copy with the budget entry',()=>{
    render(<App/>);expect(screen.getByRole('heading',{level:1})).toHaveTextContent('나에게 필요한 지원');
    expect(screen.queryByLabelText('월세')).not.toBeInTheDocument();expect(screen.queryByText('지원사업 목록')).not.toBeInTheDocument();expect(screen.queryByText('근거를 알고, 내 선택에 활용하세요.')).not.toBeInTheDocument();
    expect(screen.queryByRole('contentinfo')).not.toBeInTheDocument();expect(fetch).not.toHaveBeenCalled();
    expect(document.querySelector('.home-copy')!.lastElementChild).toBe(screen.getByRole('link',{name:'내 생활비 계산하기'}));
  });
  it.each([['청년 지원사업','나에게 필요한 청년 지원'],['생활비 계산','나의 경제생활 진단'],['상품 찾기','내 조건에 맞는 상품 찾기'],['이용 안내','근거를 알고, 내 선택에 활용하세요.']])('opens %s in its own view',async(name,title)=>{
    render(<App/>);await go(name);expect(await screen.findByRole('heading',{level:1,name:title})).toBeVisible();
    expect(document.querySelectorAll('[data-portal-page]:not([hidden])')).toHaveLength(1);
  });
  it('uses the budget CTA without a scrolling one-page form',async()=>{
    render(<App/>);await userEvent.click(screen.getByRole('link',{name:'내 생활비 계산하기'}));await screen.findByLabelText('월세');
    expect(window.location.hash).toBe('#/budget');expect(screen.queryByRole('heading',{level:1,name:/나에게 필요한 지원/})).not.toBeInTheDocument();
  });
  it('retains inputs in memory across menu visits without saving income',async()=>{
    render(<App/>);await go('생활비 계산');fireEvent.change(await screen.findByLabelText('월세'),{target:{value:'610000'}});
    fireEvent.change(screen.getByLabelText(/거주 지역/),{target:{value:'부산광역시'}});
    await go('청년 지원사업');await screen.findByRole('heading',{name:'지원사업 목록'});await go('생활비 계산');
    expect(screen.getByLabelText('월세')).toHaveValue('610,000');expect(screen.getByLabelText(/거주 지역/)).toHaveValue('부산광역시');expect(Object.keys(localStorage)).toEqual([]);
  });
  it('retains server results when returning from home and savings',async()=>{
    render(<App/>);await go('생활비 계산');await userEvent.click(await screen.findByRole('button',{name:'내 상황으로 계산하기'}));await screen.findByTestId('disposable');
    const text=screen.getByTestId('disposable').textContent;await go('상품 찾기');await screen.findByRole('heading',{name:'공식 상품 목록'});
    await userEvent.click(screen.getByRole('link',{name:'청년 경제생활 의사결정 시뮬레이터 홈'}));await screen.findByRole('heading',{level:1,name:/나에게 필요한 지원/});
    expect(screen.getByTestId('disposable')).not.toBeVisible();await go('생활비 계산');expect(screen.getByTestId('disposable')).toBeVisible();expect(screen.getByTestId('disposable').textContent).toBe(text);
  });
  it('shows a useful savings entry before a profile has been calculated',async()=>{
    render(<App/>);await go('상품 찾기');expect(await screen.findByRole('heading',{name:'공식 상품 목록'})).toBeVisible();
    expect(screen.queryByRole('link',{name:'생활비 계산으로 이동 →'})).not.toBeInTheDocument();expect(fetch).not.toHaveBeenCalled();
  });
  it('animates pointer page entries using only opacity and transform',async()=>{
    render(<App/>);animate.mockClear();await go('이용 안내');await screen.findByRole('heading',{name:'근거를 알고, 내 선택에 활용하세요.'});
    expect(animate).toHaveBeenCalled();const [frames,options]=animate.mock.lastCall!;expect(options.duration).toBe(220);expect(options.easing).toBe('cubic-bezier(0.23, 1, 0.32, 1)');
    expect(Object.keys(frames[0]).sort()).toEqual(['opacity','transform']);
  });
  it('cancels prior motion on rapid navigation and leaves only the final view active',async()=>{
    render(<App/>);await go('생활비 계산');await go('상품 찾기');await go('청년 지원사업');await screen.findByRole('heading',{name:'지원사업 목록'});
    expect(cancel.mock.calls.length).toBeGreaterThanOrEqual(2);expect(document.querySelector('[data-portal-page]:not([hidden])')).toHaveAttribute('data-portal-page','programs');
  });
  it('uses a gentle opacity-only transition for reduced motion',async()=>{
    vi.stubGlobal('matchMedia',vi.fn(()=>({matches:true})));render(<App/>);await go('생활비 계산');await screen.findByLabelText('월세');
    const [frames,options]=animate.mock.lastCall!;expect(options.duration).toBe(150);expect(frames.every((f:object)=>!('transform' in f))).toBe(true);
  });
  it('does not animate keyboard navigation',async()=>{
    render(<App/>);animate.mockClear();fireEvent.keyDown(window,{key:'Enter'});fireEvent.click(within(screen.getByRole('navigation',{name:'주요 메뉴'})).getByRole('link',{name:'생활비 계산'}));
    await screen.findByLabelText('월세');expect(animate).not.toHaveBeenCalled();
  });
  it('restores the active page on history navigation events',async()=>{
    render(<App/>);await go('생활비 계산');fireEvent.change(await screen.findByLabelText('월세'),{target:{value:'580000'}});await go('이용 안내');
    await act(async()=>{window.history.replaceState(null,'','/#/budget');window.dispatchEvent(new HashChangeEvent('hashchange'));});
    expect(await screen.findByLabelText('월세')).toHaveValue('580,000');
  });
  it('does not create duplicate page heading identifiers after visiting every section',async()=>{
    render(<App/>);for(const name of ['생활비 계산','청년 지원사업','상품 찾기','이용 안내'])await go(name);
    await screen.findByRole('heading',{name:'근거를 알고, 내 선택에 활용하세요.'});const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);expect(new Set(ids).size).toBe(ids.length);
  });
  it.each([['#asset-alerts','guide'],['#asset-programs','programs'],['#input-heading','budget'],['#result-heading','budget'],['#saving-period','budget'],['#service-guide','guide'],['#main','home'],['#/bad','home']])('preserves legacy link %s',async(hash,page)=>{
    window.history.replaceState(null,'','/'+hash);render(<App/>);await waitFor(()=>expect(document.querySelector('[data-portal-page]:not([hidden])')).toHaveAttribute('data-portal-page',page));
  });
  it('does not route an in-page skip target back to home',async()=>{
    render(<App/>);await go('생활비 계산');fireEvent.click(screen.getByRole('link',{name:'본문으로 바로가기'}));await waitFor(()=>expect(window.location.hash).toBe('#portal-budget-title'));
    expect(screen.getByRole('heading',{level:1,name:'나의 경제생활 진단'})).toBeVisible();
  });
  it('resolves unknown routes safely',()=>{expect(resolveRoute('#/not-a-real-page')).toBe('home');});
});
