import directory from './public-data/nationwide-districts.json';

/**
 * Reads a sentence like "안산 사는 24살 대학생이고 월세 살아요" into the finder's conditions.
 * Plain rules over words and the official district list; it runs in the browser and the text
 * is never sent or stored. Anything it is unsure about is reported instead of guessed.
 */
export type ParsedConditions={
  province?:string; city?:string; age?:string; employment?:string; rent?:string; school?:string; marriage?:string;
  notes:string[];
};

const cities=directory.cities as Record<string,string[]>;
const PROVINCE_WORDS:[string,string[]][]=[
  ['서울',['서울특별시','서울시','서울']],['부산',['부산광역시','부산시','부산']],['대구',['대구광역시','대구시','대구']],
  ['인천',['인천광역시','인천시','인천']],['광주',['광주광역시','광주시','광주']],['대전',['대전광역시','대전시','대전']],
  ['울산',['울산광역시','울산시','울산']],['세종',['세종특별자치시','세종시','세종']],['경기',['경기도','경기']],
  ['강원',['강원특별자치도','강원도','강원']],['충북',['충청북도','충북']],['충남',['충청남도','충남']],
  ['전북',['전북특별자치도','전라북도','전북']],['전남',['전라남도','전남']],['경북',['경상북도','경북']],
  ['경남',['경상남도','경남']],['제주',['제주특별자치도','제주도','제주']],
];
const stem=(name:string)=>name.replace(/(시|군|구)$/,'');
const esc=(s:string)=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
// A place name must stand as its own word: start, space or punctuation before it, and a
// particle, a living verb or a break after it. This keeps "남동생" from meaning 남동구.
const BEFORE='(?:^|[\\s,./·()~])';
const AFTER='(?=에서|에|사는|살고|살아|살며|거주|쪽|이고|이며|이에요|예요|입니다|이랑|[\\s,./·()~]|$)';
// Stems that are also everyday words need 시·군·구 or a living verb right after them.
const COMMON=new Set(['예산','인제','장수','진도','남해','동해','고성','영광','화성','부안','완도','증평','보은','영동','청송','하동','고령','성주','의성','함안']);
const STRONG='(?=에서|에|사는|살고|살아|살며|거주)';

function wordAt(text:string,form:string,strong=false){
  const m=new RegExp(BEFORE+esc(form)+(strong?STRONG:AFTER)).exec(text);
  return m?m.index:-1;
}

/** Every way a district can be written: "안산시", "안산", and for wards "안산시 단원구", "단원구". */
function cityForms(option:string):{form:string;strong:boolean}[]{
  const parts=option.split(' ');
  const last=parts[parts.length-1];
  const forms=[{form:option,strong:false},{form:last,strong:false}];
  if(parts.length===2)forms.push({form:parts[0]+' '+last,strong:false},{form:stem(parts[0])+' '+last,strong:false});
  const s=stem(last);
  // "제주"·"광주" alone name the province; the district needs its 시 (or 경기 in front, handled below).
  const provinceWord=PROVINCE_WORDS.some(([,words])=>words.includes(s));
  if(s.length>=2&&(!provinceWord||s==='광주'))forms.push({form:s,strong:COMMON.has(s)});
  return forms;
}
type CityHit={province:string;city:string;length:number};

function findCities(text:string):CityHit[]{
  const hits:CityHit[]=[];
  for(const [province,options] of Object.entries(cities))for(const option of options){
    let best:CityHit|null=null;
    for(const {form,strong} of cityForms(option)){
      if(wordAt(text,form,strong)<0)continue;
      if(!best||form.length>best.length)best={province,city:option,length:form.length};
    }
    if(best)hits.push(best);
  }
  return hits;
}

const NATIVE_TENS:Record<string,number>={스물:20,서른:30,마흔:40};
const NATIVE_ONES:Record<string,number>={'':0,한:1,하나:1,두:2,둘:2,세:3,셋:3,네:4,넷:4,다섯:5,여섯:6,일곱:7,여덟:8,아홉:9};

function findAge(text:string,year:number):{age?:string;note?:string}{
  const n=text.match(/만\s*(\d{1,3})\s*(?:세|살)?|(\d{1,3})\s*(?:세|살)/);
  if(n)return {age:n[1]??n[2]};
  const native=text.match(/(스물|서른|마흔)\s*(하나|한|둘|두|셋|세|넷|네|다섯|여섯|일곱|여덟|아홉)?\s*살/);
  if(native)return {age:String(NATIVE_TENS[native[1]]+NATIVE_ONES[native[2]??''])};
  const born=text.match(/(19\d{2}|20\d{2}|\d{2})\s*년생/);
  if(born){
    const y=born[1].length===2?(Number(born[1])>30?1900:2000)+Number(born[1]):Number(born[1]);
    const age=year-y;
    if(age>=0&&age<=120)return {age:String(age),note:`출생연도로 계산한 나이예요. 올해 생일이 아직 안 지났다면 만 ${age-1}세예요.`};
  }
  return {};
}

