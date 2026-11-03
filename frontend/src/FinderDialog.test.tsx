import {fireEvent,render,screen,within} from '@testing-library/react';
import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import RegionalPrograms from './RegionalPrograms';

beforeEach(()=>{vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-03T03:00:00Z'));});
afterEach(()=>{vi.useRealTimers();});
const change=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});
it('opens the public finder with applied conditions and shares the comparison selection',()=>{
  render(<RegionalPrograms/>);
  change('관심·거주 광역지역','서울');change('현재 만 나이','23');change('사업·지원내용 검색','인생설계');
  fireEvent.click(screen.getByRole('button',{name:/내 조건으로 찾기/}));
  const dialog=within(screen.getByRole('dialog'));
  expect(dialog.getByText('입력 조건 2개 일치')).toBeVisible();
  fireEvent.click(dialog.getByRole('checkbox',{name:/비교에 담기/}));
  fireEvent.click(dialog.getByRole('button',{name:/담은 사업 비교하기/}));
  expect(dialog.getByRole('region',{name:'지원사업 비교 표'})).toBeVisible();
  fireEvent.click(dialog.getByRole('button',{name:'결과 창 닫기'}));
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(screen.getByRole('button',{name:'사업 비교하기 (1/3)'})).toBeVisible();
});
it('opens an empty comparison with a path to choose programs, then searches savings with separate inputs',()=>{
  render(<RegionalPrograms/>);fireEvent.click(screen.getByRole('button',{name:'사업 비교하기 (0/3)'}));
  const d=within(screen.getByRole('dialog'));expect(d.getByText('어떤 사업을 비교할까요?')).toBeVisible();
  fireEvent.click(d.getByRole('button',{name:'적금·예금 찾기'}));
  fireEvent.change(d.getByLabelText('월 납입액 (원)'),{target:{value:'200000'}});
  expect(d.getByRole('status')).toHaveTextContent('69개');
  fireEvent.change(d.getByLabelText('저축 방식'),{target:{value:'DEPOSIT'}});
  expect(d.getByLabelText('예치할 목돈 (원)')).toHaveValue('');
});
it('maps an administrative ward to a city-wide notice, without leaking it to a different city',()=>{
  render(<RegionalPrograms/>);change('관심·거주 광역지역','경기');change('모집 상태','ALL');change('사업·지원내용 검색','이사비');
  change('시·군·구','안산시 단원구');expect(document.querySelector('[data-support-id="ANSAN-YOUTH-MOVE-FEE-2026"]')).toBeVisible();
  change('시·군·구','평택시');expect(document.querySelector('[data-support-id="ANSAN-YOUTH-MOVE-FEE-2026"]')).toBeNull();
});

