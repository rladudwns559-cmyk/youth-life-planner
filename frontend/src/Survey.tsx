import {useState} from 'react';
import {SURVEY_QUESTIONS,SURVEY_FORM,SURVEY_FORM_ONLY_QUESTION,missingAnswers,prefilledFormUrl,type SurveyAnswers} from './survey-config';
import {routeLinks} from './portal-routing';
import './survey.css';

export default function Survey({form=SURVEY_FORM}:{form?:typeof SURVEY_FORM}){
  const [answers,setAnswers]=useState<SurveyAnswers>({});
  const [tried,setTried]=useState(false);
  const missing=missingAnswers(answers);
  const url=missing.length?null:prefilledFormUrl(answers,form);
  const connected=prefilledFormUrl(Object.fromEntries(SURVEY_QUESTIONS.map(q=>[q.id,q.type==='scale'?'3':q.options[0]])),form)!==null;
  const set=(id:string,value:string)=>setAnswers(old=>({...old,[id]:value}));
  return <section className="survey" aria-label="사용자 평가 설문">
    <div className="survey-intro">
      <p>서비스를 써 본 뒤 2분 정도 답해 주세요. 팀 프로젝트의 사용자 평가에 쓰입니다.</p>
      <ul>
        <li>이름·연락처·이메일은 묻지 않아요.</li>
        <li>이 앱은 답을 저장하거나 보내지 않아요. 마지막에 구글 폼이 답이 채워진 채로 열리고, 거기서 <b>제출</b>을 눌러야 전송돼요.</li>
        <li>아직 써 보지 않았다면 <a href={routeLinks.programs}>지원사업 찾기</a>부터 써 보세요.</li>
      </ul>
    </div>
    {!connected&&<p className="survey-pending" role="status">설문 제출용 구글 폼을 연결하는 중이에요. 문항은 미리 볼 수 있지만 아직 제출할 수 없습니다.</p>}
    <ol className="survey-questions">
      {SURVEY_QUESTIONS.map((q,n)=>{
        const invalid=tried&&missing.includes(q.id);
        return <li key={q.id} className={invalid?'survey-invalid':undefined}>
          <fieldset aria-describedby={invalid?q.id+'-error':undefined}>
            <legend><span>{n+1}</span>{q.text}</legend>
            {q.type==='scale'
              ?<div className="survey-scale"><small aria-hidden="true">{q.low}</small><div role="presentation">{['1','2','3','4','5'].map(v=><label key={v}><input type="radio" name={q.id} value={v} checked={answers[q.id]===v} onChange={()=>set(q.id,v)}/><span>{v}<span className="sr-only">점{v==='1'?' ('+q.low+')':v==='5'?' ('+q.high+')':''}</span></span></label>)}</div><small aria-hidden="true">{q.high}</small></div>
              :<div className="survey-options">{q.options.map(o=><label key={o}><input type="radio" name={q.id} value={o} checked={answers[q.id]===o} onChange={()=>set(q.id,o)}/><span>{o}</span></label>)}</div>}
            {invalid&&<p className="survey-error" id={q.id+'-error'}>이 문항에 답해 주세요.</p>}
          </fieldset>
        </li>;
      })}
    </ol>
    <div className="survey-submit">
      <p>마지막 문항 “{SURVEY_FORM_ONLY_QUESTION.split(' (')[0]}”은 구글 폼에서 직접 적어 주세요.</p>
      {url
        ?<a className="survey-go" href={url} target="_blank" rel="noopener noreferrer">구글 폼에서 확인하고 제출하기 ↗</a>
        :<button type="button" className="survey-go" onClick={()=>setTried(true)} aria-disabled={!connected||undefined}>{connected?'구글 폼에서 확인하고 제출하기':'구글 폼 연결 전 · 제출 불가'}</button>}
      <p role="status" className="survey-status">{tried&&missing.length>0?`답하지 않은 문항이 ${missing.length}개 있어요.`:url?'새 창의 구글 폼에서 답을 확인한 뒤 제출을 눌러 주세요.':''}</p>
    </div>
  </section>;
}
