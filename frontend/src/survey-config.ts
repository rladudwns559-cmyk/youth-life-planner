// User-evaluation survey. Answers are never stored or sent by this app:
// the respondent is handed a Google Form link with the answers pre-filled and submits it there.
// To connect a form: create it from docs/USER_SURVEY.md, then put its prefill IDs in SURVEY_FORM.

export type SurveyQuestion =
  | {id:string; type:'scale'; text:string; low:string; high:string; required:true}
  | {id:string; type:'choice'; text:string; options:string[]; required:true};

const agreeLow='전혀 아니다', agreeHigh='매우 그렇다';

export const SURVEY_QUESTIONS:SurveyQuestion[] = [
  {id:'age', type:'choice', text:'연령대', options:['19세 이하','20~24세','25~29세','30~34세','35세 이상'], required:true},
  {id:'status', type:'choice', text:'현재 상태', options:['학생','근로 중','구직 중','기타'], required:true},
  {id:'before', type:'scale', text:'이 서비스를 쓰기 전, 나에게 맞는 청년 지원사업을 스스로 찾을 수 있다고 느꼈다.', low:agreeLow, high:agreeHigh, required:true},
  {id:'after', type:'scale', text:'이 서비스를 쓴 뒤, 나에게 맞는 청년 지원사업을 스스로 찾을 수 있다고 느낀다.', low:agreeLow, high:agreeHigh, required:true},
  {id:'understand', type:'scale', text:'지원사업 조건이 나와 맞는지, 맞지 않으면 무엇이 다른지 이해하기 쉬웠다.', low:agreeLow, high:agreeHigh, required:true},
  {id:'intent', type:'scale', text:'결과를 보고 실제로 신청하거나 더 알아볼 생각이 생겼다.', low:agreeLow, high:agreeHigh, required:true},
  {id:'learned', type:'choice', text:'이번에 처음 알게 된 지원사업이나 금융상품이 있었다.', options:['있었다','없었다'], required:true},
  {id:'deadline', type:'choice', text:'신청 마감일 캘린더 저장 기능은 어땠나요?', options:['유용했다','보통이다','별로였다','사용하지 않았다'], required:true},
  {id:'best', type:'choice', text:'가장 도움이 된 기능', options:['지원사업 찾기','조건 차이 안내','마감일 캘린더','생활비 계산','적금·예금 찾기'], required:true},
];
/** Free text is typed on the Google Form itself so it never travels in a URL. */
export const SURVEY_FORM_ONLY_QUESTION='불편했던 점이나 바라는 점 (선택, 이름·연락처 등 개인정보는 적지 마세요)';

/** Google Form prefill target (the team's published form). An empty formUrl closes submission. */
export const SURVEY_FORM:{formUrl:string; entries:Record<string,string>} = {
  formUrl:'https://docs.google.com/forms/d/e/1FAIpQLSdd6Biq-YWCvj-TKbMASDZjs_XEGVJ8B8hH5jRYD3EzvmWuJQ/viewform',
  entries:{
    age:'entry.1384659077', status:'entry.522325794',
    before:'entry.410576309', after:'entry.262259213',
    understand:'entry.2117295390', intent:'entry.1986481095',
    learned:'entry.171299156', deadline:'entry.376348182', best:'entry.222682770',
  },
};

export type SurveyAnswers = Record<string,string>;

export function missingAnswers(answers:SurveyAnswers){
  return SURVEY_QUESTIONS.filter(q=>!answers[q.id]?.trim()).map(q=>q.id);
}

/** Builds the Google Forms "viewform" URL with answers pre-filled; null when the form is not connected or a mapping is missing. */
export function prefilledFormUrl(answers:SurveyAnswers, form=SURVEY_FORM):string|null{
  if(!/^https:\/\/docs\.google\.com\/forms\/d\/e\/[\w-]+\/viewform$/.test(form.formUrl))return null;
  const params=new URLSearchParams({usp:'pp_url'});
  for(const q of SURVEY_QUESTIONS){
    const entry=form.entries[q.id];
    if(!entry||!/^entry\.\d+$/.test(entry))return null;
    const value=answers[q.id]??'';
    const allowed=q.type==='scale'?['1','2','3','4','5']:q.options;
    if(!allowed.includes(value))return null;
    params.set(entry,value);
  }
  return form.formUrl+'?'+params.toString();
}