function findRegion(text:string,out:ParsedConditions){
  const named=PROVINCE_WORDS.filter(([,words])=>words.some(w=>wordAt(text,w)>=0)).map(([p])=>p);
  // "경기 광주" is 경기도 광주시, not 광주광역시.
  const provinces=named.includes('경기')&&named.includes('광주')?named.filter(p=>p!=='광주'):named;
  const province=provinces.length===1?provinces[0]:undefined;
  if(provinces.length>1)out.notes.push(`광역지역이 여러 개(${provinces.join('·')}) 보여서 지역은 비워 뒀어요. 하나만 적어 주세요.`);
  let hits=findCities(text);
  if(province)hits=hits.filter(h=>h.province===province);
  const longest=Math.max(0,...hits.map(h=>h.length));
  const best=hits.filter(h=>h.length===longest);
  // A ward and its city both match "안산시 단원구"; keep the ward.
  const wards=best.filter(h=>h.city.includes(' '));
  const pick=wards.length?wards:best;
  if(pick.length===1){out.province=pick[0].province;out.city=pick[0].city;return;}
  if(pick.length>1){
    const ps=[...new Set(pick.map(h=>h.province))];
    if(ps.length===1)out.province=ps[0];
    else out.notes.push(`‘${pick[0].city}’은(는) 여러 지역에 있어요. 광역지역(예: ${ps.slice(0,2).join('·')})도 함께 적어 주세요.`);
  }
  if(province&&!out.province)out.province=province;
}

const has=(text:string,re:RegExp)=>re.test(text);

export function parseConditions(input:string,year=new Date().getFullYear()):ParsedConditions{
  const text=input.replace(/\s+/g,' ').trim().slice(0,300);
  const flat=text.replace(/\s+/g,'');
  const out:ParsedConditions={notes:[]};
  if(!text)return out;

  findRegion(text,out);

  const age=findAge(text,year);
  if(age.age&&Number(age.age)<=120){out.age=age.age;if(age.note)out.notes.push(age.note);}

  // Schooling: the most specific phrase wins.
  if(has(flat,/대학원|석사|박사/))out.school='grad_school';
  else if(has(flat,/졸업예정|졸업반|졸업유예|4학년/))out.school='univ_expected';
  else if(has(flat,/대졸|대학(교)?(을|를)?졸업|학사/))out.school='univ_grad';
  else if(has(flat,/대학생|대학(교)?(에|을|를)?다니|대학재학|대학교재학|휴학|복학|신입생|새내기|[123]학년/))out.school='univ_student';
  else if(has(flat,/고등학생|고3|고2|고1|고딩|고등학교(에|를)?다니/))out.school='hs_student';
  else if(has(flat,/고졸|고등학교(를|을)?졸업/))out.school='hs_grad';

  // Work: part-time work counts as working, as the finder explains.
  // Read with spaces kept, so "마포구 직장인" is not taken as "구직".
  if(has(text,/자영업|프리랜서|개인\s?사업|사업(을|를)?\s?하고|창업(했|하고|\s?중)|가게(를)?\s?운영/))out.employment='self_employed';
  else if(has(text,/취준|취업\s?준비|(?:^|[\s,])구직|백수|무직|실업|퇴사했|일(을|를)?\s?안\s?(해|하)|쉬고\s?있|일자리(를)?\s?찾/))out.employment='unemployed';
  else if(has(text,/직장인|회사원|회사(에|를)?\s?다니|재직|근무|정규직|계약직|인턴|알바|아르바이트|일하고|일해요|출근|공무원/))out.employment='employed';

  // Housing: "월세 아니에요" is a no.
  if(has(flat,/월세(가|는|에)?(아니|아님|안살|안삶)/))out.rent='no';
  else if(has(flat,/월세/))out.rent='yes';
  else if(has(flat,/전세|자가|내집|본가|부모님(이랑|과|집)|기숙사/))out.rent='no';

  // Marriage.
  if(has(flat,/결혼예정|예비신혼|예비부부/)){out.marriage='single';out.notes.push('결혼 예정이면 지금은 미혼으로 넣었어요. 신혼부부 정책은 혼인신고 기준을 확인하세요.');}
  else if(has(flat,/미혼|싱글|결혼(을|은)?안|비혼/))out.marriage='single';
  else if(has(flat,/기혼|결혼했|신혼|남편|아내|배우자|와이프/))out.marriage='married';

  if(!describeParsed(out).length)out.notes.push('알아들은 조건이 없어요. 예: “경기 안산 사는 24살 대학생, 월세 살아요”');
  return out;
}

const SCHOOL:Record<string,string>={below_hs:'고등학교 졸업 전',hs_student:'고등학생·졸업 예정',hs_grad:'고등학교 졸업',univ_student:'대학 재학',univ_expected:'대학 졸업 예정',univ_grad:'대학 졸업',grad_school:'대학원'};
const WORK:Record<string,string>={employed:'근로 중',unemployed:'현재 일하지 않음',self_employed:'자영업·프리랜서'};
/** The understood conditions as short labels, in the order of the form. */
export function describeParsed(p:ParsedConditions):{label:string;value:string}[]{
  const rows:{label:string;value:string}[]=[];
  if(p.province)rows.push({label:'지역',value:[p.province,p.city].filter(Boolean).join(' ')});
  if(p.age)rows.push({label:'나이',value:'만 '+p.age+'세'});
  if(p.employment)rows.push({label:'취업 상태',value:WORK[p.employment]});
  if(p.rent)rows.push({label:'월세',value:p.rent==='yes'?'월세 거주':'월세 아님'});
  if(p.school)rows.push({label:'학력',value:SCHOOL[p.school]});
  if(p.marriage)rows.push({label:'혼인',value:p.marriage==='married'?'기혼':'미혼'});
  return rows;
}
