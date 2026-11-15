import {render,screen,fireEvent,within,act} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {FavoriteSchedule,CalendarSubscribe} from './SchedulePanels';
import RegionalPrograms from './RegionalPrograms';
import {deadlineOf} from './SupportPlanner';
import web from './public-data/current-support-web.json';

const AS_OF='2026-11-14';
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-14T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});

it('puts saved programs on one timeline by deadline, with undated ones last',()=>{
  const dated=web.programs.filter(p=>deadlineOf(p,AS_OF)).slice(0,3);
  const undated=web.programs.filter(p=>p.intake_mode==='CONTINUOUS').slice(0,1);
  render(<FavoriteSchedule programs={[...undated,...dated].reverse()} asOf={AS_OF}/>);
  const section=screen.getByRole('region',{name:'내 관심 사업 일정'});
  const links=within(section).getAllByRole('link').map(a=>a.textContent);
  const expected=[...dated].sort((a,b)=>deadlineOf(a,AS_OF)!.localeCompare(deadlineOf(b,AS_OF)!)||a.title.localeCompare(b.title,'ko')).map(p=>p.title);
  expect(links.slice(0,3)).toEqual(expected);
  expect(links[3]).toBe(undated[0].title);
  expect(within(section).getByText('마감일이 정해지지 않은 사업')).toBeVisible();
  for(const a of within(section).getAllByRole('link'))expect(a.getAttribute('href')).toMatch(/^#\/programs\/item\//);
});

it('shows nothing without saved programs',()=>{
  const {container}=render(<FavoriteSchedule programs={[]} asOf={AS_OF}/>);
  expect(container).toBeEmptyDOMElement();
});

it('offers subscription links for the chosen region and copies the address',async()=>{
  const write=vi.fn(()=>Promise.resolve());
  vi.stubGlobal('navigator',{...navigator,clipboard:{writeText:write}});
  render(<CalendarSubscribe province="경기"/>);
  const section=screen.getByRole('region',{name:'지역 마감일을 캘린더로 구독하기'});
  expect(within(section).getByLabelText('지역')).toHaveValue('gyeonggi');
  expect(within(section).getByRole('link',{name:'아이폰·맥·아웃룩에서 구독'})).toHaveAttribute('href','webcal://rladudwns559-cmyk.github.io/youth-life-planner/calendars/gyeonggi.ics');
  const google=within(section).getByRole('link',{name:'구글 캘린더에 추가 ↗'}).getAttribute('href')!;
  expect(decodeURIComponent(google)).toContain('cid=webcal://rladudwns559-cmyk.github.io/youth-life-planner/calendars/gyeonggi.ics');
  fireEvent.change(within(section).getByLabelText('지역'),{target:{value:'busan'}});
  expect(within(section).getByText('https://rladudwns559-cmyk.github.io/youth-life-planner/calendars/busan.ics')).toBeVisible();
  await act(async()=>{fireEvent.click(within(section).getByRole('button',{name:'구독 주소 복사'}));});
  expect(write).toHaveBeenCalledWith('https://rladudwns559-cmyk.github.io/youth-life-planner/calendars/busan.ics');
});

it('defaults to the nationwide feed when no region is chosen, and the list page shows the schedule after saving',()=>{
  render(<CalendarSubscribe province=""/>);
  expect(screen.getByLabelText('지역')).toHaveValue('all');
});

it('appears on the list page once a program is saved',()=>{
  render(<RegionalPrograms/>);
  expect(screen.queryByRole('region',{name:'내 관심 사업 일정'})).toBeNull();
  fireEvent.click(screen.getAllByRole('button',{name:/관심사업$/})[0]);
  expect(screen.getByRole('region',{name:'내 관심 사업 일정'})).toBeVisible();
  expect(screen.getByRole('region',{name:'지역 마감일을 캘린더로 구독하기'})).toBeVisible();
});
