import { render, screen, fireEvent, within } from '@testing-library/react';
import { beforeEach, afterEach, it, vi, expect } from 'vitest';
import RegionalPrograms from './RegionalPrograms';
const exam='서귀포시 취업준비 청년 자격증·어학시험 응시료';
const change=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T12:00:00Z'));});
afterEach(()=>vi.useRealTimers());
it('re-ranks for a change in employment and does not infer household type from rent',()=>{
  render(<RegionalPrograms browse={false}/>);
  change('관심·거주 광역지역','제주');change('시·군·구','서귀포시');change('모집 상태','OPEN');change('현재 만 나이','25');change('현재 월세 거주 여부','yes');
  change('현재 취업 상태','unemployed');
  const open=()=>{fireEvent.click(screen.getByRole('button',{name:/내 조건으로 찾기/}));return within(screen.getByRole('dialog'));};
  const a=open();expect(a.getAllByRole('article')[0].querySelector('h3')?.textContent).toBe(exam);
  fireEvent.click(a.getByRole('button',{name:'결과 창 닫기'}));change('현재 취업 상태','employed');
  const b=open();expect(b.queryByRole('heading',{name:exam})).toBeNull();
  const meal=b.getByRole('heading',{name:/서귀포시 1인가구 식생활 교육/}).closest('article')!;
  expect(meal).toHaveTextContent('1인가구 해당 여부');expect(meal).toHaveTextContent('월세 추가 확인');
});

