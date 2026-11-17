import {render,screen,within,fireEvent,act} from '@testing-library/react';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import OntongPolicies from './OntongPolicies';
import {ONTONG_SEEN_KEY,visit,readSeen} from './ontong-seen';
import {ONTONG_SAVE_KEY,snapshot} from './ontong-saved';
import {leftOut,gapText,type OntongPolicy,type OntongPolicyList} from './ontong-policies';

beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-18T03:00:00Z'));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});

const base:OntongPolicy={id:'P0',title:'정책',category:'일자리',subcategory:'취업',org:'안산시',summary:'요약',regions:['*'],age:null,jobs:null,income:null,extra:null,apply:{mode:'ALWAYS'},url:'',apply_url:null,updated:null};
const P=(o:Partial<OntongPolicy>):OntongPolicy=>({...base,...o,url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/'+(o.id??base.id)});
const source={title:'온통청년 청년정책 Open API',institution:'한국고용정보원',attribution:'출처: 온통청년(한국고용정보원)',url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch'};
const list=(policies:OntongPolicy[]):OntongPolicyList=>({fetched_on:'2026-11-18',source,total:policies.length,policies});

describe('new since the last visit',()=>{
  it('records on the first day, compares with the last earlier day, and keeps it across same-day reloads',()=>{
    const first=visit(['A','B'],'2026-11-16',null);
    expect(first.baseline).toBeNull();
    const nextDay=visit(['A','B','C'],'2026-11-17',first.next);
    expect(nextDay.baseline).toEqual({date:'2026-11-16',ids:['A','B']});
    const reload=visit(['A','B','C','D'],'2026-11-17',nextDay.next);
    expect(reload.baseline).toEqual({date:'2026-11-16',ids:['A','B']});
    expect(reload.next.current.ids).toEqual(['A','B','C','D']);
    expect(visit(['A','B','C','D','E'],'2026-11-18',reload.next).baseline?.ids).toEqual(['A','B','C','D']);
  });
  it('ignores a broken record',()=>{
    localStorage.setItem(ONTONG_SEEN_KEY,'{oops');
    expect(readSeen()).toBeNull();
    localStorage.setItem(ONTONG_SEEN_KEY,JSON.stringify({current:{date:'bad',ids:[]}}));
    expect(readSeen()).toBeNull();
  });
  it('marks new policies, counts them and can show only them',async()=>{
    localStorage.setItem(ONTONG_SEEN_KEY,JSON.stringify({baseline:null,current:{date:'2026-11-16',ids:['OLD']}}));
    await act(async()=>{render(<OntongPolicies profile={{province:'',city:'',age:'',employment:'unknown'}} asOf="2026-11-18" data={list([P({id:'OLD',title:'예전 정책'}),P({id:'NEW',title:'새로 생긴 정책'})])} remember/>);});
    expect(screen.getByText(/지난 방문\(11월 16일\) 이후 새로 올라온 정책이/)).toHaveTextContent('1건 있어요');
    expect(screen.getByRole('heading',{level:4,name:'새 정책새로 생긴 정책'})).toBeVisible();
    fireEvent.click(screen.getByLabelText('새로 올라온 정책만 보기'));
    expect(within(document.querySelector('.ontong-list') as HTMLElement).getAllByRole('heading',{level:4}).map(h=>h.textContent)).toEqual(['새 정책새로 생긴 정책']);
    expect(JSON.parse(localStorage.getItem(ONTONG_SEEN_KEY)!).baseline.date).toBe('2026-11-16');
  });
  it('says nothing about new policies on the very first visit',async()=>{
    await act(async()=>{render(<OntongPolicies profile={{province:'',city:'',age:'',employment:'unknown'}} asOf="2026-11-18" data={list([P({id:'A',title:'정책 A'})])} remember/>);});
    expect(screen.queryByText(/지난 방문/)).toBeNull();
    expect(screen.queryByText('새 정책')).toBeNull();
    expect(readSeen()?.current).toEqual({date:'2026-11-18',ids:['A']});
  });
});

describe('without keeping conditions on this device',()=>{
  it('stores no visit record and says how to turn it on',async()=>{
    localStorage.setItem(ONTONG_SEEN_KEY,JSON.stringify({baseline:null,current:{date:'2026-11-16',ids:['OLD']}}));
    await act(async()=>{render(<OntongPolicies profile={{province:'',city:'',age:'',employment:'unknown'}} asOf="2026-11-18" data={list([P({id:'OLD',title:'예전 정책'}),P({id:'NEW',title:'새로 생긴 정책'})])}/>);});
    expect(screen.queryByText('새 정책')).toBeNull();
    expect(screen.getByText(/내 조건 기억하기’를 켜면 다음에 왔을 때 새로 올라온 정책/)).toBeVisible();
    expect(JSON.parse(localStorage.getItem(ONTONG_SEEN_KEY)!).current.date).toBe('2026-11-16');
  });
});

describe('saved policies closing within a week',()=>{
  it('lists them at the top with the days left',async()=>{
    const soon=P({id:'S',title:'곧 끝나는 정책',apply:{mode:'PERIOD',start:'2026-11-01',end:'2026-11-21'}});
    const later=P({id:'L',title:'한참 남은 정책',apply:{mode:'PERIOD',start:'2026-11-01',end:'2026-12-31'}});
    localStorage.setItem(ONTONG_SAVE_KEY,JSON.stringify([snapshot(soon),snapshot(later)]));
    await act(async()=>{render(<OntongPolicies profile={{province:'',city:'',age:'',employment:'unknown'}} asOf="2026-11-18" data={list([soon,later])}/>);});
    const note=screen.getByRole('note',{name:'곧 마감되는 관심 정책'});
    expect(within(note).getByText('관심 저장한 정책 1건이 일주일 안에 마감돼요')).toBeVisible();
    expect(within(note).getByRole('link',{name:'곧 끝나는 정책 ↗'})).toBeVisible();
    expect(within(note).getByText('11월 21일 · D-3')).toBeVisible();
    expect(within(note).queryByText(/한참 남은 정책/)).toBeNull();
  });
});

describe('policies left out by conditions',()=>{
  const data=[
    P({id:'OK',title:'맞는 정책'}),
    P({id:'YOUNG',title:'청소년 정책',age:[13,24]}),
    P({id:'SOON',title:'만 28세부터 정책',age:[28,39]}),
    P({id:'LATER',title:'만 30세부터 정책',age:[30,39]}),
    P({id:'WORK',title:'재직자 정책',jobs:{groups:['employed'],other:false}}),
    P({id:'BOTH',title:'재직 청소년 정책',age:[13,20],jobs:{groups:['employed'],other:false}}),
    P({id:'BUSAN',title:'부산 정책',regions:['부산'],age:[13,20]}),
  ];
  const profile={province:'경기',city:'안산시',age:'27',employment:'unemployed'};
  it('explains the gap and lists what would open',()=>{
    const {excluded,openings}=leftOut(data,profile,'2026-11-18');
    expect(excluded.map(r=>r.p.id).sort()).toEqual(['BOTH','LATER','SOON','WORK','YOUNG']);
    expect(gapText(excluded.find(r=>r.p.id==='YOUNG')!,profile)).toEqual(['만 13~24세 대상 · 지금 만 27세']);
    expect(gapText(excluded.find(r=>r.p.id==='WORK')!,profile)).toEqual(['근로 중 대상 · 지금 현재 일하지 않음']);
    expect(openings.map(o=>[o.label,o.policies.map(p=>p.id)])).toEqual([
      ['근로 중이면',['WORK']],
      ['1년 뒤 만 28세가 되면',['SOON']],
      ['3년 뒤 만 30세가 되면',['LATER']],
    ]);
  });
  it('shows a closed summary that opens to the reasons',async()=>{
    await act(async()=>{render(<OntongPolicies profile={profile} asOf="2026-11-18" data={list(data)}/>);});
    const box=screen.getByText(/조건이 달라 뺀 정책 5건/).closest('details')!;
    expect(box).not.toHaveAttribute('open');
    fireEvent.click(within(box).getByText(/조건이 달라 뺀 정책 5건/));
    expect(within(box).getByText(/나이 때문에 4건, 취업 상태 때문에 2건/)).toBeVisible();
    expect(within(box).getByRole('heading',{name:'조건이 바뀌면 열리는 정책'})).toBeVisible();
    expect(within(box).getByText('근로 중이면')).toBeVisible();
    expect(within(box).getByRole('link',{name:'청소년 정책 ↗'})).toBeVisible();
    expect(within(box).queryByText(/부산 정책/)).toBeNull();
  });
  it('shows nothing when no condition was entered',async()=>{
    await act(async()=>{render(<OntongPolicies profile={{province:'경기',city:'안산시',age:'',employment:'unknown'}} asOf="2026-11-18" data={list(data)}/>);});
    expect(screen.queryByText(/조건이 달라 뺀 정책/)).toBeNull();
  });
});
