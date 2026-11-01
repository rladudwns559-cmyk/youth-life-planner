import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {render,screen,within,fireEvent} from '@testing-library/react';
import RegionalPrograms from './RegionalPrograms';

beforeEach(()=>{vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T03:00:00Z'));});
afterEach(()=>vi.useRealTimers());
function choose(label:string,value:string){
  fireEvent.change(screen.getByLabelText(label),{target:{value}});
}
function firstTitle(){return within(screen.getAllByRole('article')[0]).getByRole('heading',{level:3}).textContent;}

it('puts a newly covered district ahead of broader open notices, even if broader notices match more profile fields',()=>{
  render(<RegionalPrograms/>);
  choose('관심·거주 광역지역','서울');choose('시·군·구','도봉구');choose('현재 만 나이','23');
  const first=firstTitle();
  expect(first).toMatch(/도봉|NCS/);
  expect(screen.getByRole('status',{name:'도봉구 공고 요약'})).toHaveTextContent(/도봉구 대상 공고 \d+건.*공식 접수 중.*\d+건/);
  fireEvent.click(screen.getByRole('button',{name:'내 조건으로 찾기 →'}));
  const dialog=within(screen.getByRole('dialog'));
  expect(within(dialog.getAllByRole('article')[0]).getByRole('heading',{level:3})).toHaveTextContent(first!);
  fireEvent.click(dialog.getByRole('button',{name:'결과 창 닫기'}));
  choose('시·군·구','강남구');
  expect(firstTitle()).not.toEqual(first);
});

it('hides an open local notice when its explicit age criterion fails',()=>{
  render(<RegionalPrograms/>);choose('관심·거주 광역지역','인천');choose('시·군·구','옹진군');
  choose('현재 취업 상태','unemployed');choose('현재 만 나이','25');
  expect(firstTitle()).toMatch(/자격증/);
  expect(within(screen.getAllByRole('article')[0]).getByText('지원자격 추가 확인 필요')).toBeVisible();
  const firstLocal=firstTitle();
  choose('현재 만 나이','65');
  expect(screen.queryAllByRole('heading',{level:3}).some(h=>h.textContent===firstLocal)).toBe(false);
});

