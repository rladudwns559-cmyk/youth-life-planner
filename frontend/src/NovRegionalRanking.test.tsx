import {render,screen,fireEvent} from '@testing-library/react';
import {beforeEach,afterEach,it,vi,expect} from 'vitest';
import RegionalPrograms from './RegionalPrograms';
import cases from './testing/nov-gap-cases.json';

beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T12:00:00Z'));});
afterEach(()=>vi.useRealTimers());
it.each(cases)('prioritises an open, best-matching local notice for $province $city in both views',c=>{
  const {rerender}=render(<RegionalPrograms browse={false}/>);
  const change=(name:string,value:string|number)=>fireEvent.change(screen.getByLabelText(name),{target:{value}});
  change('관심·거주 광역지역',c.province);change('시·군·구',c.city);change('현재 만 나이',c.age);
  change('현재 취업 상태',c.employment);change('현재 월세 거주 여부','yes');
  fireEvent.click(screen.getByRole('button',{name:/내 조건으로 찾기/}));
  const first=screen.getByRole('dialog').querySelector('article')!;
  const title=first.querySelector('h3')!.textContent;
  expect(first).toHaveTextContent('공식 접수중 확인');expect(first).toHaveTextContent('추가 확인');
  fireEvent.click(screen.getByRole('button',{name:'결과 창 닫기'}));
  rerender(<RegionalPrograms browse listPage/>);
  const card=document.querySelector('[data-support-id]')!;
  expect(c.allowed).toContain(card.getAttribute('data-support-id'));
  expect(card.querySelector('h3')!.textContent).toBe(title);
  expect(card).toHaveTextContent('지원자격 추가 확인 필요');
});
