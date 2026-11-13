import {useRef,useState,type FormEvent} from 'react';
import GroupedInput from './GroupedInput';
import {calculateCashflow,MAX_KRW,type CashflowInput,type CashflowResult} from './cashflow';
import {routeLinks} from './portal-routing';
import SupportAssumption from './SupportAssumption';
import './public-budget.css';

/* Public (server-less) budget page: monthly room to save, then a what-if on the user's own numbers.
   All amounts come from calculateCashflow (parity-tested against Python). Nothing is stored or sent.
   Policy benefits are never added automatically. */
export interface PublicBudgetState {before:CashflowResult;after:CashflowResult|null}
type Key='monthly_income'|'monthly_rent'|'monthly_fixed_expenses'|'other_monthly_expenses'|'user_savings_capacity';
type Values=Record<Key,string>;
const labels:Record<Key,string>={monthly_income:'월 소득',monthly_rent:'월세',monthly_fixed_expenses:'월 고정지출',other_monthly_expenses:'월 기타지출',user_savings_capacity:'저축에 쓸 상한'};
const hints:Partial<Record<Key,string>>={monthly_income:'세후로 실제 받는 금액',monthly_fixed_expenses:'통신비·보험·구독·교통비 등',other_monthly_expenses:'식비·생활비 등',user_savings_capacity:'빈칸: 남는 돈 전부 · 0: 저축하지 않음'};
const required:Key[]=['monthly_income','monthly_rent','monthly_fixed_expenses','other_monthly_expenses'];
const empty:Values={monthly_income:'',monthly_rent:'',monthly_fixed_expenses:'',other_monthly_expenses:'',user_savings_capacity:''};
const won=(n:number)=>`${n.toLocaleString('ko-KR')}원`;
const signed=(n:number)=>`${n>0?'+':n<0?'−':''}${Math.abs(n).toLocaleString('ko-KR')}원`;

function parse(values:Values):{input?:CashflowInput;errors:Partial<Record<Key,string>>}{
  const errors:Partial<Record<Key,string>>={};
  const read=(key:Key,optional=false):number|null=>{
    const raw=values[key].trim();
    if(!raw&&optional)return null;
    if(!/^\d+$/.test(raw)||!Number.isSafeInteger(Number(raw))||Number(raw)>MAX_KRW){errors[key]=raw?`${labels[key]}은(는) 0 이상의 원 단위 정수로 입력해 주세요.`:`${labels[key]}을(를) 입력해 주세요. 없으면 0을 넣으세요.`;return null;}
    return Number(raw);
  };
  const [income,rent,fixed,other]=required.map(key=>read(key));
  const capacity=read('user_savings_capacity',true);
  if(Object.keys(errors).length)return {errors};
  return {errors,input:{monthly_income:income!,monthly_rent:rent!,monthly_fixed_expenses:fixed!,other_monthly_expenses:other!,user_savings_capacity:capacity}};
}

const presets:{label:string;key:Key;delta:number}[]=[
  {label:'월세 20만원 줄면',key:'monthly_rent',delta:-200000},
  {label:'월세 10만원 오르면',key:'monthly_rent',delta:100000},
  {label:'소득 30만원 늘면',key:'monthly_income',delta:300000},
  {label:'기타지출 10만원 줄이면',key:'other_monthly_expenses',delta:-100000},
];

function Fields({prefix,values,errors,keys,onChange}:{prefix:string;values:Values;errors:Partial<Record<Key,string>>;keys:Key[];onChange:(key:Key,value:string)=>void}){
  return <div className="budget-fields">{keys.map(key=>{const id=`${prefix}-${key}`;const optional=key==='user_savings_capacity';return <div className="budget-field" key={key}>
    <label htmlFor={id}>{labels[key]}{optional&&<small> 선택</small>}</label>
    <div className="discovery-unit"><GroupedInput id={id} inputMode="numeric" autoComplete="off" placeholder={optional?'비워 두면 전부':'0'} value={values[key]} onChange={e=>onChange(key,e.target.value)} aria-invalid={!!errors[key]} aria-describedby={errors[key]?`${id}-error`:hints[key]?`${id}-hint`:undefined}/><span>원</span></div>
    {errors[key]?<p className="budget-error" id={`${id}-error`}>{errors[key]}</p>:hints[key]&&<p className="budget-hint" id={`${id}-hint`}>{hints[key]}</p>}
  </div>;})}</div>;
}

