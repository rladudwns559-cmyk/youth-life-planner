import {render,screen,fireEvent,within,act} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import RegionalPrograms from './RegionalPrograms';
import {calendarText,readPlanner,SUPPORT_SAVE_KEY,checkKey,useKoreaDay} from './SupportPlanner';
import data from './public-data/current-support.json';
const change=(name:string,value:string)=>fireEvent.change(screen.getByLabelText(name),{target:{value}});
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});
it('prioritizes verified recruitment and hides closed rounds by default',()=>{
 render(<RegionalPrograms/>);expect(screen.getByLabelText('모집 상태')).toHaveValue('CURRENT');
 const cards=screen.getAllByRole('article');expect(cards[0]).toHaveTextContent('공식 접수중 확인');
 expect(cards.every(c=>!c.textContent?.includes('확인한 회차 마감'))).toBe(true);
 change('모집 상태','CLOSED');expect(screen.getAllByRole('article')[0]).toHaveTextContent(/마감|미운영/);
});
it('keeps expired source evidence from appearing as current OPEN',()=>{
 vi.setSystemTime(new Date('2026-11-10T03:00:00Z'));render(<RegionalPrograms/>);change('모집 상태','OPEN');
 expect(screen.queryAllByRole('article')).toHaveLength(0);expect(screen.getByText(/실제 지원사업이 없다는 뜻/)).toBeVisible();
});
it('updates dates on tab focus without reloading the page',()=>{
 function Day(){return <span>{useKoreaDay()}</span>;}render(<Day/>);expect(screen.getByText('2026-11-01')).toBeVisible();
 vi.setSystemTime(new Date('2026-11-02T03:00:00Z'));act(()=>window.dispatchEvent(new Event('focus')));expect(screen.getByText('2026-11-02')).toBeVisible();
});
it('caps comparison at three and preserves selection across filters',()=>{
 render(<RegionalPrograms/>);const boxes=screen.getAllByRole('checkbox',{name:/사업 비교 선택/});boxes.slice(0,3).forEach(b=>fireEvent.click(b));expect(boxes[3]).toBeDisabled();
 expect(screen.getByRole('region',{name:'지원사업 비교 표'})).toBeVisible();change('사업·지원내용 검색','없을검색어');expect(screen.getByRole('region',{name:'지원사업 비교 표'})).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'사업 비교 선택 지우기'}));expect(screen.queryByRole('region',{name:'지원사업 비교 표'})).toBeNull();
});
it('stores only selected IDs, never profile, and supports deletion',()=>{
 render(<RegionalPrograms/>);change('현재 만 나이','23');change('현재 취업 상태','unemployed');change('현재 월세 거주 여부','yes');
 fireEvent.click(screen.getAllByRole('button',{name:/관심사업$/})[0]);const v=JSON.parse(localStorage.getItem(SUPPORT_SAVE_KEY)!);expect(Object.keys(v).sort()).toEqual(['checks','favorites']);expect(v.favorites).toHaveLength(1);
 expect(localStorage.getItem(SUPPORT_SAVE_KEY)).not.toMatch(/age|rent|income|employment|unemployed/);
 change('사업·지원내용 검색','');fireEvent.click(screen.getByRole('checkbox',{name:/관심사업만/}));expect(screen.getAllByRole('article')).toHaveLength(1);
 const c=screen.getAllByRole('article')[0];fireEvent.click(within(c).getByText(/신청 전 확인 목록/));const check=c.querySelector('.application-checklist input')!;fireEvent.click(check);
 expect(JSON.parse(localStorage.getItem(SUPPORT_SAVE_KEY)!).checks).toHaveLength(1);expect(c).toHaveTextContent('지원자격 추가 확인 필요');expect(fetch).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'내 기기의 관심·확인 기록 지우기'}));expect(localStorage.getItem(SUPPORT_SAVE_KEY)).toBeNull();
});
it('rejects corrupt, oversized and obsolete stored IDs',()=>{
 for(const raw of ['null','{"favorites":["fake",123],"checks":["fake"]}','[','x'.repeat(65537)]){localStorage.setItem(SUPPORT_SAVE_KEY,raw);expect(readPlanner(data.programs)).toEqual({favorites:[],checks:[]});}
 const p=data.programs[0];localStorage.setItem(SUPPORT_SAVE_KEY,JSON.stringify({favorites:[p.program_id,p.program_id],checks:[checkKey(p,p.required_checks[0])]}));expect(readPlanner(data.programs).favorites).toEqual([p.program_id]);
});
it('reports blocked storage instead of claiming persistent save',()=>{
 render(<RegionalPrograms/>);vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('blocked');});fireEvent.click(screen.getAllByRole('button',{name:/관심사업$/})[0]);expect(screen.getByText(/현재 화면에서만 유지/)).toBeVisible();
});
it('exports only official dated unclosed windows as explicitly all-day reminders',()=>{
 const p=data.programs.find(p=>p.program_id==='SEOUL-LIFE-PLANNING-STARTER-2026')!;
 const text=calendarText(p,'2026-11-01','2026-11-01T03:00:00.000Z')!;expect(text).toContain('DTSTART;VALUE=DATE:20261116');expect(text).toContain('DTEND;VALUE=DATE:20261117');expect(text).not.toContain('BEGIN:VALARM');expect(text).toContain('DTSTAMP:20261101T030000Z');
 expect(calendarText(p,'2026-11-17')).toBeNull();expect(calendarText({...p,intake_mode:'CLOSED'},'2026-11-01')).toBeNull();expect(calendarText({...p,ends_on:null},'2026-11-01')).toBeNull();expect(calendarText({...p,ends_on:'2026-02-30'},'2026-01-01')).toBeNull();
});
it('escapes ICS text injection and folds Korean lines without breaking UTF-8',()=>{
 const p=data.programs.find(p=>p.intake_mode==='WINDOW'&&p.ends_on!>='2026-11-01')!;
 const text=calendarText({...p,title:'한글'.repeat(100)+'\nBEGIN:VALARM',schedule_note:'가,나;다\\라'},'2026-11-01')!;
 expect(text).not.toContain('\r\nBEGIN:VALARM');expect(text.replace(/\r\n /g,'')).toContain('가\\,나\\;다\\\\라');
 for(const line of text.split('\r\n'))expect(new TextEncoder().encode(line).length).toBeLessThanOrEqual(75);
});
