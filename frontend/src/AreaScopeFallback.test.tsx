import { render, screen, fireEvent, within } from '@testing-library/react';
import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import RegionalPrograms from './RegionalPrograms';
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-01T12:00:00Z'));});
afterEach(()=>vi.useRealTimers());
const change=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});
function filter(){
 change('관심·거주 광역지역','경기');change('시·군·구','안산시 상록구');change('모집 상태','OPEN');
 change('현재 만 나이','24');change('현재 취업 상태','employed');change('현재 월세 거주 여부','yes');
}
function open(){fireEvent.click(screen.getByRole('button',{name:/내 조건으로 찾기/}));return within(screen.getByRole('dialog'));}
it('keeps the Ansan zero independent of wider notices and ranks both broader scopes before outside alternatives',()=>{
 const {rerender}=render(<RegionalPrograms browse={false}/>);filter();const d=open();
 expect(d.getByLabelText('안산시 상록구 공고 요약')).toHaveTextContent('대상 공고 0건');
 const titles=()=>d.getAllByRole('article').map(a=>a.querySelector('h3')?.textContent);
 expect(titles()).toEqual(['경기 고립·은둔청년 일상회복 지원','청년의 사회적 자립 지원강좌']);
 expect(d.getAllByRole('article')[0]).toHaveTextContent('취업 추가 확인');
 fireEvent.click(d.getByRole('checkbox',{name:/다른 지역 사업/}));
 expect(titles().slice(0,2)).toEqual(['경기 고립·은둔청년 일상회복 지원','청년의 사회적 자립 지원강좌']);
 expect(titles().length).toBeGreaterThan(2);
 fireEvent.click(d.getByRole('button',{name:'결과 창 닫기'}));
 rerender(<RegionalPrograms browse listPage/>);
 expect(screen.getAllByRole('article').slice(0,2).map(a=>a.getAttribute('data-support-id'))).toEqual(['GG-YOUTH-CONNECTION-SUPPORT-2026','KR-YOUTH-INDEPENDENT-LIVING-KMOOC-2026']);
});
it('does not silently broaden recruitment status when no wide notice matches a search',()=>{
 render(<RegionalPrograms browse={false}/>);filter();change('사업·지원내용 검색','국민내일배움카드');const d=open();
 expect(d.queryAllByRole('article')).toHaveLength(0);
 fireEvent.click(d.getByRole('button',{name:'공고상 신청기간·상시 안내까지 보기'}));
 expect(d.getAllByRole('article')[0]).toHaveTextContent('상시 제도 안내');expect(d.getAllByRole('article')[0]).not.toHaveTextContent('공식 접수중 확인');
});
it('keeps nationwide education but removes a known age mismatch from Gyeonggi',()=>{
 render(<RegionalPrograms browse={false}/>);filter();change('현재 만 나이','45');const d=open();
 expect(d.getAllByRole('article').map(a=>a.querySelector('h3')?.textContent)).toEqual(['청년의 사회적 자립 지원강좌']);
});

