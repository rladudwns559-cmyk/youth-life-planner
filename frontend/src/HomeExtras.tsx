import prepared from './public-data/current-support-web.json';
import {readRegionalDecision,intakeLabels,locationText} from './support-status';
import './regional-programs.css';
import {deadlineOf,daysLeft,DeadlineAction,useKoreaDay} from './SupportPlanner';
import {routeLinks} from './portal-routing';
import './home-extras.css';

type Program=typeof prepared.programs[number];
export type SoonItem={program:Program;end:string;days:number;status:string};

/** Programs whose published application deadline falls within `within` days, closest first. Closed rounds are left out. */
export function closingSoon(asOf:string,within=7):SoonItem[]{
  const rows:SoonItem[]=[];
  for(const program of prepared.programs){
    const end=deadlineOf(program,asOf);if(!end)continue;
    const days=daysLeft(end,asOf);if(days>within)continue;
    const intake=readRegionalDecision(program.program_id,'*',asOf).intake;
    if(intake==='CLOSED'||intake==='NO_INTAKE')continue;
    rows.push({program,end,days,status:intakeLabels[intake]});
  }
  return rows.sort((a,b)=>a.days-b.days||a.program.title.localeCompare(b.program.title,'ko'));
}

export function HomeSteps(){
  const steps=[
    {n:'1',title:'내 조건 넣기',text:'지역·나이·취업·월세 여부만 고르면 돼요. 모르는 항목은 비워 둬도 괜찮아요.',href:routeLinks.programs,link:'조건 넣으러 가기'},
    {n:'2',title:'맞는 사업 확인',text:'조건이 맞는 사업과, 맞지 않으면 무엇이 다른지 함께 보여 드려요.',href:routeLinks.catalog,link:'지원사업 둘러보기'},
    {n:'3',title:'마감일 저장 · 센터에 문의',text:'마감일을 캘린더에 저장하고, 헷갈리는 조건은 청년센터에 물어보세요.',href:routeLinks.programs,link:'결과에서 저장하기'},
  ];
  return <section className="home-steps" aria-labelledby="home-steps-title">
    <h2 id="home-steps-title">이렇게 써 보세요</h2>
    <ol>{steps.map(s=><li key={s.n}><span className="home-step-n" aria-hidden="true">{s.n}</span><div><h3>{s.title}</h3><p>{s.text}</p><a href={s.href}>{s.link} →</a></div></li>)}</ol>
  </section>;
}

export function HomeDeadlines({limit=4}:{limit?:number}){
  const asOf=useKoreaDay();
  const week=closingSoon(asOf,7);
  const items=week.length?week:closingSoon(asOf,14);
  const span=week.length?7:14;
  return <section className="home-deadlines" aria-labelledby="home-deadlines-title">
    <div className="home-deadlines-head">
      <h2 id="home-deadlines-title">{span}일 안에 신청이 마감되는 지원사업 <b>{items.length}개</b></h2>
      <a href={routeLinks.catalog}>전체 지원사업 보기 →</a>
    </div>
    <p className="home-deadlines-note">공고에 적힌 마감일 기준이에요({asOf} 기준). 접수 중인지, 예산이 남았는지는 공식 안내에서 확인하세요. 내 조건과 맞는지는 <a href={routeLinks.programs}>조건 넣기</a>에서 볼 수 있어요.</p>
    {items.length===0
      ?<p className="home-deadlines-empty">2주 안에 마감되는 등록 공고가 없어요.</p>
      :<ul>{items.slice(0,limit).map(({program:p,status})=><li key={p.program_id}>
        <div className="home-deadline-meta"><span>{locationText(p)}</span><span>{status}</span></div>
        <h3>{p.title}</h3>
        <DeadlineAction program={p} asOf={asOf}/>
        <a href={p.sources[0].url} target="_blank" rel="noopener noreferrer" aria-label={p.title+' 공식 안내'}>공식 안내 ↗</a>
      </li>)}</ul>}
    {items.length>limit&&<p className="home-deadlines-more">외 {items.length-limit}개는 지원사업 목록에서 정렬을 “공고 마감일 가까운 순”으로 바꾸면 볼 수 있어요.</p>}
  </section>;
}
