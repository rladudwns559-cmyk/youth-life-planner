import {render,screen,within,fireEvent} from '@testing-library/react';
import {describe,it,expect} from 'vitest';
import OntongPolicies from './OntongPolicies';
import {regionFit,ageFit,jobFit,looksKnown,rankPolicies,ageText,jobText,regionText,type OntongPolicy,type OntongPolicyList} from './ontong-policies';
import file from './public-data/youth-policies.json';

const AS_OF='2026-11-16';
const base:OntongPolicy={id:'P0',title:'정책',category:'주거',subcategory:'주거비 지원',org:'안산시',summary:'월 20만원',regions:['*'],age:null,jobs:null,income:null,extra:null,apply:{mode:'ALWAYS'},url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/P0',apply_url:null,updated:'2026-11-13'};
const P=(o:Partial<OntongPolicy>):OntongPolicy=>({...base,...o});
const source={title:'온통청년 청년정책 Open API',institution:'한국고용정보원',attribution:'출처: 온통청년(한국고용정보원)',url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch'};
const list=(policies:OntongPolicy[]):OntongPolicyList=>({fetched_on:AS_OF,source,total:policies.length,policies});

describe('matching',()=>{
  it('reads regions for nationwide, province, city, ward and partial coverage',()=>{
    expect(regionFit(P({regions:['*']}),'','')).toBe('PASS');
    expect(regionFit(P({regions:['경기']}),'','')).toBe('FAIL');
    expect(regionFit(P({regions:['경기']}),'경기','수원시')).toBe('PASS');
    expect(regionFit(P({regions:['경기|안산시']}),'경기','안산시 단원구')).toBe('PASS');
    expect(regionFit(P({regions:['경기|안산시 단원구']}),'경기','안산시')).toBe('UNKNOWN');
    expect(regionFit(P({regions:['경기|안산시']}),'경기','')).toBe('UNKNOWN');
    expect(regionFit(P({regions:['경기|안산시']}),'경기','수원시')).toBe('FAIL');
    expect(regionFit(P({regions:['부산']}),'경기','안산시')).toBe('FAIL');
  });
  it('reads age and employment',()=>{
    expect(ageFit(P({age:[19,34]}),'25')).toBe('PASS');
    expect(ageFit(P({age:[19,34]}),'35')).toBe('FAIL');
    expect(ageFit(P({age:[19,null]}),'50')).toBe('PASS');
    expect(ageFit(P({age:[19,34]}),'')).toBe('UNKNOWN');
    expect(jobFit(P({jobs:{groups:['unemployed'],other:false}}),'unemployed')).toBe('PASS');
    expect(jobFit(P({jobs:{groups:['unemployed'],other:false}}),'employed')).toBe('FAIL');
    expect(jobFit(P({jobs:{groups:['unemployed'],other:true}}),'employed')).toBe('UNKNOWN');
    expect(jobFit(P({jobs:{groups:['unemployed'],other:false}}),'unknown')).toBe('UNKNOWN');
  });
  it('describes conditions in words',()=>{
    expect(ageText(P({age:[19,34]}))).toBe('만 19~34세');
    expect(ageText(P({age:[null,39]}))).toBe('만 39세 이하');
    expect(jobText(P({jobs:{groups:['employed','unemployed'],other:true}}))).toBe('근로 중 · 일하지 않음 · 기타');
    expect(regionText(P({regions:['경기|안산시','경기|수원시']}))).toBe('경기 안산시 외 1곳');
    expect(regionText(P({regions:['광주','전남']}),'전남')).toBe('전남 외 1곳');
  });
  it('skips titles that match hand-checked programs',()=>{
    expect(looksKnown('2026년 안산시 청년 월세 지원사업',['안산시 청년 월세 지원사업'])).toBe(true);
    expect(looksKnown('부산 청년 면접수당',['안산시 청년 월세 지원사업'])).toBe(false);
  });
  it('ranks local first, then by closing date, and drops clashes and closed periods',()=>{
    const rows=rankPolicies([
      P({id:'nation',title:'전국 정책',regions:['*'],apply:{mode:'PERIOD',start:'2026-11-01',end:'2026-11-20'}}),
      P({id:'city-late',title:'안산 늦은 마감',regions:['경기|안산시'],apply:{mode:'PERIOD',start:'2026-11-01',end:'2026-12-31'}}),
      P({id:'city-soon',title:'안산 빠른 마감',regions:['경기|안산시'],apply:{mode:'PERIOD',start:'2026-11-01',end:'2026-11-18'}}),
      P({id:'province',title:'경기 상시',regions:['경기']}),
      P({id:'old',title:'끝난 정책',regions:['경기'],apply:{mode:'PERIOD',start:'2026-01-01',end:'2026-11-15'}}),
      P({id:'older',title:'나이 다름',regions:['경기'],age:[19,24]}),
      P({id:'busan',title:'부산 정책',regions:['부산']}),
    ],{province:'경기',city:'안산시 단원구',age:'29',employment:'unknown'},AS_OF);
    expect(rows.map(r=>r.p.id)).toEqual(['city-soon','city-late','province','nation']);
    expect(rows[0].job).toBe('PASS');
  });
});

describe('the policy section',()=>{
  const data=list([
    P({id:'A',title:'안산 청년 면접 정장 대여',regions:['경기|안산시'],age:[19,39],jobs:{groups:['unemployed'],other:false},income:'기준 중위소득 150% 이하',extra:'관내 6개월 거주',apply:{mode:'PERIOD',start:'2026-11-01',end:'2026-11-30'},apply_url:'https://www.ansan.go.kr/x',url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/A'}),
    ...Array.from({length:9},(_,i)=>P({id:'N'+i,title:'전국 정책 '+i})),
  ]);
  it('shows matching policies with their conditions, links and the source',()=>{
    render(<OntongPolicies profile={{province:'경기',city:'안산시',age:'25',employment:'unemployed'}} asOf={AS_OF} data={data}/>);
    const section=screen.getByRole('region',{name:/온통청년에 등록된 청년정책 10건 더 보기/});
    const card=within(section).getByRole('heading',{name:'안산 청년 면접 정장 대여'}).closest('li')!;
    expect(within(card).getByText('신청 마감 11월 30일 · D-14')).toBeVisible();
    expect(within(card).getByText('만 19~39세')).toBeVisible();
    expect(within(card).getByText('기준 중위소득 150% 이하')).toBeVisible();
    expect(within(card).getByText('관내 6개월 거주')).toBeVisible();
    expect(within(card).getByText('지역 일치 · 나이 일치 · 취업 일치')).toBeVisible();
    expect(within(card).getByRole('link',{name:'안산 청년 면접 정장 대여 온통청년에서 보기'})).toHaveAttribute('href','https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/A');
    expect(within(card).getByRole('link',{name:'안산 청년 면접 정장 대여 신청·안내 페이지'})).toHaveAttribute('target','_blank');
    expect(within(section).getByText(/출처: 온통청년\(한국고용정보원\)/)).toHaveTextContent('2026-11-16 수집');
    expect(within(section).getByText(/직접 읽고 확인한 사업은 아니에요/)).toBeVisible();
  });
  it('shows eight first and more on request',()=>{
    render(<OntongPolicies profile={{province:'경기',city:'안산시',age:'',employment:'unknown'}} asOf={AS_OF} data={data}/>);
    expect(screen.getAllByRole('heading',{level:4})).toHaveLength(8);
    fireEvent.click(screen.getByRole('button',{name:'정책 2건 더 보기'}));
    expect(screen.getAllByRole('heading',{level:4})).toHaveLength(10);
  });
  it('drops policies that clash and says so when none are left',()=>{
    render(<OntongPolicies profile={{province:'경기',city:'안산시',age:'25',employment:'employed'}} asOf={AS_OF} data={list([data.policies[0]])}/>);
    expect(screen.getByText(/남은 정책이 없어요/)).toBeVisible();
  });
  it('renders nothing while the stored list is empty',()=>{
    const {container}=render(<OntongPolicies profile={{province:'',city:'',age:'',employment:'unknown'}} asOf={AS_OF} data={list([])}/>);
    expect(container).toBeEmptyDOMElement();
  });
  it('keeps only display fields with the attribution in the stored file',()=>{
    const f=file as unknown as OntongPolicyList;
    expect(f.source.attribution).toBe('출처: 온통청년(한국고용정보원)');
    expect(f.total).toBe(f.policies.length);
    for(const p of f.policies.slice(0,200)){
      expect(p.url).toBe('https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/'+p.id);
      expect(p.regions.length).toBeGreaterThan(0);
    }
  });
});