function Bar({result}:{result:CashflowResult}){
  const income=result.monthly_income;
  if(income<=0)return null;
  const rent=result.essential_monthly_expenses-0;
  const parts=[
    {name:'월세·고정지출',value:rent,className:'seg-essential'},
    {name:'기타지출',value:result.other_monthly_expenses,className:'seg-other'},
    {name:'남는 돈',value:Math.max(0,result.disposable_after_policy),className:'seg-left'},
  ];
  const total=Math.max(income,result.total_monthly_expenses);
  return <div className="budget-bar-wrap"><div className="budget-bar" role="img" aria-label={parts.map(p=>`${p.name} ${won(p.value)}`).join(', ')}>{parts.map(p=>p.value>0&&<span key={p.name} className={p.className} style={{width:`${p.value/total*100}%`}}/>)}</div>
    <ul className="budget-legend">{parts.map(p=><li key={p.name}><i className={p.className}/> {p.name} <b>{won(p.value)}</b></li>)}</ul></div>;
}

export default function PublicBudget({onChange}:{onChange:(state:PublicBudgetState|null)=>void}){
  const [values,setValues]=useState<Values>(empty);
  const [errors,setErrors]=useState<Partial<Record<Key,string>>>({});
  const [result,setResult]=useState<CashflowResult|null>(null);
  const [changed,setChanged]=useState<Values>(empty);
  const [changedErrors,setChangedErrors]=useState<Partial<Record<Key,string>>>({});
  const [after,setAfter]=useState<CashflowResult|null>(null);
  const resultHeading=useRef<HTMLHeadingElement>(null);
  const afterHeading=useRef<HTMLHeadingElement>(null);

  function edit(key:Key,value:string){setValues(old=>({...old,[key]:value}));setResult(null);setAfter(null);onChange(null);}
  function editChanged(key:Key,value:string){setChanged(old=>({...old,[key]:value}));setAfter(null);if(result)onChange({before:result,after:null});}
  function submit(event:FormEvent){
    event.preventDefault();
    const parsed=parse(values);setErrors(parsed.errors);
    if(!parsed.input){setResult(null);return;}
    const next=calculateCashflow(parsed.input);
    setResult(next);setChanged(values);setChangedErrors({});setAfter(null);onChange({before:next,after:null});
    window.setTimeout(()=>resultHeading.current?.focus(),0);
  }
  function compare(event:FormEvent){
    event.preventDefault();
    if(!result)return;
    const parsed=parse(changed);setChangedErrors(parsed.errors);
    if(!parsed.input){setAfter(null);return;}
    const next=calculateCashflow(parsed.input);
    setAfter(next);onChange({before:result,after:next});
    window.setTimeout(()=>afterHeading.current?.focus(),0);
  }
  function applyPreset(key:Key,delta:number){
    const current=/^\d+$/.test(changed[key].trim())?Number(changed[key].trim()):0;
    editChanged(key,String(Math.max(0,current+delta)));
  }
  const deficit=result!==null&&result.disposable_after_policy<0;
  const rows=result&&after?[
    {name:'월 소득',before:result.monthly_income,after:after.monthly_income},
    {name:'지출 합계',before:result.total_monthly_expenses,after:after.total_monthly_expenses},
    {name:'한 달 여유자금',before:result.disposable_after_policy,after:after.disposable_after_policy},
    {name:'저축에 쓸 수 있는 금액',before:result.savable_amount,after:after.savable_amount},
  ]:[];

  return <section className="public-budget" aria-labelledby="public-budget-heading">
    <div className="budget-intro"><h2 id="public-budget-heading">한 달에 얼마를 모을 수 있을까요?</h2><p>소득과 지출을 넣으면 남는 돈을 계산하고, 그 금액으로 적금·예금을 찾아볼 수 있어요.</p></div>
    <form className="budget-panel" onSubmit={submit} noValidate>
      <Fields prefix="budget" values={values} errors={errors} keys={[...required,'user_savings_capacity']} onChange={edit}/>
      <div className="budget-actions"><button type="submit" className="finder-primary">여유자금 계산하기 <span aria-hidden="true">→</span></button><p className="budget-privacy">입력한 금액은 저장하거나 전송하지 않고, 이 화면에서만 계산해요.</p></div>
    </form>

    {result&&<div className="budget-result" data-testid="public-budget-result">
      <h3 ref={resultHeading} tabIndex={-1}>계산 결과</h3>
      <div className="budget-figures">
        <div className={`budget-figure main${deficit?' deficit':''}`}><span>한 달 여유자금</span><strong data-testid="public-disposable">{signed(result.disposable_after_policy)}</strong><p>{deficit?`매달 ${won(-result.disposable_after_policy)}이 부족해요. 저축보다 지출 점검이 먼저예요.`:'소득에서 월세·고정지출·기타지출을 뺀 금액이에요.'}</p></div>
        <div className="budget-figure"><span>지출 합계</span><strong>{won(result.total_monthly_expenses)}</strong><p>월세·고정지출 {won(result.essential_monthly_expenses)} + 기타 {won(result.other_monthly_expenses)}</p></div>
        <div className="budget-figure save"><span>저축에 쓸 수 있는 금액</span><strong data-testid="public-savable">{won(result.savable_amount)}</strong><p>{result.user_savings_capacity===null?'남는 돈 전부를 기준으로 했어요.':`정한 상한 ${won(result.user_savings_capacity)} 안에서 계산했어요.`}</p></div>
      </div>
      <Bar result={result}/>
      <div className="budget-next">{result.savable_amount>0?<a className="finder-primary budget-link" href={routeLinks.savings}>월 {won(result.savable_amount)}으로 상품 찾기 <span aria-hidden="true">→</span></a>:<p className="budget-hint">저축에 쓸 수 있는 금액이 0원이라 상품 추천으로 넘기지 않았어요.</p>}<a className="budget-secondary" href={routeLinks.programs}>받을 수 있는 지원 찾기 <span aria-hidden="true">→</span></a></div>
      <p className="budget-note">정책 지원금은 자동으로 더하지 않아요. 선정 여부와 금액이 확정되지 않았기 때문이에요. 받는다고 가정한 결과는 아래에서 따로 볼 수 있어요.</p>
    </div>}

    {result&&<SupportAssumption result={result}/>}

    {result&&<form className="budget-panel budget-whatif" onSubmit={compare} noValidate aria-labelledby="whatif-heading">
      <h3 id="whatif-heading">조건이 바뀌면 어떻게 될까요?</h3>
      <p className="budget-hint">월세 지원을 받거나 이사·이직을 하는 경우처럼, 숫자를 바꿔서 지금과 비교해 보세요. 가정일 뿐이며 지원 선정을 뜻하지 않아요.</p>
      <div className="budget-presets" role="group" aria-label="빠른 가정">{presets.map(p=><button type="button" key={p.label} onClick={()=>applyPreset(p.key,p.delta)}>{p.label}</button>)}</div>
      <Fields prefix="whatif" values={changed} errors={changedErrors} keys={[...required,'user_savings_capacity']} onChange={editChanged}/>
      <div className="budget-actions"><button type="submit" className="finder-primary">바꿔서 비교하기 <span aria-hidden="true">→</span></button></div>
    </form>}

    {result&&after&&<div className="budget-result budget-compare" data-testid="public-budget-compare">
      <h3 ref={afterHeading} tabIndex={-1}>지금과 바뀐 조건 비교</h3>
      <table><thead><tr><th scope="col">항목</th><th scope="col">지금</th><th scope="col">바뀐 조건</th><th scope="col">차이</th></tr></thead>
        <tbody>{rows.map(row=>{const diff=row.after-row.before;const good=row.name==='지출 합계'?diff<0:diff>0;return <tr key={row.name}><th scope="row">{row.name}</th><td>{won(row.before)}</td><td>{won(row.after)}</td><td className={diff===0?'same':good?'up':'down'}>{diff===0?'변화 없음':signed(diff)}</td></tr>;})}</tbody></table>
      <div className="budget-next">{after.savable_amount>0&&<a className="finder-primary budget-link" href={routeLinks.savings}>바뀐 금액 월 {won(after.savable_amount)}으로 상품 찾기 <span aria-hidden="true">→</span></a>}</div>
      <p className="budget-note">두 계산 모두 같은 식을 쓰고, 정책 지원금·이자·세금은 포함하지 않아요.</p>
    </div>}
  </section>;
}
