import {render,screen,fireEvent,within} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import RegionalPrograms,{conditionGaps,readPersonalDecision} from './RegionalPrograms';
import {calendarTextMany,deadlineOf,deadlineLabel} from './SupportPlanner';
import web from './public-data/current-support-web.json';

const AS_OF='2026-11-01';
const change=(name:string,value:string)=>fireEvent.change(screen.getByLabelText(name),{target:{value}});
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});

const none={employment:'unknown',rent:'unknown'};
// Finds a nationwide program whose age table has a clear pass range, using the same decision function the UI uses.
function ageRangeProgram(){
  for(const p of web.programs){
    if(p.provinces.length)continue;
    const pass=Array.from({length:121},(_,a)=>a).filter(a=>readPersonalDecision(p.program_id,'*',{age:String(a),...none},AS_OF).age==='PASS');
    if(pass.length&&readPersonalDecision(p.program_id,'*',{age:String(pass[pass.length-1]+3),...none},AS_OF).age==='FAIL'&&readPersonalDecision(p.program_id,'*',{age:String(pass[0]-2),...none},AS_OF).age==='FAIL')
      return {p,lo:pass[0],hi:pass[pass.length-1]};
  }
  throw Error('no program with an age range');
}

it('explains an age mismatch with the range and the distance to it',()=>{
  const {p,lo,hi}=ageRangeProgram();
  const older=conditionGaps(p.program_id,'*',{age:String(hi+3),...none},AS_OF);
  expect(older).toHaveLength(1);
  expect(older[0].text).toContain(`만 ${lo}~${hi}세`);
  expect(older[0].text).toContain('3살 많아요');
  const younger=conditionGaps(p.program_id,'*',{age:String(lo-2),...none},AS_OF);
  expect(younger[0].text).toContain('2살 많아야 해요');
  expect(conditionGaps(p.program_id,'*',{age:String(lo),...none},AS_OF)).toEqual([]);
});

it('lists the employment states a program accepts when the input differs',()=>{
  const p=web.programs.find(p=>readPersonalDecision(p.program_id,'*',{age:'',employment:'employed',rent:'unknown'},AS_OF).employment==='FAIL');
  expect(p).toBeDefined();
  const [gap]=conditionGaps(p!.program_id,'*',{age:'',employment:'employed',rent:'unknown'},AS_OF);
  expect(gap.key).toBe('employment');
  expect(gap.text).toContain("'근로 중' 상태는 대상이 아니에요");
});

it('gives no gaps when nothing conflicts',()=>{
  for(const p of web.programs.slice(0,40))expect(conditionGaps(p.program_id,'*',{age:'',...none},AS_OF)).toEqual([]);
});

it('labels inclusive deadlines and bundles several programs into one calendar file',()=>{
  const dated=web.programs.filter(p=>deadlineOf(p,AS_OF)).slice(0,3);
  expect(dated.length).toBe(3);
  const text=calendarTextMany(dated,AS_OF,'2026-11-01T03:00:00.000Z')!;
  expect(text.match(/BEGIN:VEVENT/g)).toHaveLength(3);
  expect(text.match(/BEGIN:VCALENDAR/g)).toHaveLength(1);
  expect(text.endsWith('END:VCALENDAR\r\n')).toBe(true);
  expect(deadlineLabel('2026-11-16','2026-11-01')).toBe('신청 마감 11월 16일 · D-15');
  expect(deadlineLabel('2026-11-01','2026-11-01')).toBe('신청 마감 11월 1일 · 오늘 마감');
  const closed=web.programs.find(p=>p.intake_mode!=='WINDOW')!;
  expect(calendarTextMany([closed],AS_OF)).toBeNull();
});

it('shows the deadline on cards and why a hidden program differs',()=>{
  render(<RegionalPrograms/>);
  expect(screen.getAllByRole('button',{name:/마감일 캘린더에 추가$/}).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/^신청 마감 \d+월 \d+일 · (D-\d+|오늘 마감)$/).length).toBeGreaterThan(0);
  const {p,hi}=ageRangeProgram();
  change('모집 상태','ALL');
  fireEvent.change(screen.getByLabelText('사업·지원내용 검색'),{target:{value:p.title}});
  change('현재 만 나이',String(hi+3));
  expect(screen.queryByText('무엇이 달라서 맞지 않나요?')).toBeNull();
  fireEvent.click(screen.getByLabelText('현재 조건과 다른 사업도 보기'));
  const card=screen.getByText(p.title,{selector:'h3'}).closest('article')!;
  expect(within(card).getByText('무엇이 달라서 맞지 않나요?')).toBeVisible();
  expect(within(card).getByText(/3살 많아요/)).toBeVisible();
});

it('offers a bundled calendar only for saved programs with a dated deadline',()=>{
  render(<RegionalPrograms/>);
  expect(screen.queryByRole('button',{name:/관심 사업 마감일 한꺼번에/})).toBeNull();
  const card=screen.getAllByRole('button',{name:/마감일 캘린더에 추가$/})[0].closest('article')!;
  fireEvent.click(within(card).getByRole('button',{name:/관심사업$/}));
  expect(screen.getByRole('button',{name:'관심 사업 마감일 한꺼번에 캘린더 저장 (1)'})).toBeEnabled();
});

it('lists programs dropped from the results with the condition that differs',()=>{
  const {hi}=ageRangeProgram();
  render(<RegionalPrograms browse={false}/>);
  change('현재 만 나이',String(hi+3));
  fireEvent.click(screen.getByRole('button',{name:'내 조건으로 찾기 →'}));
  const summary=screen.getByText(/^조건이 달라 뺀 사업 \d+개/);
  fireEvent.click(summary);
  const list=summary.closest('details')!;
  expect(within(list).getAllByText(/살 많아요/).length).toBeGreaterThan(0);
});
