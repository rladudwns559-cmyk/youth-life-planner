import {render,screen,fireEvent,within} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import RegionalPrograms,{openingScenarios,readPersonalDecision,type PersonalInput} from './RegionalPrograms';
import web from './public-data/current-support-web.json';

const AS_OF='2026-11-14';
beforeEach(()=>{localStorage.clear();window.location.hash='';vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-14T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();window.location.hash='';});

const fails=(id:string,input:PersonalInput)=>{const m=readPersonalDecision(id,'*',input,AS_OF);return [m.age,m.employment,m.rent].filter(s=>s==='FAIL').length;};

it('lists only programs that fail now and have no failing condition after one change',()=>{
  const input={age:'36',employment:'employed',rent:'no'};
  const excluded=web.programs.filter(p=>fails(p.program_id,input)>0);
  const scenarios=openingScenarios(excluded,'*',input,AS_OF);
  expect(scenarios.length).toBeGreaterThan(0);
  for(const sc of scenarios){
    expect(sc.programs.length).toBeGreaterThan(0);
    const changed:PersonalInput=sc.key==='rent-yes'?{...input,rent:'yes'}:sc.key==='age-next'?{...input,age:'37'}:{...input,employment:sc.key.replace('employment-','')};
    for(const p of sc.programs){expect(fails(p.program_id,input)).toBeGreaterThan(0);expect(fails(p.program_id,changed)).toBe(0);}
  }
  expect(scenarios.map(s=>s.key)).not.toContain('employment-employed');  // never the current state
  expect(scenarios.map(s=>s.key)).not.toContain('rent-no');
});

it('varies only the conditions the visitor actually set',()=>{
  const excluded=web.programs.slice(0,200);
  expect(openingScenarios(excluded,'*',{age:'',employment:'unknown',rent:'unknown'},AS_OF)).toEqual([]);
  const onlyRent=openingScenarios(excluded,'*',{age:'',employment:'unknown',rent:'no'},AS_OF);
  expect(onlyRent.every(s=>s.key==='rent-yes')).toBe(true);
});

it('shows the scenarios in the results with links to each program',()=>{
  render(<RegionalPrograms browse={false}/>);
  fireEvent.change(screen.getByLabelText('현재 만 나이'),{target:{value:'36'}});
  fireEvent.change(screen.getByLabelText('현재 취업 상태'),{target:{value:'employed'}});
  fireEvent.change(screen.getByLabelText('현재 월세 거주 여부'),{target:{value:'no'}});
  fireEvent.click(screen.getByRole('button',{name:'내 조건으로 찾기 →'}));
  const section=screen.getByRole('region',{name:'조건이 바뀌면 열리는 사업'});
  const summary=section.querySelector('summary')!;
  expect(summary).toHaveTextContent(/개 더$/);
  const link=within(section).getAllByRole('link')[0];
  expect(link.getAttribute('href')).toMatch(/^#\/programs\/item\//);
});
