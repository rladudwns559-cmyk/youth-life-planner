import {render,screen,fireEvent,within} from '@testing-library/react';
import {it,expect,beforeEach,afterEach,vi} from 'vitest';
import RegionalPrograms from './RegionalPrograms';
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T03:00:00Z'));});
afterEach(()=>vi.useRealTimers());
const change=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});
it.each(['내 조건으로 찾기 →','추천 결과 열기 ↗'])('requires at least one personal or region condition at %s',name=>{
 render(<RegionalPrograms browse={false}/>);
 change('사업·지원내용 검색','월세');
 fireEvent.click(screen.getByRole('button',{name}));
 const prompt=screen.getByRole('dialog',{name:'내 조건을 먼저 입력해 주세요'});
 expect(prompt).toHaveTextContent('한 가지 이상');
 expect(screen.queryByRole('dialog',{name:'내 조건으로 찾은 결과'})).toBeNull();
 fireEvent.click(within(prompt).getByRole('button',{name:'조건 입력하기'}));
 expect(screen.queryByRole('dialog')).toBeNull();
 change('관심·거주 광역지역','경기');
 fireEvent.click(screen.getByRole('button',{name}));
 expect(screen.getByRole('dialog',{name:'내 조건으로 찾은 결과'})).toBeVisible();
});
it('allows a single known profile field while leaving unknown fields empty',()=>{
 render(<RegionalPrograms browse={false}/>);
 change('현재 취업 상태','unemployed');
 fireEvent.click(screen.getByRole('button',{name:'내 조건으로 찾기 →'}));
 expect(screen.getByRole('dialog',{name:'내 조건으로 찾은 결과'})).toBeVisible();
 expect(screen.getByLabelText('현재 만 나이')).toHaveValue(null);
});
it('searches the dedicated catalog with multiple terms and preserves profile and category',()=>{
 const {rerender}=render(<RegionalPrograms browse={false}/>);
 change('관심·거주 광역지역','경기');change('시·군·구','의정부시');change('현재 만 나이','25');
 rerender(<RegionalPrograms listPage/>);
 const search=within(screen.getByRole('search',{name:'지원사업 검색'}));
 fireEvent.change(search.getByRole('searchbox'),{target:{value:'의정부   면접'}});
 expect(screen.getAllByRole('article')).toHaveLength(1);
 expect(screen.getAllByRole('article')[0]).toHaveTextContent('의정부 면접키트 · 면접도서 구입비 지원');
 fireEvent.click(screen.getByRole('button',{name:'월세·주거'}));
 expect(screen.getByText('등록한 자료 중 표시할 사업이 없어요.')).toBeVisible();
 fireEvent.click(search.getByRole('button',{name:'검색어 지우기'}));
 expect(screen.getByRole('button',{name:'월세·주거'})).toHaveAttribute('aria-pressed','true');
 expect(screen.getByText(/의정부시 · 만 25세/)).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'전체 분야'}));
 expect(screen.getAllByRole('article').length).toBeGreaterThan(1);
});

