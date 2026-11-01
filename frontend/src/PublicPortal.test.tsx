import {render,screen,fireEvent,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
vi.hoisted(()=>vi.stubEnv('VITE_PUBLIC_BACKEND_PENDING','true'));
vi.mock('./RegionalPrograms',()=>({default:()=> <h2>공식 청년 지원사업</h2>}));
import App from './App';

beforeEach(()=>{window.history.replaceState(null,'','/#/');vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('Public product inputs must stay local');}));});
afterEach(()=>vi.useRealTimers());
describe('coherent free public site',()=>{
  it('links the home to usable condition search without dead budget or alert menus',async()=>{
    render(<App/>);const nav=within(screen.getByRole('navigation',{name:'주요 메뉴'}));
    expect(nav.queryByRole('link',{name:'생활비 계산'})).not.toBeInTheDocument();expect(nav.queryByRole('link',{name:'모집 알림'})).not.toBeInTheDocument();
    expect(screen.getByRole('link',{name:'내 조건에 맞는 지원 찾기'})).toHaveAttribute('href','#/programs');
    const action=screen.getByRole('link',{name:'내 조건에 맞는 지원 찾기'});expect(document.querySelector('.home-copy')!.lastElementChild).toBe(action);
    await userEvent.click(action);expect(await screen.findByRole('heading',{name:'공식 청년 지원사업'})).toBeVisible();
    await userEvent.click(nav.getByRole('link',{name:'상품 찾기'}));expect(screen.getAllByTestId('discovery-card')).toHaveLength(12);
    fireEvent.change(screen.getByLabelText('매월 저축할 금액'),{target:{value:'500000'}});await userEvent.click(screen.getByRole('button',{name:'내 조건으로 비교'}));
    expect(document.querySelectorAll('.code-fit,.code-partial').length).toBeGreaterThan(4);expect(fetch).not.toHaveBeenCalled();
    expect(screen.queryByText('기존 계산 검증 자료 · 일반 상품 추천 아님')).not.toBeInTheDocument();
  });
  it('redirects an old disabled budget link to product search',()=>{
    window.history.replaceState(null,'','/#input-heading');render(<App/>);expect(screen.getByRole('heading',{level:1,name:'내 조건에 맞는 상품 찾기'})).toBeVisible();expect(screen.queryByLabelText('월세')).not.toBeInTheDocument();
  });
  it('redirects the old notification link to an honest guide with no pending-server advertisement',async()=>{
    window.history.replaceState(null,'','/#asset-alerts');render(<App/>);
    expect(screen.queryByText('계산·알림 서버 연결 준비 중')).not.toBeInTheDocument();
    await userEvent.click(screen.getByText('새 모집이나 금리는 자동으로 알려주나요?'));
    expect(screen.getByText(/현재 공개 사이트에는 자동 갱신·브라우저 알림·이메일 구독이 없습니다/)).toBeVisible();expect(screen.queryByRole('button',{name:/테스트 알림/})).not.toBeInTheDocument();
  });
});
