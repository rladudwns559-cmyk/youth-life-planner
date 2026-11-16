import {render,screen,within,fireEvent,act} from '@testing-library/react';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import FutureTimeline from './FutureTimeline';
import RegionalPrograms from './RegionalPrograms';
import {futureStages,schoolAfter,stageLabel} from './ontong-timeline';
import type {OntongPolicy} from './ontong-policies';

beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-17T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});

const AS_OF='2026-11-17';
const base:OntongPolicy={id:'P0',title:'정책',category:'일자리',subcategory:'취업',org:'안산시',summary:'요약',regions:['*'],age:null,jobs:null,income:null,extra:null,apply:{mode:'ALWAYS'},url:'',apply_url:null,updated:null};
const P=(o:Partial<OntongPolicy>):OntongPolicy=>({...base,...o,url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/'+(o.id??base.id)});
const list=[
  P({id:'ANY',title:'누구나'}),
  P({id:'TEEN',title:'만 24세까지',age:[19,24]}),
  P({id:'AT25',title:'만 25세부터',age:[25,34]}),
  P({id:'GRAD',title:'졸업생 대상',school:{groups:['univ_grad'],other:false}}),
  P({id:'EXP',title:'졸업 예정자 대상',school:{groups:['univ_expected'],other:false}}),
];
const profile={province:'경기',city:'안산시',age:'23',employment:'unknown',school:'univ_student',marriage:'unknown'};

describe('future stages',()=>{
  it('moves a university student to 졸업 예정 then 졸업',()=>{
    expect(schoolAfter('univ_student',0)).toBe('univ_student');
    expect(schoolAfter('univ_student',1)).toBe('univ_expected');
    expect(schoolAfter('univ_student',3)).toBe('univ_grad');
    expect(schoolAfter('univ_expected',1)).toBe('univ_grad');
    expect(schoolAfter('univ_grad',5)).toBe('univ_grad');
  });
  it('lists what opens and closes each year, only for years that change',()=>{
    const stages=futureStages(list,profile,AS_OF)!;
    const summary=stages.map(s=>[stageLabel(s),s.count,s.opened.map(p=>p.id),s.closed.map(p=>p.id)]);
    // Years with no change are skipped; the 25~34 policy closes at 35. The line stops at 40.
    expect(summary).toEqual([
      ['지금 · 만 23세',2,[],[]],
      ['1년 뒤 · 만 24세 · 대학 졸업 예정',3,['EXP'],[]],
      ['2년 뒤 · 만 25세 · 대학 졸업',3,['AT25','GRAD'],['TEEN','EXP']],
      ['12년 뒤 · 만 35세',2,[],['AT25']],
    ]);
    expect(futureStages(list,profile,AS_OF,[],3)!.at(-1)!.age).toBe(25);
  });
  it('needs an age',()=>{
    expect(futureStages(list,{...profile,age:''},AS_OF)).toBeNull();
  });
});

describe('timeline on screen',()=>{
  it('stays closed until asked, so nothing is worked out on every change',()=>{
    render(<FutureTimeline list={list} profile={profile} asOf={AS_OF} known={[]}/>);
    expect(screen.getByRole('button',{name:'앞으로 열리고 닫히는 정책 보기'})).toHaveAttribute('aria-expanded','false');
    expect(screen.queryByText('지금 · 만 23세')).toBeNull();
  });
  it('shows each year with counts, opened titles and the assumptions',()=>{
    render(<FutureTimeline list={list} profile={profile} asOf={AS_OF} known={[]}/>);
    fireEvent.click(screen.getByRole('button',{name:'앞으로 열리고 닫히는 정책 보기'}));
    const section=screen.getByRole('region',{name:'내 미래 정책 타임라인'});
    expect(within(section).getByText('지금 · 만 23세')).toBeVisible();
    expect(within(section).getByText('2년 뒤 · 만 25세 · 대학 졸업')).toBeVisible();
    expect(within(section).getByRole('link',{name:'만 25세부터 ↗'})).toBeVisible();
    expect(within(section).getByText('−2 닫힘')).toBeVisible();
    expect(within(section).getByText(/1년 뒤 졸업 예정, 2년 뒤 졸업으로 가정했어요/)).toBeVisible();
  });
  it('asks for an age when there is none',()=>{
    render(<FutureTimeline list={list} profile={{...profile,age:''}} asOf={AS_OF} known={[]} defaultOpen/>);
    expect(screen.getByText(/만 나이를 넣으면 앞으로 몇 년 동안/)).toBeVisible();
  });
});

describe('sentence on the support page',()=>{
  it('fills the form from one sentence and shows what it understood',async()=>{
    render(<RegionalPrograms/>);
    fireEvent.change(screen.getByLabelText('내 상황 문장'),{target:{value:'안산 사는 24살 대학생이고 월세 살아요'}});
    await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'조건 채우기'}));});
    expect(screen.getByLabelText('관심·거주 광역지역')).toHaveValue('경기');
    expect(screen.getByLabelText('시·군·구')).toHaveValue('안산시');
    expect(screen.getByLabelText('현재 만 나이')).toHaveValue(24);
    expect(screen.getByLabelText('현재 월세 거주 여부')).toHaveValue('yes');
    expect(screen.getByLabelText('학력')).toHaveValue('univ_student');
    expect(screen.getByLabelText('현재 취업 상태')).toHaveValue('unknown');
    const result=screen.getByText('이렇게 이해했어요').closest('[role=status]') as HTMLElement;
    expect(within(result).getByText('경기 안산시')).toBeVisible();
    expect(localStorage.length).toBe(0);
  });
  it('says so when nothing was understood and leaves the form alone',async()=>{
    render(<RegionalPrograms/>);
    fireEvent.change(screen.getByLabelText('내 상황 문장'),{target:{value:'안녕하세요'}});
    await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'조건 채우기'}));});
    expect(screen.getByText(/알아들은 조건이 없어요/)).toBeVisible();
    expect(screen.getByLabelText('관심·거주 광역지역')).toHaveValue('');
  });
});
