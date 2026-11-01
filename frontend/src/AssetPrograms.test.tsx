vi.mock('./AssetAlerts',()=>({default:()=>null}));
import {act,fireEvent,render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {describe,it,expect,vi} from 'vitest';
import AssetPrograms from './AssetPrograms';
import App from './App';
import rawFixture from './testing/asset-programs-fixture.json';
import comparisonFixture from './testing/comparison-fixture.json';
import type {AssetResponse} from './asset-programs-api';
import {getAssetPrograms} from './asset-programs-api';
import type {SimulationResult} from './api';
const baseline=comparisonFixture.before as SimulationResult;
const after=comparisonFixture.after as SimulationResult;
const facts={province:null,birth_date:null,owns_home:null};
const fixture=(name:'public'|'personal'|'after'|'seoul'='public')=>structuredClone(rawFixture[name]) as unknown as AssetResponse;
const reply=(data:unknown)=>({ok:true,json:async()=>data});
function publicSetup(){const fetcher=vi.fn().mockResolvedValue(reply(fixture()));vi.stubGlobal('fetch',fetcher);return {fetcher,view:render(<AssetPrograms goalMonths={null}/>)};}

describe('official government asset-building discovery',()=>{
  it('loads public information without transmitting a profile',async()=>{
    const {fetcher}=publicSetup();const result=await screen.findByTestId('asset-programs-result');
    expect(within(result).getByText('등록 사업')).toBeInTheDocument();
    const [url,options]=fetcher.mock.calls[0];expect(url).toBe('/api/asset-programs');expect(options.method).toBe('GET');expect(options.body).toBeUndefined();expect(options.cache).toBe('no-store');
    expect(screen.getAllByRole('link',{name:/공식 공고 보기/})).toHaveLength(3);
  });
  it('shows all ten distinct programs on demand',async()=>{
    publicSetup();await screen.findByTestId('asset-programs-result');
    await userEvent.click(screen.getByRole('button',{name:'나머지 7개 사업 더 보기'}));
    expect(screen.getAllByRole('link',{name:/공식 공고 보기/})).toHaveLength(10);
    expect(screen.getByRole('heading',{name:'경기도 청년 노동자 통장'})).toBeInTheDocument();
    expect(screen.getByText('올해 신규모집 없음',{exact:true})).toBeInTheDocument();
  });
  it('separates current recruitment from eight closed rounds',async()=>{
    publicSetup();await screen.findByTestId('asset-programs-result');await userEvent.click(screen.getByRole('button',{name:'모집 중'}));
    expect(screen.getAllByRole('link',{name:/공식 공고 보기/})).toHaveLength(1);
    expect(screen.getByRole('heading',{name:'청년 주택드림 청약통장'})).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button',{name:'마감'}));expect(screen.getByText('8개 사업 표시 · 먼저 3개를 보여드려요.')).toBeInTheDocument();
  });
  it('does not label screened applicants as new applications',async()=>{
    publicSetup();await screen.findByTestId('asset-programs-result');await userEvent.type(screen.getByRole('searchbox',{name:'지원사업 검색'}),'청년미래');
    expect(screen.getByText(/현재 단계: 기신청자 심사/)).toBeInTheDocument();expect(within(screen.getByRole('heading',{name:'청년미래적금'}).closest('article')!).getByText('신청 마감',{exact:true})).toBeInTheDocument();
    await userEvent.click(screen.getByText('조건·추천 근거·추가 확인사항',{exact:true}));
    expect(screen.getByText(/11월 16~27일은 기존 신청자/)).toBeInTheDocument();
  });
  it('searches official titles and regions and offers an empty state',async()=>{
    publicSetup();await screen.findByTestId('asset-programs-result');const search=screen.getByRole('searchbox',{name:'지원사업 검색'});
    await userEvent.type(search,'전북');expect(screen.getByRole('heading',{name:'전북청년 함께 두배적금'})).toBeInTheDocument();
    await userEvent.clear(search);await userEvent.type(search,'등록되지않은사업');expect(screen.getByText('이 조건에서 표시할 사업이 없어요.')).toBeInTheDocument();
  });
  it('personalizes automatically with Python-derived capacity and no client amount override',async()=>{
    const fetcher=vi.fn().mockResolvedValue(reply(fixture('personal')));vi.stubGlobal('fetch',fetcher);
    render(<AssetPrograms baseline={baseline} goalMonths={12}/>);await screen.findByTestId('asset-programs-result');
    expect(screen.getByText(/경기 · 월 저축 여력 300,000원/)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'내 조건으로 보기'})).toHaveAttribute('aria-pressed','true');
    const [url,options]=fetcher.mock.calls[0];expect(url).toBe('/api/asset-programs/recommendations');
    expect(JSON.parse(options.body)).toEqual({profile:baseline.input_summary,supplement:facts,goal_months:12});
    expect(JSON.parse(options.body)).not.toHaveProperty('capacity');
    expect(screen.queryByRole('heading',{name:'드림For 청년통장'})).not.toBeInTheDocument();
  });
  it('keeps income, home ownership, and remaining criteria visibly unconfirmed',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(reply(fixture('personal'))));render(<AssetPrograms baseline={baseline} goalMonths={12}/>);
    await screen.findByTestId('asset-programs-result');
    const card=screen.getByRole('heading',{name:'청년 주택드림 청약통장'});
    expect(card).toBeInTheDocument();
    await userEvent.click(screen.getAllByText('조건·추천 근거·추가 확인사항',{exact:true})[0]);
    expect(screen.getByText('본인 무주택 · 확인 필요')).toBeInTheDocument();
    expect(screen.getByText(/시행 완료·유형별 적용을 확인하기 전/)).toBeInTheDocument();
    expect(screen.getAllByText('추가 확인 필요',{exact:true}).length).toBeGreaterThan(0);
  });
  it('applies optional facts only after explicit submit and does not save them',async()=>{
    const fetcher=vi.fn().mockResolvedValueOnce(reply(fixture('personal'))).mockResolvedValueOnce(reply(fixture('seoul')));vi.stubGlobal('fetch',fetcher);
    render(<AssetPrograms baseline={baseline} goalMonths={12}/>);await screen.findByTestId('asset-programs-result');
    await userEvent.click(screen.getByText('추천 정확도를 높일 추가 정보 · 선택'));
    await userEvent.selectOptions(screen.getByLabelText('추천용 거주 광역지역'),'서울');
    fireEvent.change(screen.getByLabelText('생년월일'),{target:{value:'2002-01-01'}});
    await userEvent.selectOptions(screen.getByLabelText('본인 명의 주택 소유'),'false');expect(fetcher).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByRole('button',{name:'추가 정보로 추천 갱신'}));
    await screen.findByText(/서울 · 월 저축 여력/);
    expect(JSON.parse(fetcher.mock.calls[1][1].body).supplement).toEqual({province:'서울',birth_date:'2002-01-01',owns_home:false});
    expect(localStorage.length).toBe(0);
  });
  it('switches to after capacity without inventing policy support money',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(reply(fixture('after'))));render(<AssetPrograms baseline={baseline} after={after} goalMonths={12}/>);
    await screen.findByTestId('asset-programs-result');await userEvent.click(screen.getByRole('button',{name:'지원사업 변경 후 기준'}));
    expect(screen.getByText(/월 저축 여력 0원/)).toBeInTheDocument();
    expect(screen.getByText('이 조건에서 표시할 사업이 없어요.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button',{name:'전체'}));
    expect(screen.getAllByText(/현재 저축 여력으로 최소 납입액/).length).toBeGreaterThan(0);
  });
  it('links the implemented alert channels and explicitly excludes email',async()=>{
    publicSetup();await screen.findByTestId('asset-programs-result');await userEvent.click(screen.getByText('자료 갱신과 모집 알림 안내'));
    expect(screen.getByText(/현재 공개 서비스에서는 자동 갱신·브라우저 알림·이메일 구독을 제공하지 않습니다/)).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/알림 구독/})).not.toBeInTheDocument();
  });
  it('offers retry on service failure without removing other features',async()=>{
    const fetcher=vi.fn().mockResolvedValueOnce({ok:false,status:503}).mockResolvedValueOnce(reply(fixture()));vi.stubGlobal('fetch',fetcher);
    render(<AssetPrograms goalMonths={null}/>);expect(await screen.findByRole('alert')).toHaveTextContent('불러오지 못했습니다');
    await userEvent.click(screen.getByRole('button',{name:'지원사업 다시 조회'}));expect(await screen.findByTestId('asset-programs-result')).toBeInTheDocument();
  });
  it.each([null,{}, {...rawFixture.public,policy_benefit_applied_krw:100000}])('rejects malformed or monetary-tampered output',async(value)=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(reply(value)));
    await expect(getAssetPrograms(null,null,facts,null,new AbortController().signal)).rejects.toThrow('응답 형식');
  });
  it('ignores an older public response after personalization begins',async()=>{
    let resolve!:(value:unknown)=>void;
    vi.stubGlobal('fetch',vi.fn().mockReturnValueOnce(new Promise(r=>{resolve=r;})).mockResolvedValueOnce(reply(fixture('personal'))));
    const view=render(<AssetPrograms goalMonths={null}/>);view.rerender(<AssetPrograms baseline={baseline} goalMonths={null}/>);
    await screen.findByText(/경기 · 월 저축 여력/);await act(async()=>resolve(reply(fixture())));
    expect(screen.getByText(/경기 · 월 저축 여력/)).toBeInTheDocument();
  });
  it('aborts a ten-second catalog request without automatic retry',async()=>{
    vi.useFakeTimers();
    try{
      const fetcher=vi.fn().mockImplementation((_url,options)=>new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError')))));
      vi.stubGlobal('fetch',fetcher);render(<AssetPrograms goalMonths={null}/>);
      await act(async()=>{await vi.advanceTimersByTimeAsync(10001);});
      expect(screen.getByRole('alert')).toHaveTextContent('조회 시간이 초과');expect(fetcher).toHaveBeenCalledTimes(1);
    }finally{vi.useRealTimers();}
  });
  it('integrates public discovery and actual personal recommendation in App',async()=>{
    const fetcher=vi.fn().mockImplementation((url)=>{
      const path=String(url);
      return Promise.resolve(reply(path==='/api/asset-programs'?fixture():path.endsWith('/recommendations')?fixture('personal'):baseline));
    });vi.stubGlobal('fetch',fetcher);window.history.replaceState(null,'','/#/programs');render(<App/>);
    await screen.findByTestId('asset-programs-result');
    expect(fetcher.mock.calls[0][0]).toBe('/api/asset-programs');
    await go('budget');await userEvent.click(screen.getByRole('button',{name:'내 상황으로 계산하기'}));await screen.findByTestId('disposable');await go('programs');
    await screen.findByText(/경기 · 월 저축 여력/);
    expect(screen.getByTestId('disposable')).toHaveTextContent('500,000원');
    expect(fetcher.mock.calls.some(([url])=>url==='/api/asset-programs/recommendations')).toBe(true);
    expect(screen.getByText(/합성 정책 결과를 실제 수입으로 더하지 않습니다/)).toBeInTheDocument();
  });
});


async function go(page:string){await userEvent.click(screen.getByRole('navigation',{name:'주요 메뉴'}).querySelector(`a[href="#/${page}"]`)!);}
