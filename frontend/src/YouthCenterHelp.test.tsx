import {render,screen,within,fireEvent} from '@testing-library/react';
import {it,expect,describe} from 'vitest';
import YouthCenterHelp,{centersFor,apiCentersFor,type ApiCenterList,type ApiCenter} from './YouthCenterHelp';
import apiFile from './public-data/youth-centers-api.json';
import data from './public-data/youth-centers.json';

const source={title:'온통청년 청년센터 정보 Open API',institution:'한국고용정보원',attribution:'출처: 온통청년(한국고용정보원)',url:'https://www.youthcenter.go.kr/youthApply/ythCenter/ythCenterMain'};
const EMPTY:ApiCenterList={fetched_on:null,source,total:0,centers:[]};
const center=(id:string,province:string,city:string,name:string,phone:string|null='031-000-0000',url:string|null=null):ApiCenter=>({id,province,city,district_label:city,name,address:province+' '+city+' 어딘가 1',phone,url});
const LIST:ApiCenterList={fetched_on:'2026-11-16',source,total:12,centers:[
  center('YC-1','경기','안산시','안산시 청년센터 상상대로','031-492-2030'),
  center('YC-2','경기','안산시 단원구','단원 청년공간',null),
  center('YC-3','경기','수원시 팔달구','팔달 청년센터','031-111-2222','https://example.kr/'),
  center('YC-4','경기','수원시','수원시 청년바람지대'),
  center('YC-5','세종','','세종 청년센터'),
  center('YC-6','부산','동래구','동래구청년어울림센터'),
  ...Array.from({length:6},(_,i)=>center('YC-S'+i,'서울','마포구','마포 청년공간 '+i)),
]};

