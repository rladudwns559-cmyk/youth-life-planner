import {render,screen,within} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {HomeSteps,HomeDeadlines,closingSoon} from './HomeExtras';
import {readRegionalDecision} from './support-status';
import {daysLeft} from './SupportPlanner';

beforeEach(()=>{vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-13T03:00:00Z'));});
afterEach(()=>{vi.useRealTimers();});

it('lists only dated, unclosed deadlines within the window, closest first',()=>{
  const rows=closingSoon('2026-11-13',7);
  expect(rows.length).toBeGreaterThan(0);
  for(const r of rows){
    expect(r.program.intake_mode).toBe('WINDOW');
    expect(r.end>='2026-11-13').toBe(true);
    expect(r.days).toBe(daysLeft(r.end,'2026-11-13'));
    expect(r.days).toBeLessThanOrEqual(7);
    expect(['CLOSED','NO_INTAKE']).not.toContain(readRegionalDecision(r.program.program_id,'*','2026-11-13').intake);
  }
  expect(rows.map(r=>r.days)).toEqual([...rows.map(r=>r.days)].sort((a,b)=>a-b));
  expect(closingSoon('2026-11-13',14).length).toBeGreaterThanOrEqual(rows.length);
});

it('shows the count, four programs with D-day and calendar buttons, and the status caveat',()=>{
  render(<HomeDeadlines/>);
  const total=closingSoon('2026-11-13',7).length;
  const section=screen.getByRole('region',{name:`7일 안에 신청이 마감되는 지원사업 ${total}개`});
  const items=within(section).getAllByRole('listitem');
  expect(items).toHaveLength(Math.min(4,total));
  for(const li of items){
    expect(within(li).getByText(/^신청 마감 \d+월 \d+일 · (D-\d+|오늘 마감)$/)).toBeVisible();
    expect(within(li).getByRole('button',{name:/마감일 캘린더에 추가$/})).toBeVisible();
    expect(within(li).getByRole('link',{name:/공식 안내$/})).toHaveAttribute('rel','noopener noreferrer');
  }
  expect(within(section).getByText(/공고에 적힌 마감일 기준이에요\(2026-11-13 기준\)/)).toBeVisible();
  if(total>4)expect(within(section).getByText(`외 ${total-4}개는`,{exact:false})).toBeVisible();
});

it('explains the three steps with links into the app',()=>{
  render(<HomeSteps/>);
  const section=screen.getByRole('region',{name:'이렇게 써 보세요'});
  expect(within(section).getAllByRole('listitem')).toHaveLength(3);
  expect(within(section).getByRole('link',{name:'조건 넣으러 가기 →'})).toHaveAttribute('href','#/programs');
  expect(within(section).getByRole('link',{name:'지원사업 둘러보기 →'})).toHaveAttribute('href','#/programs/list');
});
