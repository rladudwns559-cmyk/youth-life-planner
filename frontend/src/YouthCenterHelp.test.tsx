import {render,screen,within} from '@testing-library/react';
import {it,expect,describe} from 'vitest';
import YouthCenterHelp,{centersFor} from './YouthCenterHelp';
import data from './public-data/youth-centers.json';

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
  render(<YouthCenterHelp province="경기" city="안산시 단원구"/>);
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
  render(<YouthCenterHelp province="경기" city="수원시"/>);
  expect(screen.getByText(/아직 직접 확인한 자료가 없어요/)).toBeVisible();
  expect(screen.queryByText('안산시 청년센터 상상대로')).toBeNull();
  expect(screen.getByRole('link',{name:'온통청년 청년센터 찾기 ↗'})).toBeVisible();
});
