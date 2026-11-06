import {render,screen,fireEvent,within} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import RegionalPrograms from './RegionalPrograms';
import {deadlineOrder} from './support-order';
import prepared from './public-data/current-support-web.json';
import {SUPPORT_SAVE_KEY} from './SupportPlanner';

beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-06T03:00:00Z'));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});
const change=(name:string,value:string)=>fireEvent.change(screen.getByLabelText(name),{target:{value}});

it('saves a finder result to the same favorites list using only IDs, not profile inputs',()=>{
 const {rerender}=render(<RegionalPrograms browse={false}/>);
 change('관심·거주 광역지역','경기');change('현재 만 나이','24');
 fireEvent.click(screen.getByRole('button',{name:'내 조건으로 찾기 →'}));
 const d=within(screen.getByRole('dialog'));
 fireEvent.click(d.getAllByRole('button',{name:/관심사업/})[0]);
 const saved=JSON.parse(localStorage.getItem(SUPPORT_SAVE_KEY)!);
 expect(Object.keys(saved).sort()).toEqual(['checks','favorites']);
 expect(saved.favorites).toHaveLength(1);expect(saved.checks).toEqual([]);
 fireEvent.click(d.getByRole('button',{name:'결과 창 닫기'}));
 rerender(<RegionalPrograms listPage/>);
 fireEvent.click(screen.getByRole('checkbox',{name:'관심사업만 (1)'}));
 expect(Array.from(document.querySelectorAll('[data-support-id]'),n=>n.getAttribute('data-support-id'))).toEqual(saved.favorites);
});

it('reports a real storage write failure inside the active finder without changing eligibility',()=>{
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new DOMException('Synthetic quota','QuotaExceededError');});
 render(<RegionalPrograms browse={false}/>);change('관심·거주 광역지역','경기');
 fireEvent.click(screen.getByRole('button',{name:'내 조건으로 찾기 →'}));const d=within(screen.getByRole('dialog'));
 fireEvent.click(d.getAllByRole('button',{name:/관심사업/})[0]);
 expect(d.getByRole('status')).toHaveTextContent('현재 화면에서만 유지');
 expect(localStorage.getItem(SUPPORT_SAVE_KEY)).toBeNull();
 expect(d.getByText(/입력 조건의 일치는 신청·수급 가능 확정이 아닙니다/)).toBeVisible();
});

it.each([
 ['CONTINUOUS','2026-11-06'],['WINDOW',null],['WINDOW','2026-11-05'],['WINDOW','2026-02-30'],['WINDOW','not-a-date'],
])('never gives unknown, continuous, past or invalid dates an urgent rank: %s %s',(mode,end)=>{
 expect(deadlineOrder({intake_mode:mode!,ends_on:end},'2026-11-06')).toBe(Infinity);
});

it('includes the deadline day itself and orders actual calendar dates',()=>{
 expect(deadlineOrder({intake_mode:'WINDOW',ends_on:'2026-11-06'},'2026-11-06')).toBe(Date.UTC(2026,10,6));
 expect(deadlineOrder({intake_mode:'WINDOW',ends_on:'2026-12-01'},'2026-11-06')).toBeGreaterThan(deadlineOrder({intake_mode:'WINDOW',ends_on:'2026-11-30'},'2026-11-06'));
});

it('changes intake on the list itself without losing the region, age or search',()=>{
 const {rerender}=render(<RegionalPrograms browse={false}/>);
 change('관심·거주 광역지역','경기');change('시·군·구','안산시 상록구');change('현재 만 나이','24');
 rerender(<RegionalPrograms listPage/>);
 change('사업·지원내용 검색','면접');change('모집 상태','ALL');
 expect(screen.getByLabelText('사업·지원내용 검색')).toHaveValue('면접');
 expect(screen.getByText(/안산시 상록구 · 만 24세/)).toBeVisible();
 change('모집 상태','OPEN');
 const cards=Array.from(document.querySelectorAll('[data-support-id]'));
 for(const c of cards){expect(c).toHaveTextContent('공식 접수중 확인');expect(c).toHaveTextContent('지원자격 추가 확인 필요');}
 expect(screen.getByLabelText('모집 상태')).toHaveValue('OPEN');
});

it('sorts known deadlines while keeping mismatched regions out and UNKNOWN intact',()=>{
 const {rerender}=render(<RegionalPrograms browse={false}/>);
 change('관심·거주 광역지역','경기');change('시·군·구','안산시 상록구');change('현재 만 나이','24');
 rerender(<RegionalPrograms listPage/>);change('모집 상태','OPEN');change('지원사업 정렬','DEADLINE');
 const cards=Array.from(document.querySelectorAll('[data-support-id]'));
 expect(cards.length).toBeGreaterThan(0);
 const dates=cards.map(c=>{
  const p=prepared.programs.find(p=>p.program_id===c.getAttribute('data-support-id'))!;
  expect(p.provinces.length===0||(p.provinces as string[]).includes('경기')).toBe(true);
  expect(c).toHaveTextContent('지원자격 추가 확인 필요');
  return deadlineOrder(p,'2026-11-06');
 });
 expect(dates).toEqual([...dates].sort((a,b)=>a-b));
 expect(screen.getByText(/상시·일정 미확인 사업은 뒤에 표시/)).toBeVisible();
 expect(localStorage.length).toBe(0);
});
