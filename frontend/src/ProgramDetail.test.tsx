import {render,screen,within,fireEvent,act} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import ProgramDetail from './ProgramDetail';
import RegionalPrograms from './RegionalPrograms';
import {resolveRoute,programIdFromHash,programLink} from './portal-routing';
import {PROFILE_KEY} from './support-profile';
import web from './public-data/current-support-web.json';

beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-14T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();window.location.hash='';});

const p=web.programs.find(x=>x.intake_mode==='WINDOW'&&x.ends_on&&x.ends_on>='2026-11-14'&&(x.provinces as string[]).includes('경기'))!;

it('routes #/programs/item/<id> to the detail page and reads the id back',()=>{
  expect(resolveRoute(programLink(p.program_id))).toBe('detail');
  expect(programIdFromHash(programLink(p.program_id))).toBe(p.program_id);
  expect(resolveRoute('#/programs/list')).toBe('catalog');
  expect(programIdFromHash('#/programs')).toBeNull();
});

it('shows one program with its deadline, conditions, checks, sources and help',()=>{
  window.location.hash=programLink(p.program_id);
  render(<ProgramDetail/>);
  expect(screen.getByRole('heading',{level:1,name:p.title})).toBeVisible();
  expect(screen.getByText(p.benefit_summary)).toBeVisible();
  expect(screen.getByText(/^신청 마감 \d+월 \d+일 · (D-\d+|오늘 마감)$/)).toBeVisible();
  expect(screen.getByRole('heading',{name:'신청 전에 확인할 것'})).toBeVisible();
  for(const t of p.required_checks)expect(screen.getByText(t)).toBeInTheDocument();
  expect(screen.getByRole('link',{name:'공식 안내 보기 ↗'})).toHaveAttribute('href',p.sources[0].url);
  expect(screen.getByRole('complementary',{name:'청년센터 상담 안내'})).toBeVisible();
  expect(screen.getByRole('link',{name:'내 조건 넣고 비교하기 →'})).toBeVisible();
  expect(document.title).toBe(`${p.title} | 청년 경제생활`);
});

it('compares with remembered conditions when there are some',()=>{
  localStorage.setItem(PROFILE_KEY,JSON.stringify({province:'경기',city:'',age:'25',employment:'unemployed',rent:'yes'}));
  window.location.hash=programLink(p.program_id);
  render(<ProgramDetail/>);
  const mine=screen.getByRole('heading',{name:'내 조건과 비교'}).parentElement!;
  expect(within(mine).getByText(/만 25세/)).toBeVisible();
  expect(within(mine).getByText('지역')).toBeVisible();
});

it('says so for an unknown program and follows hash changes',()=>{
  window.location.hash='#/programs/item/NOPE';
  render(<ProgramDetail/>);
  expect(screen.getByRole('heading',{level:1,name:'사업을 찾을 수 없어요'})).toBeVisible();
  act(()=>{window.location.hash=programLink(p.program_id);window.dispatchEvent(new HashChangeEvent('hashchange'));});
  expect(screen.getByRole('heading',{level:1,name:p.title})).toBeVisible();
});

it('copies the link when the browser cannot open a share sheet',async()=>{
  const write=vi.fn(()=>Promise.resolve());
  vi.stubGlobal('navigator',{...navigator,share:undefined,clipboard:{writeText:write}});
  window.location.hash=programLink(p.program_id);
  render(<ProgramDetail/>);
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'이 사업 링크 공유'}));});
  expect(write).toHaveBeenCalledWith(window.location.href);
  expect(screen.getByText(/링크를 복사했어요/)).toBeVisible();
});

it('cards link to the detail page',()=>{
  render(<RegionalPrograms/>);
  const link=screen.getAllByRole('link',{name:/ 자세히 보기$/})[0];
  expect(link.getAttribute('href')).toMatch(/^#\/programs\/item\//);
});

it('gives the tab title back when the page is left',()=>{
  document.title='청년 경제생활 | 내 조건에 맞는 지원과 저축';
  window.location.hash=programLink(p.program_id);
  const {rerender}=render(<ProgramDetail active/>);
  expect(document.title).toBe(`${p.title} | 청년 경제생활`);
  rerender(<ProgramDetail active={false}/>);
  expect(document.title).toBe('청년 경제생활 | 내 조건에 맞는 지원과 저축');
});
