import {render,screen,within,fireEvent,act} from '@testing-library/react';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import OntongPolicies from './OntongPolicies';
import RegionalPrograms from './RegionalPrograms';
import {schoolFit,marriageFit,rankPolicies,leftOut,gapText,schoolText,marriageText,type OntongPolicy,type OntongPolicyList} from './ontong-policies';
import {PROFILE_KEY,readProfile} from './support-profile';

beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-17T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});

const AS_OF='2026-11-17';
const base:OntongPolicy={id:'P0',title:'정책',category:'일자리',subcategory:'취업',org:'안산시',summary:'요약',regions:['*'],age:null,jobs:null,income:null,extra:null,apply:{mode:'ALWAYS'},url:'',apply_url:null,updated:null};
const P=(o:Partial<OntongPolicy>):OntongPolicy=>({...base,...o,url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/'+(o.id??base.id)});
const source={title:'온통청년 청년정책 Open API',institution:'한국고용정보원',attribution:'출처: 온통청년(한국고용정보원)',url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch'};
const list=(policies:OntongPolicy[]):OntongPolicyList=>({fetched_on:AS_OF,source,total:policies.length,policies});

const data=[
  P({id:'ANY',title:'누구나 정책'}),
  P({id:'GRAD',title:'졸업생 취업 정책',school:{groups:['univ_grad'],other:false}}),
  P({id:'STUD',title:'대학생 장학 정책',school:{groups:['univ_student','univ_expected'],other:false}}),
  P({id:'NEWLY',title:'신혼부부 주거 정책',marriage:'married'}),
  P({id:'SINGLE',title:'미혼 청년 정책',marriage:'single'}),
  P({id:'MIX',title:'기타 학력 정책',school:{groups:['hs_grad'],other:true}}),
];

describe('schooling and marriage',()=>{
  it('compare like the other conditions, and treat missing data as no limit',()=>{
    expect(schoolFit(data[1],'univ_grad')).toBe('PASS');
    expect(schoolFit(data[1],'univ_student')).toBe('FAIL');
    expect(schoolFit(data[1],'unknown')).toBe('UNKNOWN');
    expect(schoolFit(data[5],'univ_grad')).toBe('UNKNOWN');
    expect(schoolFit(data[0],'univ_grad')).toBe('PASS');
    expect(marriageFit(data[3],'married')).toBe('PASS');
    expect(marriageFit(data[3],'single')).toBe('FAIL');
    expect(marriageFit(data[3],undefined)).toBe('UNKNOWN');
    expect(schoolText(data[2])).toBe('대학 재학 · 대학 졸업 예정');
    expect(marriageText(data[3])).toBe('기혼 대상');
  });
  it('leave out clashing policies and say what a graduation or marriage would open',()=>{
    const profile={province:'경기',city:'안산시',age:'24',employment:'unknown',school:'univ_student',marriage:'single'};
    expect(rankPolicies(data,profile,AS_OF).map(r=>r.p.id).sort()).toEqual(['ANY','MIX','SINGLE','STUD']);
    const {excluded,openings}=leftOut(data,profile,AS_OF);
    expect(excluded.map(r=>r.p.id).sort()).toEqual(['GRAD','NEWLY']);
    expect(gapText(excluded.find(r=>r.p.id==='GRAD')!,profile)).toEqual(['대학 졸업 대상 · 지금 대학 재학']);
    expect(gapText(excluded.find(r=>r.p.id==='NEWLY')!,profile)).toEqual(['기혼 대상 · 지금 미혼']);
    expect(openings.map(o=>[o.label,o.policies.map(p=>p.id)])).toEqual([['대학을 졸업하면',['GRAD']],['결혼하면',['NEWLY']]]);
  });
  it('show on the card and in the left-out box',async()=>{
    await act(async()=>{render(<OntongPolicies profile={{province:'경기',city:'안산시',age:'24',employment:'unknown',school:'univ_student',marriage:'single'}} asOf={AS_OF} data={list(data)}/>);});
    const card=screen.getByRole('heading',{level:4,name:'대학생 장학 정책'}).closest('li')!;
    expect(within(card).getByText('대학 재학 · 대학 졸업 예정')).toBeVisible();
    expect(within(card).getByText(/학력 일치/)).toBeVisible();
    const box=screen.getByText(/조건이 달라 뺀 정책 2건/).closest('details')!;
    fireEvent.click(within(box).getByText(/조건이 달라 뺀 정책 2건/));
    expect(within(box).getByText(/학력 때문에 1건, 혼인 여부 때문에 1건/)).toBeVisible();
    expect(within(box).getByText('대학을 졸업하면')).toBeVisible();
    expect(within(box).getByText('결혼하면')).toBeVisible();
  });
});

describe('inputs on the support page',()=>{
  it('offers schooling and marriage, explains their scope and remembers them when asked',()=>{
    render(<RegionalPrograms/>);
    expect(screen.getByText(/학력과 혼인 여부는 아래 ‘온통청년 청년정책’을 좁힐 때만 써요/)).toBeVisible();
    fireEvent.change(screen.getByLabelText('학력'),{target:{value:'univ_expected'}});
    fireEvent.change(screen.getByLabelText('혼인 여부'),{target:{value:'married'}});
    expect(localStorage.getItem(PROFILE_KEY)).toBeNull();
    fireEvent.click(screen.getByLabelText('이 기기에 내 조건 기억하기'));
    expect(readProfile()).toMatchObject({school:'univ_expected',marriage:'married'});
  });
  it('drops unknown stored values',()=>{
    localStorage.setItem(PROFILE_KEY,JSON.stringify({province:'',city:'',age:'',employment:'unknown',rent:'unknown',school:'phd-ish',marriage:'maybe'}));
    expect(readProfile()).toMatchObject({school:'unknown',marriage:'unknown'});
  });
});