describe('verified youth-center data',()=>{
  it('keeps every center tied to an official municipal source with a check date',()=>{
    expect(data.centers.length).toBeGreaterThan(0);
    for(const c of data.centers){
      expect(c.phone).toMatch(/^0\d{1,2}-\d{3,4}-\d{4}$/);
      expect(c.url).toMatch(/^https:\/\//);
      expect(c.sources.length).toBeGreaterThan(0);
      for(const s of c.sources){
        expect(new URL(s.url).hostname).toMatch(/\.go\.kr$/);
        expect(s.verified_on).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      }
    }
    expect(new Set(data.centers.map(c=>c.id)).size).toBe(data.centers.length);
  });
  it('links to the national finder instead of copying its list',()=>{
    expect(new URL(data.national.url).hostname).toBe('www.youthcenter.go.kr');
    expect(data.national.phone).toBe('1670-1839');
  });
});

describe('centersFor',()=>{
  it('finds Ansan centers for the city and for its districts',()=>{
    const ids=centersFor('경기','안산시').map(c=>c.id);
    expect(ids).toEqual(['GG-ANSAN-SANGSANGDAERO','GG-ANSAN-SANGSANGSTATION']);
    expect(centersFor('경기','안산시 단원구').map(c=>c.id)).toEqual(ids);
    expect(centersFor('경기','안산시 상록구').map(c=>c.id)).toEqual(ids);
  });
  it('returns nothing for other places or an unselected city',()=>{
    expect(centersFor('경기','수원시')).toEqual([]);
    expect(centersFor('서울','안산시')).toEqual([]);
    expect(centersFor('경기','')).toEqual([]);
    expect(centersFor('경기','__OTHER__')).toEqual([]);
    expect(centersFor('','')).toEqual([]);
  });
});

it('shows Ansan centers with a callable phone, the source and the national finder',()=>{
  render(<YouthCenterHelp province="경기" city="안산시 단원구" list={EMPTY}/>);
  const panel=screen.getByRole('complementary',{name:'청년센터 상담 안내'});
  expect(within(panel).getByText('안산시 청년센터 상상대로')).toBeVisible();
  expect(within(panel).getByRole('link',{name:'안산시 청년센터 상상대로 전화 031-492-2030'})).toHaveAttribute('href','tel:0314922030');
  expect(within(panel).getByRole('link',{name:'안산시 청년센터 상상스테이션 전화 031-410-0311'})).toHaveAttribute('href','tel:0314100311');
  expect(within(panel).getAllByText(/확인 2026-11-13/)).toHaveLength(2);
  for(const link of within(panel).getAllByRole('link').filter(a=>a.getAttribute('href')!.startsWith('http'))){
    expect(link).toHaveAttribute('target','_blank');expect(link).toHaveAttribute('rel','noopener noreferrer');
  }
  expect(within(panel).getByRole('link',{name:'온통청년 청년센터 찾기 ↗'})).toHaveAttribute('href',data.national.url);
  expect(within(panel).getByRole('link',{name:'1670-1839'})).toHaveAttribute('href','tel:16701839');
});

it('says so when a region has no verified center and still offers the national finder',()=>{
  render(<YouthCenterHelp province="경기" city="수원시" list={EMPTY}/>);
  expect(screen.getByText(/이 지역 청년센터 정보가 아직 없어요/)).toBeVisible();
  expect(screen.queryByText('안산시 청년센터 상상대로')).toBeNull();
  expect(screen.getByRole('link',{name:'온통청년 청년센터 찾기 ↗'})).toBeVisible();
});

describe('nationwide list from the 온통청년 Open API',()=>{
  it('stores only display fields with the attribution, and every record maps to a region',()=>{
    const file=apiFile as unknown as ApiCenterList;
    expect(file.source.attribution).toBe('출처: 온통청년(한국고용정보원)');
    expect(file.total).toBe(file.centers.length);
    for(const c of file.centers){
      expect(Object.keys(c).sort()).toEqual(['address','city','district_label','id','name','phone','province','url']);
      expect(c.id).toMatch(/^YC-\d+$/);
      if(c.url)expect(c.url).toMatch(/^https?:\/\//);
    }
    expect(new Set(file.centers.map(c=>c.id)).size).toBe(file.centers.length);
  });
  it('finds centers for a ward, its city and the whole of 세종, and skips hand-verified duplicates',()=>{
    expect(apiCentersFor('경기','안산시 단원구',LIST).map(c=>c.id)).toEqual(['YC-2']);
    expect(apiCentersFor('경기','수원시',LIST).map(c=>c.id)).toEqual(['YC-3','YC-4']);
    expect(apiCentersFor('경기','수원시 팔달구',LIST).map(c=>c.id)).toEqual(['YC-3','YC-4']);
    expect(apiCentersFor('세종','',LIST).map(c=>c.id)).toEqual(['YC-5']);
    expect(apiCentersFor('경기','',LIST)).toEqual([]);
    expect(apiCentersFor('경기','__OTHER__',LIST)).toEqual([]);
    expect(apiCentersFor('','',LIST)).toEqual([]);
  });
  it('shows listed centers with the source and collection date',()=>{
    render(<YouthCenterHelp province="경기" city="수원시 팔달구" list={LIST}/>);
    const panel=screen.getByRole('complementary',{name:'청년센터 상담 안내'});
    expect(within(panel).getByText('팔달 청년센터')).toBeVisible();
    expect(within(panel).getByRole('link',{name:'팔달 청년센터 전화 031-111-2222'})).toHaveAttribute('href','tel:0311112222');
    expect(within(panel).getByRole('link',{name:'팔달 청년센터 누리집'})).toHaveAttribute('href','https://example.kr/');
    expect(within(panel).queryByRole('link',{name:'수원시 청년바람지대 누리집'})).toBeNull();
    expect(within(panel).getByText(/출처: 온통청년\(한국고용정보원\)/)).toHaveTextContent('2026-11-16 수집');
    expect(within(panel).getByText(/다른 지역의 청년센터는/)).toBeVisible();
  });
  it('says when a phone is missing and keeps the verified card first without a duplicate',()=>{
    render(<YouthCenterHelp province="경기" city="안산시 단원구" list={LIST}/>);
    expect(screen.getAllByText('안산시 청년센터 상상대로')).toHaveLength(1);
    const card=screen.getByText('단원 청년공간').closest('li')!;
    expect(within(card).getByText('자료에 없음')).toBeVisible();
  });
  it('shows six at first and the rest on request',()=>{
    render(<YouthCenterHelp province="서울" city="마포구" list={{...LIST,centers:[...LIST.centers,center('YC-S9','서울','마포구','마포 청년공간 9')]}}/>);
    expect(screen.getAllByText(/^마포 청년공간 /)).toHaveLength(6);
    fireEvent.click(screen.getByRole('button',{name:'1곳 더 보기'}));
    expect(screen.getAllByText(/^마포 청년공간 /)).toHaveLength(7);
    expect(screen.getByRole('button',{name:'접기'})).toHaveAttribute('aria-expanded','true');
  });
  it('asks for a city when only a province is chosen',()=>{
    render(<YouthCenterHelp province="경기" city="" list={LIST}/>);
    expect(screen.getByText('시·군·구를 고르면 그 지역 청년센터를 보여드려요.')).toBeVisible();
  });
});
