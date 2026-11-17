import {render,screen,within,fireEvent,act,waitFor} from '@testing-library/react';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import HomeSummary from './HomeSummary';
import {encodeSaved,decodeSaved,savedFromHash,savedLink,SavedLinkTools,SavedImport} from './SavedLink';
import {ONTONG_SAVE_KEY,snapshot,readSaved} from './ontong-saved';
import {PROFILE_KEY} from './support-profile';
import {SUPPORT_SAVE_KEY,deadlineOf} from './SupportPlanner';
import RegionalPrograms from './RegionalPrograms';
import web from './public-data/current-support-web.json';
import type {OntongPolicy,OntongPolicyList} from './ontong-policies';

const AS_OF='2026-11-16';
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-16T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));window.location.hash='';});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();window.location.hash='';});

const base:OntongPolicy={id:'P0',title:'정책',category:'일자리',subcategory:'취업',org:'안산시',summary:'요약',regions:['*'],age:null,jobs:null,income:null,extra:null,apply:{mode:'ALWAYS'},url:'',apply_url:null,updated:null};
const P=(o:Partial<OntongPolicy>):OntongPolicy=>({...base,...o,url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/'+(o.id??base.id)});
const source={title:'온통청년 청년정책 Open API',institution:'한국고용정보원',attribution:'출처: 온통청년(한국고용정보원)',url:'https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch'};
const list=(policies:OntongPolicy[]):OntongPolicyList=>({fetched_on:AS_OF,source,total:policies.length,policies});

describe('home summary',()=>{
  it('stays hidden for someone who keeps nothing on this device',()=>{
    const {container}=render(<HomeSummary/>);
    expect(container).toBeEmptyDOMElement();
  });
  it('shows saved programs and policies closing within a week, closest first',()=>{
    const program=web.programs.find(p=>{const end=deadlineOf(p,AS_OF);return end&&end<='2026-11-23';})!;
    localStorage.setItem(SUPPORT_SAVE_KEY,JSON.stringify({favorites:[program.program_id],checks:[]}));
    localStorage.setItem(ONTONG_SAVE_KEY,JSON.stringify([snapshot(P({id:'S',title:'곧 끝나는 정책',apply:{mode:'PERIOD',start:'2026-11-01',end:'2026-11-17'}}))]));
    render(<HomeSummary/>);
    const section=screen.getByRole('region',{name:'오늘 확인할 것'});
    expect(within(section).getByText('일주일 안에 마감되는 관심 사업·정책').previousSibling).toHaveTextContent('2건');
    const links=within(section).getAllByRole('link').map(a=>a.textContent);
    expect(links).toContain('곧 끝나는 정책 ↗');
    expect(links).toContain(program.title);
    expect(within(section).getByText('11월 17일 · D-1')).toBeVisible();
    expect(within(section).queryByText(/기억한 조건/)).toBeNull();
  });
  it('counts fitting policies for remembered conditions',async()=>{
    localStorage.setItem(PROFILE_KEY,JSON.stringify({province:'경기',city:'안산시',age:'27',employment:'unemployed',rent:'unknown'}));
    render(<HomeSummary/>);
    const section=screen.getByRole('region',{name:'오늘 확인할 것'});
    expect(within(section).getByText(/이 기기에 기억한 조건: 경기 · 안산시 · 만 27세 · 현재 일하지 않음/)).toBeVisible();
    await waitFor(()=>expect(within(section).getByText('내 조건과 맞지 않는 것을 뺀 온통청년 정책').previousSibling?.textContent).toMatch(/^\d[\d,]*건$/),{timeout:5000});
    expect(within(section).getByRole('link',{name:'정책 보기 →'})).toHaveAttribute('href','#/programs/list');
  });
});

describe('saved-list link',()=>{
  it('round-trips program and policy numbers and rejects junk',()=>{
    const ids={programs:['GG-YOUTH-A','KR-B'],policies:['20261113005400214853']};
    expect(decodeSaved(encodeSaved(ids))).toEqual(ids);
    expect(savedFromHash('#/programs/list?saved='+encodeSaved(ids))).toEqual(ids);
    expect(decodeSaved('not-base64!!')).toBeNull();
    expect(decodeSaved(encodeSaved({programs:['<script>','ok-1'],policies:[]}))).toEqual({programs:['ok-1'],policies:[]});
    expect(decodeSaved(encodeSaved({programs:[],policies:[]}))).toBeNull();
    expect(savedLink(ids,'https://example.test/app/')).toBe('https://example.test/app/#/programs/list?saved='+encodeSaved(ids));
  });
  it('copies the link and shows it, with only numbers in it',async()=>{
    const write=vi.fn(()=>Promise.resolve());
    vi.stubGlobal('navigator',{...navigator,clipboard:{writeText:write}});
    render(<SavedLinkTools ids={{programs:['GG-A'],policies:['P1','P2']}}/>);
    await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'관심 목록 링크 만들기 (3)'}));});
    const url=(screen.getByLabelText('관심 목록 링크') as HTMLInputElement).value;
    expect(write).toHaveBeenCalledWith(url);
    expect(savedFromHash(url.slice(url.indexOf('#')))).toEqual({programs:['GG-A'],policies:['P1','P2']});
    expect(screen.getByRole('status')).toHaveTextContent('링크를 복사했어요');
  });
  it('is disabled with nothing saved',()=>{
    render(<SavedLinkTools ids={{programs:[],policies:[]}}/>);
    expect(screen.getByRole('button',{name:'관심 목록 링크 만들기 (0)'})).toBeDisabled();
  });
  it('merges only after asking, keeping what is known and dropping the rest',async()=>{
    const mergePrograms=vi.fn(),mergePolicies=vi.fn(),done=vi.fn(),dismiss=vi.fn();
    const load=()=>Promise.resolve(list([P({id:'P1',title:'정책 하나'})]));
    render(<SavedImport ids={{programs:['GOOD','GONE'],policies:['P1','P9']}} knownPrograms={new Set(['GOOD'])} onMergePrograms={mergePrograms} onMergePolicies={mergePolicies} onDone={done} onDismiss={dismiss} load={load}/>);
    expect(screen.getByRole('heading',{name:'다른 기기에서 보낸 관심 목록이 있어요'})).toBeVisible();
    expect(mergePrograms).not.toHaveBeenCalled();
    await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'이 기기에 합치기'}));});
    expect(mergePrograms).toHaveBeenCalledWith(['GOOD']);
    expect(mergePolicies.mock.calls[0][0].map((s:{id:string})=>s.id)).toEqual(['P1']);
    expect(screen.getByRole('status')).toHaveTextContent('사업 1개, 정책 1개를 이 기기의 관심 목록에 합쳤어요. 지금 목록에 없는 정책 1개는 빼었어요. 지금 목록에 없는 사업 1개도 빼었어요.');
    expect(done).toHaveBeenCalled();expect(dismiss).not.toHaveBeenCalled();
  });
  it('opens from the address on the list page and merges into this device',async()=>{
    const program=web.programs[0];
    window.location.hash='#/programs/list?saved='+encodeSaved({programs:[program.program_id],policies:[]});
    render(<RegionalPrograms browse listPage/>);
    await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'이 기기에 합치기'}));});
    expect(JSON.parse(localStorage.getItem(SUPPORT_SAVE_KEY)!).favorites).toEqual([program.program_id]);
    expect(window.location.hash).toBe('#/programs/list');
    expect(readSaved()).toEqual([]);
  });
});
