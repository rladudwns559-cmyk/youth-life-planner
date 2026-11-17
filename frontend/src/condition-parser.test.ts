import {describe,it,expect} from 'vitest';
import {parseConditions,describeParsed} from './condition-parser';

const P=(t:string)=>parseConditions(t,2026);

describe('reading a sentence into conditions',()=>{
  it('reads the usual demo sentence',()=>{
    expect(P('안산 사는 24살 대학생이고 월세 살아요')).toMatchObject({province:'경기',city:'안산시',age:'24',school:'univ_student',rent:'yes'});
  });
  it('reads province with city, wards and full names',()=>{
    expect(P('경기도 수원시 팔달구에 살아요')).toMatchObject({province:'경기',city:'수원시 팔달구'});
    expect(P('안산시 단원구 거주')).toMatchObject({province:'경기',city:'안산시 단원구'});
    expect(P('서울 마포구 직장인 29세')).toMatchObject({province:'서울',city:'마포구',employment:'employed',age:'29'});
    expect(P('부산진구 살아요')).toMatchObject({province:'부산',city:'부산진구'});
    expect(P('서울에 살아요')).toMatchObject({province:'서울'});
    expect(P('서울에 살아요').city).toBeUndefined();
  });
  it('tells 광주광역시 from 경기 광주시 and asks when a district name is shared',()=>{
    expect(P('광주 사는 취준생')).toMatchObject({province:'광주',employment:'unemployed'});
    expect(P('광주 사는 취준생').city).toBeUndefined();
    expect(P('경기 광주 살아요')).toMatchObject({province:'경기',city:'광주시'});
    expect(P('광주 광산구에 살아요')).toMatchObject({province:'광주',city:'광산구'});
    const shared=P('중구에 살아요');
    expect(shared.province).toBeUndefined();
    expect(shared.notes.join(' ')).toMatch(/여러 지역에 있어요/);
    expect(P('대구 중구에 살아요')).toMatchObject({province:'대구',city:'중구'});
  });
  it('does not read everyday words as places',()=>{
    expect(P('남동생이랑 같이 살아요').city).toBeUndefined();
    expect(P('고양이 키우는 대학생').city).toBeUndefined();
    expect(P('예산 소진 전에 신청하고 싶어요').city).toBeUndefined();
    expect(P('예산군에 살아요')).toMatchObject({province:'충남',city:'예산군'});
    expect(P('경기가 안 좋아서 걱정이에요').province).toBeUndefined();
  });
  it('reads ages in several forms',()=>{
    expect(P('만 27세').age).toBe('27');
    expect(P('스물다섯 살').age).toBe('25');
    expect(P('서른 살').age).toBe('30');
    const born=P('2002년생');
    expect(born.age).toBe('24');
    expect(born.notes.join(' ')).toMatch(/생일이 아직 안 지났다면 만 23세/);
    expect(P('월세 50만원 내요').age).toBeUndefined();
  });
  it('reads work, schooling, housing and marriage',()=>{
    expect(P('대학생인데 알바해요')).toMatchObject({school:'univ_student',employment:'employed'});
    expect(P('졸업 예정인 취준생')).toMatchObject({school:'univ_expected',employment:'unemployed'});
    expect(P('대학 졸업하고 프리랜서')).toMatchObject({school:'univ_grad',employment:'self_employed'});
    expect(P('고3이에요')).toMatchObject({school:'hs_student'});
    expect(P('전세 살아요').rent).toBe('no');
    expect(P('월세 아니에요').rent).toBe('no');
    expect(P('신혼부부예요').marriage).toBe('married');
    expect(P('미혼 직장인').marriage).toBe('single');
    const plan=P('결혼 예정이에요');
    expect(plan.marriage).toBe('single');
    expect(plan.notes.join(' ')).toMatch(/혼인신고/);
  });
  it('says so when nothing was understood, and describes what was',()=>{
    expect(P('안녕하세요').notes.join(' ')).toMatch(/알아들은 조건이 없어요/);
    expect(describeParsed(P('안산 사는 24살 대학생이고 월세 살아요'))).toEqual([
      {label:'지역',value:'경기 안산시'},{label:'나이',value:'만 24세'},{label:'월세',value:'월세 거주'},{label:'학력',value:'대학 재학'},
    ]);
  });
});
