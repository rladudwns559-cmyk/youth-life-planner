import {render,screen,fireEvent,within,cleanup} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi,describe} from 'vitest';
import RegionalPrograms from './RegionalPrograms';
import {readProfile,PROFILE_KEY} from './support-profile';
import {ConsultMemoSheet,type MemoItem} from './ConsultMemo';

const change=(name:string,value:string)=>fireEvent.change(screen.getByLabelText(name),{target:{value}});
beforeEach(()=>{localStorage.clear();vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-11-13T03:00:00Z'));vi.stubGlobal('fetch',vi.fn(()=>{throw Error('Unexpected network');}));});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});

describe('remember my conditions',()=>{
  it('is off by default and stores nothing',()=>{
    render(<RegionalPrograms browse={false}/>);
    expect(screen.getByLabelText('이 기기에 내 조건 기억하기')).not.toBeChecked();
    change('현재 만 나이','25');
    expect(localStorage.getItem(PROFILE_KEY)).toBeNull();
    expect(screen.getByText(/외부 전송·영구 저장하지 않습니다/)).toBeVisible();
  });

  it('keeps only region, age and two choices, restores them, and forgets on switch-off',()=>{
    render(<RegionalPrograms browse={false}/>);
    fireEvent.click(screen.getByLabelText('이 기기에 내 조건 기억하기'));
    change('관심·거주 광역지역','경기');change('시·군·구','안산시 단원구');change('현재 만 나이','25');
    change('현재 취업 상태','unemployed');change('현재 월세 거주 여부','yes');
    change('사업·지원내용 검색','월세');
    expect(JSON.parse(localStorage.getItem(PROFILE_KEY)!)).toEqual({province:'경기',city:'안산시 단원구',age:'25',employment:'unemployed',rent:'yes'});
    cleanup();
    render(<RegionalPrograms browse={false}/>);
    expect(screen.getByLabelText('이 기기에 내 조건 기억하기')).toBeChecked();
    expect(screen.getByLabelText('관심·거주 광역지역')).toHaveValue('경기');
    expect(screen.getByLabelText('시·군·구')).toHaveValue('안산시 단원구');
    expect(screen.getByLabelText('현재 만 나이')).toHaveValue(25);
    expect(screen.getByLabelText('사업·지원내용 검색')).toHaveValue('');  // search words are not remembered
    fireEvent.click(screen.getByLabelText('이 기기에 내 조건 기억하기'));
    expect(localStorage.getItem(PROFILE_KEY)).toBeNull();
  });

  it('ignores tampered or invalid stored values',()=>{
    localStorage.setItem(PROFILE_KEY,JSON.stringify({province:'없는도',city:'x',age:'999',employment:'ceo',rent:'maybe',income:5000000}));
    expect(readProfile()).toEqual({province:'',city:'',age:'',employment:'unknown',rent:'unknown'});
    localStorage.setItem(PROFILE_KEY,'not json');
    expect(readProfile()).toBeNull();
  });

  it('keeps working on screen when the browser refuses storage',()=>{
    vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('blocked');});
    render(<RegionalPrograms browse={false}/>);
    fireEvent.click(screen.getByLabelText('이 기기에 내 조건 기억하기'));
    expect(screen.getByText('이 브라우저에서는 저장할 수 없어 현재 화면에서만 유지합니다.')).toBeVisible();
    change('현재 만 나이','30');
    expect(screen.getByLabelText('현재 만 나이')).toHaveValue(30);
  });
});

const item:MemoItem={id:'P1',title:'시험 사업',place:'경기 안산시',status:'공고상 신청기간 · 잔여 확인',deadline:'신청 마감 11월 30일 · D-17',
  matches:[{label:'나이',word:'입력 조건 일치'}],gaps:[{label:'취업 상태',text:"입력한 '근로 중' 상태는 대상이 아니에요."}],
  checks:[{text:'소득 기준 확인',done:true},{text:'거주기간 확인',done:false}],url:'https://example.go.kr/p1'};

describe('consult memo',()=>{
  it('puts my conditions, the programs with open questions and where to ask on one sheet',()=>{
    render(<ConsultMemoSheet items={[item]} asOf="2026-11-13" province="경기" city="안산시" profile={{region:'경기 안산시',age:'만 25세',employment:'근로 중',rent:'월세 거주'}}/>);
    const sheet=screen.getByRole('article',{name:'상담 준비 메모'});
    expect(within(sheet).getByText('작성 2026-11-13 · 청년 경제생활 시뮬레이터')).toBeVisible();
    expect(within(sheet).getByText('만 25세')).toBeVisible();
    expect(within(sheet).getByText('시험 사업')).toBeVisible();
    expect(within(sheet).getByText(/신청 마감 11월 30일 · D-17/)).toBeVisible();
    expect(within(sheet).getByText(/근로 중' 상태는 대상이 아니에요/)).toBeVisible();
    expect(within(sheet).getByText('(확인함)',{exact:false})).toBeInTheDocument();
    expect(within(sheet).getByText('공식 안내 https://example.go.kr/p1')).toBeVisible();
    expect(within(sheet).getByText(/안산시 청년센터 상상대로/)).toBeVisible();
    expect(within(sheet).getByText(/1670-1839/)).toBeVisible();
    expect(within(sheet).getByText(/신청 자격을 확정하지 않습니다/)).toBeVisible();
  });

  it('is built from saved programs and printed only from the preview',()=>{
    const print=vi.fn();vi.stubGlobal('print',print);
    render(<RegionalPrograms/>);
    expect(screen.getByRole('button',{name:'상담 준비 메모 만들기 (0)'})).toBeDisabled();
    const card=screen.getAllByRole('article')[0];
    const title=within(card).getByRole('heading',{level:3}).textContent!;
    fireEvent.click(within(card).getByRole('button',{name:/관심사업$/}));
    fireEvent.click(screen.getByRole('button',{name:'상담 준비 메모 만들기 (1)'}));
    const preview=screen.getByRole('dialog',{name:'상담 준비 메모 미리보기'});
    expect(within(preview).getByRole('heading',{name:title,level:4})).toBeVisible();
    expect(print).not.toHaveBeenCalled();
    fireEvent.click(within(preview).getByRole('button',{name:'인쇄 · PDF로 저장'}));
    expect(print).toHaveBeenCalledTimes(1);
    expect(document.body).toHaveClass('printing-memo');
    fireEvent.click(within(preview).getByRole('button',{name:'닫기'}));
    expect(document.body).not.toHaveClass('printing-memo');
    expect(screen.queryByRole('dialog',{name:'상담 준비 메모 미리보기'})).toBeNull();
  });
});
