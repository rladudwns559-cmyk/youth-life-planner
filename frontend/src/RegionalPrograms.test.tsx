import {render,screen,fireEvent,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import RegionalPrograms,{readRegionalDecision} from './RegionalPrograms';
import data from './public-data/current-support.json';
const change=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});
const cards=()=>screen.queryAllByRole('article');
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('Regional inputs must not be transmitted');}));});
afterEach(()=>vi.useRealTimers());
describe('regional grants beyond savings',()=>{
 it('shows the current catalog and all17region choices without transmitting input',()=>{
  render(<RegionalPrograms/>);change('모집 상태','ALL');expect(screen.getByText('지원사업·모집 안내').parentElement).toHaveTextContent(String(data.programs.length));
  expect(screen.getByLabelText('관심·거주 광역지역').querySelectorAll('option')).toHaveLength(18);
  expect(cards()).toHaveLength(12);expect(fetch).not.toHaveBeenCalled();expect(localStorage.length).toBe(0);
 });
 it('combines national,province,city for Ansan and excludes Seoul',async()=>{
  render(<RegionalPrograms/>);change('모집 상태','ALL');change('관심·거주 광역지역','경기');change('시·군·구','안산시');
  change('사업·지원내용 검색','면접수당');expect(document.querySelector('[data-support-id="GG-YOUTH-INTERVIEW-ALLOWANCE-2026"]')).toBeVisible();change('사업·지원내용 검색','');
  await userEvent.click(screen.getByRole('button',{name:'월세·주거'}));
  const rent=document.querySelector('[data-support-id="KR-YOUTH-RENT-2026"]') as HTMLElement;expect(rent).toBeVisible();
  expect(within(rent).getByText('확인한 회차 마감')).toBeVisible();expect(within(rent).getByText('지원자격 추가 확인 필요')).toBeVisible();
  change('사업·지원내용 검색','서울시 청년월세지원');
  expect(document.querySelector('[data-support-id="SEOUL-YOUTH-RENT-2026"]')).toBeNull();
  await userEvent.click(screen.getByRole('checkbox',{name:'다른 지역 사업도 함께 보기'}));expect(document.querySelector('[data-support-id="SEOUL-YOUTH-RENT-2026"]')).toBeVisible();
  expect(fetch).not.toHaveBeenCalled();expect(localStorage.length).toBe(0);
 });
 it('keeps municipality unknown until selected and resets it on province change',()=>{
  render(<RegionalPrograms/>);change('모집 상태','ALL');change('관심·거주 광역지역','경기');
  change('사업·지원내용 검색','응시료');const c=document.querySelector('[data-support-id="ANSAN-YOUTH-EXAM-FEE-2026"]') as HTMLElement;
  expect(within(c).getByText('거주지·직장·학교 등 세부 지역 확인')).toBeVisible();change('시·군·구','안산시');change('관심·거주 광역지역','서울');
  expect(screen.getByLabelText('시·군·구')).toHaveValue('');expect(document.querySelector('[data-support-id="ANSAN-YOUTH-EXAM-FEE-2026"]')).toBeNull();
 });
 it('does not pretend a different unregistered city has Ansan local benefits',()=>{
  render(<RegionalPrograms/>);change('모집 상태','ALL');change('관심·거주 광역지역','경기');change('시·군·구','__OTHER__');
  expect(document.querySelector('[data-support-id="ANSAN-YOUTH-MOVE-FEE-2026"]')).toBeNull();expect(screen.getByText(/전국 사업과 해당 지역 사업을 함께/)).toBeVisible();
 });
 it('searches non-savings benefits and provides a meaningful empty result',async()=>{
  render(<RegionalPrograms/>);change('모집 상태','ALL');change('사업·지원내용 검색','면접');expect(cards().length).toBeGreaterThan(3);
  change('사업·지원내용 검색','존재하지않는합성문구');expect(cards()).toHaveLength(0);expect(screen.getByText(/실제 지원사업이 없다는 뜻은 아닙니다/)).toBeVisible();
  await userEvent.click(screen.getByRole('button',{name:'전체 등록 사업 보기'}));expect(cards()).toHaveLength(12);
  expect(screen.getByRole('link',{name:'온통청년 공식 정책 통합검색 ↗'})).toHaveAttribute('href','https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch');
 });
 it('distinguishes closed and unknown even inside annual business periods',()=>{
  render(<RegionalPrograms/>);change('모집 상태','ALL');change('관심·거주 광역지역','인천');change('사업·지원내용 검색','드림나래');
  expect(within(cards()[0]).getByText('확인한 회차 마감')).toBeVisible();
  change('관심·거주 광역지역','경기');change('시·군·구','안산시');change('사업·지원내용 검색','응시료');
  expect(within(cards()[0]).getByText('현재 접수 추가 확인')).toBeVisible();
 });
 it('pages through all records without losing state or duplicating IDs',()=>{
  render(<RegionalPrograms/>);change('모집 상태','ALL');
  const more=screen.getByRole('button',{name:'사업 12개 더 보기'});
  for(let offset=12;offset<data.programs.length;offset+=12){
    fireEvent.click(more);
    expect(document.querySelectorAll('[data-support-id]')).toHaveLength(Math.min(offset+12,data.programs.length));
  }
  const ids=Array.from(document.querySelectorAll('[data-support-id]'),c=>c.getAttribute('data-support-id'));
  expect(new Set(ids)).toEqual(new Set(data.programs.map(p=>p.program_id)));
  expect(more).not.toBeInTheDocument();
 },20000);
 it('preserves UNKNOWN and downgrades schedules beyond the built review window',()=>{
  expect(readRegionalDecision('KR-YOUTH-RENT-2026','경기|안산시','2026-11-01')).toEqual({region:'PASS',intake:'CLOSED',overall:'UNKNOWN'});
  expect(readRegionalDecision('KR-NATIONAL-LEARNING-CARD','서울','2026-11-09').intake).toBe('REVIEW_REQUIRED');
  expect(data.programs.every(p=>p.eligibility==='UNKNOWN'&&p.benefit_applied_krw===0)).toBe(true);
 });
});
