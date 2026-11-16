import {render,screen,within,fireEvent} from '@testing-library/react';
import {describe,it,expect} from 'vitest';
import DailyTrend from './DailyTrend';
import ontongFile from './public-data/metrics-ontong.json';
import supportFile from './public-data/metrics-support.json';

const files={
  ontong:{days:[{date:'2026-11-16',policies:2034,new:null,removed:null,centers:236},{date:'2026-11-17',policies:2040,new:9,removed:3,centers:236}]},
  support:{days:[{date:'2026-11-15',checked:254,renewed:97,closed_signal:3,not_matched:154},{date:'2026-11-16',checked:244,renewed:94,closed_signal:3,not_matched:147}]},
};

describe('daily update record',()=>{
  it('shows the span, one bar per day with its number, and a dash where there is nothing to compare',()=>{
    render(<DailyTrend files={files}/>);
    const section=screen.getByRole('region',{name:'매일 자동 갱신 기록'});
    expect(within(section).getByText(/11\/15부터 11\/17까지 3일 동안/)).toBeVisible();
    const renewed=within(section).getByText(/일치해서 갱신한 사업 수/).closest('figure')!;
    expect(within(renewed).getByText('97')).toBeVisible();
    const fresh=within(section).getByText('온통청년에 새로 올라온 정책 수').closest('figure')!;
    expect(within(fresh).getByText('–')).toBeVisible();
    expect(within(fresh).getByText('2026-11-16 첫 수집일이라 비교 대상 없음')).toBeInTheDocument();
    expect(within(fresh).getByText('9')).toBeVisible();
  });
  it('lists every day in a table',()=>{
    render(<DailyTrend files={files}/>);
    fireEvent.click(screen.getByText('일별 기록 표로 보기'));
    const table=screen.getByRole('table',{name:'날짜별 자동 갱신 결과'});
    expect(within(table).getAllByRole('row')).toHaveLength(1+3);
    const row=within(table).getByRole('row',{name:/2026-11-17/});
    expect(within(row).getAllByRole('cell').map(c=>c.textContent)).toEqual(['2040','9','3','236','–','–','–']);
  });
  it('marks a day that was run by hand on a PC',()=>{
    render(<DailyTrend files={{...files,support:{days:[{date:'2026-11-13',checked:268,renewed:119,closed_signal:3,not_matched:146,manual:true},...files.support.days]}}}/>);
    expect(screen.getByText(/‘PC’ 표시가 있는 날은 자동 작업을 만들기 전에 PC에서 직접 실행한 결과예요/)).toBeVisible();
    expect(screen.getByText('PC')).toBeVisible();
  });
  it('shows nothing without any record',()=>{
    const {container}=render(<DailyTrend files={{ontong:{days:[]},support:{days:[]}}}/>);
    expect(container).toBeEmptyDOMElement();
  });
  it('ships records with dates in order and the expected fields',()=>{
    for(const f of [ontongFile,supportFile]){
      const dates=f.days.map((d:{date:string})=>d.date);
      expect(dates).toEqual([...dates].sort());
      for(const d of dates)expect(d).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
    expect(supportFile.days.length).toBeGreaterThan(0);
  });
});
