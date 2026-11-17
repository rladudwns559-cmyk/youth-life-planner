import {render,screen,within,fireEvent,act} from '@testing-library/react';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import OntongPolicies from './OntongPolicies';
import {FavoriteSchedule} from './SchedulePanels';
import {ONTONG_SAVE_KEY,readSaved,snapshot,asPlannerProgram,type SavedPolicy} from './ontong-saved';
import {policyGroups,categoryText,closesSoon,type OntongPolicy,type OntongPolicyList} from './ontong-policies';
import {calendarTextMany} from './SupportPlanner';
import RegionalPrograms from './RegionalPrograms';

const AS_OF='2026-11-16';
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-16T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});

const base:OntongPolicy={id:'P0',title:'정책',category:'일자리',subcategory:'취업',org:'안산시',summary:'요약',regions:['*'],age:null,jobs:null,income:null,extra:null,apply:{mode:'ALWAYS'},url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/P0',apply_url:null,updated:null};
const P=(o:Partial<OntongPolicy>):OntongPolicy=>({...base,...o,url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/'+(o.id??base.id)});
const source={title:'온통청년 청년정책 Open API',institution:'한국고용정보원',attribution:'출처: 온통청년(한국고용정보원)',url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch'};
const data:OntongPolicyList={fetched_on:AS_OF,source,total:4,policies:[
  P({id:'J1',title:'면접 정장 대여',category:'일자리,일자리',apply:{mode:'PERIOD',start:'2026-11-01',end:'2026-11-20'}}),
  P({id:'H1',title:'월세 지원',category:'주거',subcategory:'주거비'}),
  P({id:'E1',title:'자격증 응시료',category:'교육·직업훈련,교육',apply:{mode:'PERIOD',start:'2026-11-01',end:'2026-12-31'}}),
  P({id:'W1',title:'문화 패스',category:'복지문화'}),
]};
const profile={province:'경기',city:'안산시',age:'',employment:'unknown'};

describe('fields and closing soon',()=>{
  it('folds repeated and old field names into five groups',()=>{
    expect(policyGroups({category:'일자리,일자리'})).toEqual(['일자리']);
    expect(policyGroups({category:'일자리,교육'})).toEqual(['일자리','교육']);
    expect(policyGroups({category:'복지문화'})).toEqual(['복지·문화']);
    expect(policyGroups({category:'금융·복지·문화'})).toEqual(['복지·문화']);
    expect(policyGroups({category:'참여권리'})).toEqual(['참여']);
    expect(categoryText({category:'교육·직업훈련,교육·직업훈련',subcategory:'역량,역량'})).toBe('교육·직업훈련 · 역량');
  });
  it('counts a period ending within 14 days as closing soon',()=>{
    expect(closesSoon(data.policies[0],AS_OF)).toBe(true);
    expect(closesSoon(data.policies[2],AS_OF)).toBe(false);
    expect(closesSoon(data.policies[1],AS_OF)).toBe(false);
  });
});

describe('filters in the policy section',()=>{
  it('narrows by field and by closing soon, with counts',()=>{
    render(<OntongPolicies profile={profile} asOf={AS_OF} data={data}/>);
    const groups=screen.getByRole('group',{name:'정책 분야'});
    expect(within(groups).getAllByRole('button').map(b=>b.textContent)).toEqual(['전체 4','일자리 1','주거 1','교육 1','복지·문화 1']);
    fireEvent.click(within(groups).getByRole('button',{name:'주거 1'}));
    expect(within(document.querySelector('.ontong-list') as HTMLElement).getAllByRole('heading',{level:4}).map(h=>h.textContent)).toEqual(['월세 지원']);
    expect(screen.getByRole('status')).toHaveTextContent('주거 분야 1건');
    fireEvent.click(within(groups).getByRole('button',{name:'전체 4'}));
    fireEvent.click(screen.getByLabelText('마감 14일 이내만 보기'));
    expect(within(document.querySelector('.ontong-list') as HTMLElement).getAllByRole('heading',{level:4}).map(h=>h.textContent)).toEqual(['면접 정장 대여']);
    fireEvent.click(within(groups).getByRole('button',{name:'주거 1'}));
    expect(screen.getByText(/고른 분야·마감 조건에 맞는 정책이 없어요/)).toBeVisible();
  });
});

describe('saving policies',()=>{
  it('stores a small copy only and reads back valid entries',()=>{
    render(<OntongPolicies profile={profile} asOf={AS_OF} data={data}/>);
    fireEvent.click(screen.getByRole('button',{name:'면접 정장 대여 관심 정책'}));
    expect(screen.getByRole('button',{name:'면접 정장 대여 관심 정책'})).toHaveAttribute('aria-pressed','true');
    const stored=JSON.parse(localStorage.getItem(ONTONG_SAVE_KEY)!);
    expect(Object.keys(stored[0]).sort()).toEqual(['always','apply_url','end','id','org','place','start','summary','title','url']);
    expect(readSaved()[0]).toMatchObject({id:'J1',end:'2026-11-20',place:'전국'});
    fireEvent.click(screen.getByRole('button',{name:'면접 정장 대여 관심 정책'}));
    expect(localStorage.getItem(ONTONG_SAVE_KEY)).toBeNull();
  });
  it('ignores broken or unsafe stored data',()=>{
    localStorage.setItem(ONTONG_SAVE_KEY,JSON.stringify([{id:'X',title:'나쁜 링크',url:'javascript:alert(1)'},{id:'Y',title:'정상',url:'https://www.youthcenter.go.kr/a',end:'not-a-date'},'junk']));
    expect(readSaved()).toEqual([expect.objectContaining({id:'Y',end:null})]);
    localStorage.setItem(ONTONG_SAVE_KEY,'{broken');
    expect(readSaved()).toEqual([]);
  });
  it('puts saved policies on the schedule with dated, always-open and past groups',()=>{
    const saved:SavedPolicy[]=[snapshot(data.policies[0]),snapshot(data.policies[1]),{...snapshot(data.policies[2]),id:'OLD',title:'끝난 정책',end:'2026-11-01'}];
    const remove=vi.fn();
    render(<FavoriteSchedule programs={[]} policies={saved} asOf={AS_OF} onRemovePolicy={remove}/>);
    const section=screen.getByRole('region',{name:'내 관심 사업 일정'});
    expect(within(section).getByText(/온통청년 정책 3개를/)).toBeVisible();
    expect(within(section).getByRole('heading',{name:'11월 마감'})).toBeVisible();
    const link=within(section).getByRole('link',{name:'면접 정장 대여 ↗'});
    expect(link).toHaveAttribute('href',data.policies[0].url);expect(link).toHaveAttribute('target','_blank');
    expect(within(section).getByRole('heading',{name:'신청 기간이 지난 관심 정책'})).toBeVisible();
    fireEvent.click(within(section).getByRole('button',{name:'끝난 정책 관심 정책 지우기'}));
    expect(remove).toHaveBeenCalledWith('OLD');
  });
  it('adds dated saved policies to the calendar file',()=>{
    const text=calendarTextMany([asPlannerProgram(snapshot(data.policies[0])),asPlannerProgram(snapshot(data.policies[1]))],AS_OF,'2026-11-16T00:00:00.000Z')!;
    expect(text.match(/BEGIN:VEVENT/g)).toHaveLength(1);
    expect(text).toContain('UID:ontong-J1@youth-life-planner.local');
    expect(text).toContain('DTSTART;VALUE=DATE:20261120');
  });
  it('shows saved policies on the list page schedule, calendar button and memo, and clears them',async()=>{
    localStorage.setItem(ONTONG_SAVE_KEY,JSON.stringify([snapshot(data.policies[0])]));
    render(<RegionalPrograms/>);
    const schedule=screen.getByRole('region',{name:'내 관심 사업 일정'});
    expect(within(schedule).getByRole('link',{name:'면접 정장 대여 ↗'})).toBeVisible();
    expect(screen.getByRole('button',{name:'관심 사업 마감일 한꺼번에 캘린더 저장 (1)'})).toBeEnabled();
    fireEvent.click(screen.getByRole('button',{name:'상담 준비 메모 만들기 (1)'}));
    const sheet=await screen.findByRole('article',{name:'상담 준비 메모'});
    expect(within(sheet).getByRole('heading',{name:'면접 정장 대여'})).toBeVisible();
    expect(within(sheet).getByText(/온통청년 등록 정책/)).toBeVisible();
    fireEvent.click(screen.getAllByRole('button',{name:'닫기'})[0]);
    await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'내 기기의 관심·확인 기록 지우기'}));});
    expect(localStorage.getItem(ONTONG_SAVE_KEY)).toBeNull();
    expect(screen.queryByRole('region',{name:'내 관심 사업 일정'})).toBeNull();
  });
});
