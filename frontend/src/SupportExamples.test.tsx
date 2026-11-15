import {render,screen,fireEvent,within,cleanup} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import RegionalPrograms from './RegionalPrograms';
import {HomeSteps} from './HomeExtras';
import {PROFILE_KEY} from './support-profile';
import {SUPPORT_EXAMPLES,exampleFromHash} from './support-examples';
import directory from './public-data/nationwide-districts.json';

const change=(name:string,value:string)=>fireEvent.change(screen.getByLabelText(name),{target:{value}});
const value=(name:string)=>(screen.getByLabelText(name) as HTMLInputElement).value;
beforeEach(()=>{localStorage.clear();window.location.hash='';vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-14T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();window.location.hash='';});

it('uses only real region choices',()=>{
  for(const e of SUPPORT_EXAMPLES)expect((directory.cities as Record<string,string[]>)[e.province]).toContain(e.city);
  expect(exampleFromHash('#/programs?example=ansan')?.id).toBe('ansan');
  expect(exampleFromHash('#/programs?example=nope')).toBeNull();
  expect(exampleFromHash('#/programs')).toBeNull();
});

it('fills the conditions, opens results and marks them as an example',()=>{
  render(<RegionalPrograms browse={false}/>);
  fireEvent.click(screen.getByRole('button',{name:'안산 · 25세 · 구직 중 · 월세'}));
  expect(screen.getByRole('button',{name:'안산 · 25세 · 구직 중 · 월세'})).toHaveAttribute('aria-pressed','true');
  expect(value('관심·거주 광역지역')).toBe('경기');expect(value('시·군·구')).toBe('안산시 단원구');
  expect(value('현재 만 나이')).toBe('25');expect(value('현재 취업 상태')).toBe('unemployed');expect(value('현재 월세 거주 여부')).toBe('yes');
  const dialog=screen.getByRole('dialog');
  expect(within(dialog).getByText('경기 · 안산시 단원구 · 만 25세 · 현재 일하지 않음 · 월세 거주')).toBeVisible();
  expect(screen.getByText(/예시 조건으로 보는 중이에요/)).toBeInTheDocument();
});

it('never overwrites remembered conditions and restores them when the example ends',()=>{
  render(<RegionalPrograms browse={false}/>);
  fireEvent.click(screen.getByLabelText('이 기기에 내 조건 기억하기'));
  change('관심·거주 광역지역','서울');change('현재 만 나이','31');
  const mine=localStorage.getItem(PROFILE_KEY);
  fireEvent.click(screen.getByRole('button',{name:'부산 · 22세 · 대학생 아르바이트 · 월세'}));
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'결과 창 닫기'}));
  expect(localStorage.getItem(PROFILE_KEY)).toBe(mine);
  fireEvent.click(screen.getByRole('button',{name:'예시 끝내기'}));
  expect(value('관심·거주 광역지역')).toBe('서울');expect(value('현재 만 나이')).toBe('31');
  expect(screen.queryByText(/예시 조건으로 보는 중이에요/)).toBeNull();
});

it('brings back unsaved conditions too, and editing a field ends the example',()=>{
  render(<RegionalPrograms browse={false}/>);
  change('현재 만 나이','27');
  fireEvent.click(screen.getByRole('button',{name:'서울 마포 · 29세 · 직장인 · 전세'}));
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'결과 창 닫기'}));
  fireEvent.click(screen.getByRole('button',{name:'예시 끝내기'}));
  expect(value('현재 만 나이')).toBe('27');expect(value('관심·거주 광역지역')).toBe('');
  fireEvent.click(screen.getByRole('button',{name:'서울 마포 · 29세 · 직장인 · 전세'}));
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'결과 창 닫기'}));
  change('현재 만 나이','30');
  expect(screen.queryByText(/예시 조건으로 보는 중이에요/)).toBeNull();
  expect(value('관심·거주 광역지역')).toBe('서울');  // continues from the example as a starting point
});

it('opens an example from a home link once and drops the query',()=>{
  window.location.hash='#/programs?example=busan';
  render(<RegionalPrograms browse={false}/>);
  expect(within(screen.getByRole('dialog')).getByText('부산 · 부산진구 · 만 22세 · 근로 중 · 월세 거주')).toBeVisible();
  expect(window.location.hash).toBe('#/programs');
  cleanup();
  render(<HomeSteps/>);
  for(const e of SUPPORT_EXAMPLES)expect(screen.getByRole('link',{name:e.label})).toHaveAttribute('href','#/programs?example='+e.id);
});
