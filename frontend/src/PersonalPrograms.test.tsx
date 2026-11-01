import {render,screen,fireEvent,within} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import RegionalPrograms,{readPersonalDecision,validAge} from './RegionalPrograms';
const change=(name:string,value:string)=>fireEvent.change(screen.getByLabelText(name),{target:{value}});
const card=(id:string)=>document.querySelector(`[data-support-id="${id}"]`) as HTMLElement|null;
const profile={age:'25',employment:'unemployed',rent:'yes'};
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('No profile transmission');}));});
afterEach(()=>vi.useRealTimers());

it('automatically changes housing candidates with rent, keeping jeonse moving assistance',()=>{
 render(<RegionalPrograms/>);change('모집 상태','ALL');change('관심·거주 광역지역','경기');change('시·군·구','안산시');change('현재 만 나이','25');change('현재 취업 상태','unemployed');change('현재 월세 거주 여부','yes');
 fireEvent.click(screen.getByRole('button',{name:'월세·주거'}));
 expect(card('KR-YOUTH-RENT-2026')).toBeVisible();expect(card('ANSAN-YOUTH-MOVE-FEE-2026')).toBeVisible();
 expect(within(card('KR-YOUTH-RENT-2026')!).getByText('입력 조건 3개 일치 · 나머지 확인')).toBeVisible();
 change('현재 월세 거주 여부','no');expect(card('KR-YOUTH-RENT-2026')).toBeNull();expect(card('ANSAN-YOUTH-MOVE-FEE-2026')).toBeVisible();
 fireEvent.click(screen.getByRole('checkbox',{name:'현재 조건과 다른 사업도 보기'}));expect(card('KR-YOUTH-RENT-2026')).toBeVisible();
 expect(within(card('KR-YOUTH-RENT-2026')!).getByText('현재 입력과 다른 조건이 있어요')).toBeVisible();
 expect(fetch).not.toHaveBeenCalled();expect(localStorage.length).toBe(0);
});
it('shows birthday overlap UNKNOWN instead of excluding 18 or 35 year olds',()=>{
 expect(readPersonalDecision('KR-YOUTH-RENT-2026','경기|안산시',{...profile,age:'18'}).age).toBe('UNKNOWN');
 expect(readPersonalDecision('KR-YOUTH-RENT-2026','경기|안산시',{...profile,age:'35'}).age).toBe('UNKNOWN');
 expect(readPersonalDecision('KR-YOUTH-RENT-2026','경기|안산시',{...profile,age:'36'}).age).toBe('FAIL');
});
it('filters worker-only current relevance while preserving exam and short-worker exceptions',()=>{
 render(<RegionalPrograms/>);change('모집 상태','ALL');change('관심·거주 광역지역','경기');change('시·군·구','안산시');change('현재 취업 상태','unemployed');
 change('사업·지원내용 검색','복지포인트');expect(card('GG-YOUTH-WELFARE-POINTS-2026')).toBeNull();
 change('현재 취업 상태','employed');expect(card('GG-YOUTH-WELFARE-POINTS-2026')).toBeVisible();
 change('사업·지원내용 검색','응시료');expect(card('ANSAN-YOUTH-EXAM-FEE-2026')).toBeVisible();
 expect(readPersonalDecision('ANSAN-YOUTH-EXAM-FEE-2026','경기|안산시',{...profile,employment:'employed'}).employment).toBe('UNKNOWN');
 expect(readPersonalDecision('SEOUL-YOUTH-ALLOWANCE-2026','서울',{...profile,employment:'employed'}).employment).toBe('UNKNOWN');
});
it('never infers household income, assets or overall eligibility from matched inputs',()=>{
 render(<RegionalPrograms/>);change('모집 상태','ALL');change('사업·지원내용 검색','청년월세 지원사업');change('현재 만 나이','25');change('현재 월세 거주 여부','yes');
 const c=card('KR-YOUTH-RENT-2026')!;expect(within(c).getByText('지원자격 추가 확인 필요')).toBeVisible();expect(c).toHaveTextContent('가구소득·재산·거주기간');
 for(const id of ['KR-YOUTH-RENT-2026','KR-YOUTH-HOUSING','GG-YOUTH-WELFARE-POINTS-2026']){
  const r=readPersonalDecision(id,'경기|안산시',profile);expect(r.summary.eligibility).toBe('UNKNOWN');expect(r.summary.benefit_applied_krw).toBe(0);
 }
});
it('missing and invalid fields remain unknown and reset clears every personal field',()=>{
 render(<RegionalPrograms/>);change('모집 상태','ALL');change('현재 만 나이','121');expect(screen.getByRole('alert')).toBeVisible();
 expect(readPersonalDecision('KR-YOUTH-RENT-2026','*',{age:'121',employment:'unknown',rent:'unknown'}).age).toBe('UNKNOWN');
 for(const value of ['-1','1.5','NaN','1e2','121'])expect(validAge(value)).toBe(false);
 change('현재 취업 상태','employed');change('현재 월세 거주 여부','yes');fireEvent.click(screen.getByRole('button',{name:'조건 초기화'}));
 expect(screen.getByLabelText('현재 만 나이')).toHaveValue(null);expect(screen.getByLabelText('현재 취업 상태')).toHaveValue('unknown');expect(screen.getByLabelText('현재 월세 거주 여부')).toHaveValue('unknown');
});
it('keeps employment and housing unknown for rules not yet structured',()=>{
 const r=readPersonalDecision('JEJU-TAMRA-YOUTH-ARRIVAL-2026','제주',profile);expect([r.age,r.employment,r.rent]).toEqual(['UNKNOWN','UNKNOWN','UNKNOWN']);
});
it('exposes official evidence and reason for the current condition comparison',()=>{
 render(<RegionalPrograms/>);change('모집 상태','ALL');change('사업·지원내용 검색','응시료');change('관심·거주 광역지역','경기');change('시·군·구','안산시');change('현재 만 나이','25');change('현재 취업 상태','employed');
 const c=card('ANSAN-YOUTH-EXAM-FEE-2026')!;fireEvent.click(within(c).getByText('지원 조건·신청 일정·공식 근거'));
 expect(within(c).getByText(/2026 공고 생년범위와 현행 안내/)).toBeVisible();expect(within(c).getAllByRole('link',{name:/조건 비교 근거/}).length).toBeGreaterThan(0);
});
it('shows new official programs without reopening closed intake or proving eligibility',()=>{
 render(<RegionalPrograms/>);change('모집 상태','ALL');change('관심·거주 광역지역','서울');change('현재 만 나이','23');change('사업·지원내용 검색','문화패스');
 const c=card('SEOUL-YOUTH-CULTURE-PASS-2026')!;expect(c).toBeVisible();expect(within(c).getByText('공식 접수중 확인 · 잔여 확인')).toBeVisible();
 change('사업·지원내용 검색','부동산');expect(within(card('SEOUL-YOUTH-MOVE-FEE-2026-H2')!).getByText('확인한 회차 마감')).toBeVisible();
});
it('never extrapolates age past precomputed dates or invents results for missing IDs',()=>{
 expect(readPersonalDecision('KR-YOUTH-RENT-2026','서울',profile,'2027-11-02').age).toBe('UNKNOWN');
 expect(readPersonalDecision('missing','서울',profile).summary.eligibility).toBe('UNKNOWN');
 expect(readPersonalDecision('missing','서울',profile).summary.matched_count).toBe(0);
});
