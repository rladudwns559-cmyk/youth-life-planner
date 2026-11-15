import {render, screen, fireEvent, within, waitFor} from '@testing-library/react';
import {expect,it,vi,afterEach} from 'vitest';
import App from './App';
vi.hoisted(()=>vi.stubEnv('VITE_PUBLIC_BACKEND_PENDING','true'));
afterEach(()=>vi.useRealTimers());

it('separates the catalog from matching and carries the profile into the list and back',async()=>{
  vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T06:00:00Z'));
  window.history.replaceState(null,'','/#/programs');render(<App/>);
  expect(screen.queryByRole('button',{name:'전체 분야'})).toBeNull();
  fireEvent.change(screen.getByLabelText('관심·거주 광역지역'),{target:{value:'강원'}});
  fireEvent.change(screen.getByLabelText('시·군·구'),{target:{value:'횡성군'}});
  fireEvent.change(screen.getByLabelText('현재 만 나이'),{target:{value:'25'}});
  fireEvent.click(screen.getByRole('button',{name:/내 조건으로 찾기/}));
  const dialog=screen.getByRole('dialog');
  expect(within(dialog).getAllByRole('article')[0]).toHaveTextContent('횡성군 청년센터 · 11월 손뜨개 교실');
  fireEvent.click(within(dialog).getByRole('button',{name:'결과 창 닫기'}));
  fireEvent.click(screen.getByRole('link',{name:'청년지원사업 보기'}));
  await screen.findByRole('button',{name:'전체 분야'});
  expect(screen.getAllByRole('article')[0]).toHaveAttribute('data-support-id','NOV-HOENGSEONG-KNITTING-2026');
  fireEvent.click(screen.getByRole('link',{name:/지역·조건 변경/}));
  await waitFor(()=>expect(screen.getByLabelText('시·군·구')).toHaveValue('횡성군'));
  expect(screen.getByLabelText('현재 만 나이')).toHaveValue(25);
  fireEvent.change(screen.getByLabelText('현재 만 나이'),{target:{value:'65'}});
  fireEvent.click(screen.getByRole('button',{name:/내 조건으로 찾기/}));
  const results=screen.getByRole('dialog');
  for(const row of results.querySelectorAll('article.finder-row'))expect(row).not.toHaveTextContent('횡성군 청년센터 · 11월 손뜨개 교실');
  // the age-mismatched program is only named in the collapsed "why it was dropped" list
  expect(results.querySelector('details.finder-excluded')).toHaveTextContent('횡성군 청년센터 · 11월 손뜨개 교실');
});
