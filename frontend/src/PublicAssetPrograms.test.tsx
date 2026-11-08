import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,describe,it,expect,vi} from 'vitest';
vi.hoisted(()=>vi.stubEnv('VITE_PUBLIC_BACKEND_PENDING','true'));
import AssetPrograms from './AssetPrograms';
import fixture from './testing/asset-programs-fixture.json';
beforeEach(()=>vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>fixture.public}))));

describe('public government information scope',()=>{
  it('does not advertise a profile recommendation link that routes to bank-only discovery',async()=>{
    render(<AssetPrograms goalMonths={null}/>);await screen.findByTestId('asset-programs-result');
    expect(screen.queryByRole('link',{name:'내 조건으로 찾아보기 →'})).not.toBeInTheDocument();
    expect(screen.getByRole('searchbox',{name:'지원사업 검색'})).toBeVisible();
    // The public snapshot is bundled (no network), so the page also works where it is not served from the site root.
    expect(fetch).not.toHaveBeenCalled();
    expect(document.querySelectorAll('[data-asset-id]').length).toBe(3);
    await userEvent.click(screen.getByRole('button',{name:'나머지 7개 사업 더 보기'}));expect(document.querySelectorAll('[data-asset-id]').length).toBe(10);
  });
  it('labels recruitment by verification date and offers no subscription action',async()=>{
    render(<AssetPrograms goalMonths={null}/>);await screen.findByTestId('asset-programs-result');
    expect(screen.getByText('확인일의 모집 안내')).toBeVisible();await userEvent.click(screen.getByText('자료 갱신과 모집 알림 안내'));
    expect(screen.getByText(/목록 다시 불러오기는 새 모집을 실시간 수집하는 동작이 아닙니다/)).toBeVisible();
    expect(screen.queryByRole('button',{name:/구독|테스트 알림/})).not.toBeInTheDocument();
  });
});
