import {render,screen,fireEvent} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import RegionalPrograms from './RegionalPrograms';
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-03T03:00:00Z'));});
afterEach(()=>vi.useRealTimers());
const change=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});
it.each([
 {city:'광주시',query:'AI 취업코칭',title:'광주시 AI 취업코칭 · 11월 이용권',pid:'EXT3-GG-12344',age:'25',employment:'unemployed'},
 {city:'용인시',query:'실무 PPT',title:'용인 재직자를 위한 실무 PPT 클래스',pid:'EXT3-GG-12382',age:'25',employment:'employed'},
 {city:'여주시',query:'신혼부부',title:'여주 청년 신혼부부 전세자금 대출이자 지원 · 추가 모집',pid:'EXT3-GG-12349',age:'50',employment:'employed'},
])('ranks current matching new support before alternatives for $city in both views',c=>{
 const {rerender}=render(<RegionalPrograms browse={false}/>);
 change('관심·거주 광역지역','경기');change('시·군·구',c.city);change('현재 만 나이',c.age);
 change('현재 취업 상태',c.employment);change('현재 월세 거주 여부','no');
 change('모집 상태','OPEN');change('사업·지원내용 검색',c.query);
 fireEvent.click(screen.getByRole('button',{name:/내 조건으로 찾기/}));
 const first=screen.getByRole('dialog').querySelector('article')!;
 expect(first.querySelector('h3')).toHaveTextContent(c.title);
 expect(first).toHaveTextContent('공식 접수중 확인');expect(first).toHaveTextContent('추가 확인');
 expect(first).toHaveTextContent('우선 검토 추천 01');
 if(c.city==='여주시')expect(first).toHaveTextContent('본인 나이만으로 판정하지 않음');
 fireEvent.click(screen.getByRole('button',{name:'결과 창 닫기'}));
 rerender(<RegionalPrograms browse listPage/>);
 const card=document.querySelector('[data-support-id]')!;
 expect(card).toHaveAttribute('data-support-id',c.pid);
 expect(card).toHaveTextContent('지원자격 추가 확인 필요');
});
it('removes a new course from open matches when current age conflicts',()=>{
 render(<RegionalPrograms browse={false}/>);
 change('관심·거주 광역지역','경기');change('시·군·구','용인시');change('현재 만 나이','17');
 change('모집 상태','OPEN');change('사업·지원내용 검색','실무 PPT');
 fireEvent.click(screen.getByRole('button',{name:/내 조건으로 찾기/}));
 const dialog=screen.getByRole('dialog');
 expect(dialog.querySelector('article')).toBeNull();
 expect(dialog).toHaveTextContent('현재 필터에 맞는 안내가 없어요.');
});
