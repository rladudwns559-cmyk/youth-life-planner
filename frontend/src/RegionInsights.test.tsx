import {render,screen,within,fireEvent} from '@testing-library/react';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import RegionInsights from './RegionInsights';
import {regionStats,cityCounts,comparisonNotes,PROVINCES} from './region-stats';
import {resolveRoute,routeLinks} from './portal-routing';
import {PROFILE_KEY} from './support-profile';
import type {OntongPolicy,OntongPolicyList} from './ontong-policies';

const AS_OF='2026-11-17';
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-17T03:00:00Z'));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});

const base:OntongPolicy={id:'P0',title:'정책',category:'일자리',subcategory:'',org:'',summary:'',regions:['*'],age:null,jobs:null,income:null,extra:null,apply:{mode:'ALWAYS'},url:'',apply_url:null,updated:null};
let n=0;const P=(o:Partial<OntongPolicy>):OntongPolicy=>({...base,id:'P'+(++n),...o});
const policies=[
  P({regions:['*'],category:'주거'}),
  P({regions:['경기'],category:'주거'}),
  P({regions:['경기|안산시','경기|수원시 팔달구'],category:'일자리,교육'}),
  P({regions:['경기|안산시 단원구'],category:'일자리'}),
  P({regions:['서울','경기'],category:'참여권리'}),
  P({regions:['부산'],category:'복지문화'}),
  P({regions:['경기'],apply:{mode:'PERIOD',start:'2026-01-01',end:'2026-11-01'}}),
];
const source={title:'온통청년 청년정책 Open API',institution:'한국고용정보원',attribution:'출처: 온통청년(한국고용정보원)',url:''};
const data:OntongPolicyList={fetched_on:AS_OF,source,total:policies.length,policies};

describe('counting',()=>{
  it('separates nationwide from regional, counts a multi-region policy in each region, and drops closed ones',()=>{
    const s=regionStats(policies,AS_OF);
    expect([s.total,s.national,s.regional]).toEqual([6,1,5]);
    const by=(p:string)=>s.provinces.find(x=>x.province===p)!;
    expect(by('경기').count).toBe(4);
    expect(by('서울').count).toBe(1);
    expect(by('경기').byGroup).toEqual({'일자리':2,'주거':1,'교육':1,'복지·문화':0,'참여':1});
    expect(s.nationalByGroup['주거']).toBe(1);
    expect(s.provinces).toHaveLength(17);
    expect(s.average).toBeCloseTo(6/17);
  });
  it('counts districts, folding wards into their city and leaving province-wide policies out',()=>{
    expect(cityCounts(policies,'경기',AS_OF)).toEqual([{city:'안산시',count:2},{city:'수원시',count:1}]);
  });
  it('describes the largest gaps against the average first',()=>{
    const s=regionStats(policies,AS_OF);
    const notes=comparisonNotes(s.provinces.find(x=>x.province==='경기')!,s.averageByGroup);
    expect(notes[0].text).toMatch(/평균보다 \d+% 많아요/);
    expect(notes.every(x=>x.group!=='복지·문화'||x.diff===-100)).toBe(true);
  });
  it('has a route of its own',()=>{
    expect(resolveRoute('#/insights')).toBe('insights');
    expect(routeLinks.insights).toBe('#/insights');
    expect(PROVINCES).toContain('세종');
  });
});

describe('page',()=>{
  it('shows the tiles, ranks the chosen province and compares fields with the average',()=>{
    render(<RegionInsights data={data}/>);
    const tiles=screen.getByRole('list',{name:'정책 수 요약'});
    expect(within(tiles).getByText('6건')).toBeVisible();
    expect(screen.getByLabelText('비교할 지역')).toHaveValue('경기');
    expect(screen.getByText(/17개 광역 중/)).toHaveTextContent('경기 지역은 17개 광역 중 1번째로 많아요(4건');
    const fields=screen.getByRole('region',{name:/분야별 비교: 경기/});
    expect(within(fields).getByText('일자리')).toBeVisible();
    expect(within(fields).getAllByText(/^\(평균/).length).toBe(5);
    const cities=screen.getByRole('region',{name:/경기 안 시·군·구별 정책 수/});
    expect(within(cities).getByText('안산시')).toBeVisible();
    fireEvent.change(screen.getByLabelText('비교할 지역'),{target:{value:'부산'}});
    expect(screen.getByRole('region',{name:/분야별 비교: 부산/})).toBeVisible();
    expect(screen.queryByRole('region',{name:/부산 안 시·군·구별/})).toBeNull();
  });
  it('starts from the remembered province and offers a table',()=>{
    localStorage.setItem(PROFILE_KEY,JSON.stringify({province:'서울',city:'',age:'',employment:'unknown',rent:'unknown'}));
    render(<RegionInsights data={data}/>);
    expect(screen.getByLabelText('비교할 지역')).toHaveValue('서울');
    fireEvent.click(screen.getByText('숫자 표로 보기'));
    const table=screen.getByRole('table',{name:'광역지역별·분야별 지역 대상 정책 수'});
    expect(within(table).getByRole('rowheader',{name:'전국 대상'})).toBeVisible();
    expect(within(table).getAllByRole('row')).toHaveLength(1+17+1);
  });
});
