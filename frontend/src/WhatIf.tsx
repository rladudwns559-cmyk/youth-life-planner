import GroupedInput from './GroupedInput';
import { useEffect, useRef, useState } from 'react';
import ExplanationPanel from './ExplanationPanel';
import type { SimulationInput, SimulationResult } from './api';
import { compare, ComparisonApiError, type ComparisonResult } from './comparison-api';
import { labels, parseForm, type FormValues } from './form';

const money=(amount:number)=>`${amount.toLocaleString('ko-KR')}원`;
const signed=(amount:number)=>`${amount>0?'+':''}${money(amount)}`;
const fieldNames:Record<string,string>={...labels,household_income:'정책 기준의 가구소득'};
const statuses={PASS:'이용 가능성 높음',FAIL:'현재 조건과 맞지 않음',UNKNOWN:'추가 확인 필요'};
const valueText=(field:string,value:unknown)=>{
  if(value===null)return field==='user_savings_capacity'?'별도 상한 없음':'미입력';
  if(field==='employment_status')return value==='employed'?'취업':'미취업';
  if(field==='student_status')return value?'재학 중':'재학하지 않음';
  if(typeof value==='number')return field==='age'?`${value}세`:money(value);
  return String(value);
};
export function toForm(input:SimulationInput):FormValues {
  return Object.fromEntries(Object.entries(input).map(([key,value])=>[key,value===null?'':String(value)])) as FormValues;
}

function ComparisonView({result}:{result:ComparisonResult}) {
  const rows:[string,number,number,number][]=[
    ['월소득',result.before.cashflow.monthly_income,result.after.cashflow.monthly_income,result.numeric_deltas.monthly_income],
    ['월세',result.before.input_summary.monthly_rent,result.after.input_summary.monthly_rent,result.numeric_deltas.monthly_rent],
    ['고정지출',result.before.input_summary.monthly_fixed_expenses,result.after.input_summary.monthly_fixed_expenses,result.numeric_deltas.monthly_fixed_expenses],
    ['기타지출',result.before.input_summary.other_monthly_expenses,result.after.input_summary.other_monthly_expenses,result.numeric_deltas.other_monthly_expenses],
    ['월 총지출',result.before.cashflow.total_monthly_expenses,result.after.cashflow.total_monthly_expenses,result.numeric_deltas.total_monthly_expenses],
    ['월 여유자금',result.before.cashflow.disposable_after_policy,result.after.cashflow.disposable_after_policy,result.numeric_deltas.disposable_after_policy],
    ['저축 투입 상한',result.before.cashflow.savable_amount,result.after.cashflow.savable_amount,result.numeric_deltas.savable_amount],
    ['정책 혜택 반영',result.before.cashflow.policy_benefit_applied,result.after.cashflow.policy_benefit_applied,result.numeric_deltas.policy_benefit_applied],
  ];
  return <div className="comparison-output" data-testid="comparison-result">
    <h3>월 예산 비교</h3><p className="hint">현재와 변경 상황의 한 달 예산을 원 단위로 비교합니다.</p>
    <table className="comparison-table"><caption className="sr-only">월 예산 Before After 변화량 비교</caption><thead><tr><th scope="col">항목</th><th scope="col">현재<br/>Before</th><th scope="col">변경<br/>After</th><th scope="col">변화</th></tr></thead><tbody>{rows.map(([label,b,a,d])=><tr key={label} className={label==='월 여유자금'||label==='저축 투입 상한'?'key-row':''}><th scope="row">{label}</th><td>{money(b)}</td><td>{money(a)}</td><td data-testid={label==='월 여유자금'?'disposable-delta':label==='저축 투입 상한'?'savable-delta':undefined}>{signed(d)}</td></tr>)}</tbody></table>
    {(result.before.cashflow.disposable_after_policy<0||result.after.cashflow.disposable_after_policy<0)&&<p className="deficit-note">적자는 정상적인 계산 결과입니다. 음수를 그대로 표시하고 저축 투입 상한은 기존 계산기에 따라 표시합니다.</p>}
    <div className="comparison-explanations"><h3>어떤 변화가 있었나요?</h3><ul>{result.explanations.map((text,i)=><li key={i}>{text}</li>)}</ul></div>
    <details><summary>변경한 입력 {result.changed_input_fields.length}개 확인</summary>{result.changed_input_fields.length===0?<p>변경한 입력이 없습니다.</p>:<ul className="input-changes">{result.changed_input_fields.map(change=><li key={change.field}><strong>{fieldNames[change.field]}</strong><span>{valueText(change.field,change.before)} → {valueText(change.field,change.after)}</span></li>)}</ul>}</details>
    <h3 className="comparison-policy-title">정책별 Before → After</h3><div className="policy-list">{result.policy_transitions.map(policy=><article key={policy.policy_id} className="policy-card"><div className="policy-heading"><div><span className="eyebrow">{policy.policy_id} · 합성 정책</span><h3>{policy.policy_name}</h3></div><span className="transition-change">{policy.status_changed?'상태 변경':'상태 유지'}</span></div><div className="status-transition"><div><small>현재</small><span className={`badge ${policy.before_status.toLowerCase()}`}>{policy.before_status}</span><p>{statuses[policy.before_status]}</p></div><span aria-hidden="true">→</span><div><small>변경</small><span className={`badge ${policy.after_status.toLowerCase()}`}>{policy.after_status}</span><p>{statuses[policy.after_status]}</p></div></div><p className="transition-explanation">{policy.explanation}</p><details><summary>조건별 판정과 근거</summary>{policy.rules.map(rule=><div className="raw-reason" key={rule.rule_id}><strong>{fieldNames[rule.field]??rule.field} · {rule.before.status} → {rule.after.status}</strong><span>{rule.explanation}</span><span>판정 사유: {rule.before.reason_code} → {rule.after.reason_code}</span><span>확인한 입력: {valueText(rule.field,rule.before.evaluated_value)} → {valueText(rule.field,rule.after.evaluated_value)}</span>{rule.after.evidence_refs.map(ref=><code key={ref}>{ref}</code>)}</div>)}</details></article>)}</div>
    {result.unknown_information.length>0&&<aside className="missing"><strong>미확인 정보는 계속 확인이 필요합니다.</strong>{result.unknown_information.map(info=><p key={info.policy_id}>{info.policy_id}: 현재 {info.before_missing_fields.map(field=>fieldNames[field]??field).join(', ')||'누락 없음'} / 변경 {info.after_missing_fields.map(field=>fieldNames[field]??field).join(', ')||'누락 없음'} ({info.before_status} → {info.after_status})</p>)}<p>생활비 소득으로 가구소득을 채우지 않습니다. 누락 조건이 있어도 다른 조건이 미충족이면 최종 상태는 FAIL일 수 있습니다.</p></aside>}
    <p className="result-footnote">{result.disclaimer}<br/>합성 기준일 {result.before.evaluation_date} · 데이터 {result.before.dataset_version}</p>
  </div>;
}

export default function WhatIf({baseline,onComparisonChange}:{baseline:SimulationResult;onComparisonChange?:(result:ComparisonResult|null)=>void}) {
  const [opened,setOpened]=useState(false);
  const [form,setForm]=useState<FormValues>(()=>toForm(baseline.input_summary));
  const [result,setResult]=useState<ComparisonResult|null>(null);
  const [errors,setErrors]=useState<Partial<Record<keyof FormValues,string>>>({});
  const [error,setError]=useState<{kind:string;text:string}|null>(null);
  const [loading,setLoading]=useState(false);
  const current=useRef<{id:number;controller:AbortController}|null>(null);
  const sequence=useRef(0);
  const heading=useRef<HTMLHeadingElement>(null);
  useEffect(()=>()=>{++sequence.current;current.current?.controller.abort();},[]);
  function invalidate() {
    onComparisonChange?.(null);
    ++sequence.current;current.current?.controller.abort();current.current=null;
    setResult(null);setError(null);setErrors({});setLoading(false);
  }
  function change(key:keyof FormValues,value:string) {invalidate();setForm(previous=>({...previous,[key]:value}));}
  function reset() {invalidate();setForm(toForm(baseline.input_summary));}
  async function submit(event?:React.FormEvent) {
    event?.preventDefault();invalidate();
    const parsed=parseForm(form);setErrors(parsed.errors);
    if(!parsed.input){setError({kind:'입력 오류',text:'변경 입력을 확인해 주세요. 금액은 쉼표 없는 원 단위 정수로 입력합니다.'});return;}
    const id=++sequence.current;const controller=new AbortController();current.current={id,controller};setLoading(true);
    const timeout=window.setTimeout(()=>controller.abort('timeout'),10000);
    try {
      const output=await compare(baseline.input_summary,parsed.input,controller.signal);
      if(sequence.current===id&&!controller.signal.aborted){setResult(output);onComparisonChange?.(output);window.setTimeout(()=>heading.current?.focus(),0);}
    } catch(cause) {
      if(sequence.current!==id)return;
      if(controller.signal.aborted&&controller.signal.reason!=='timeout')return;
      setError(controller.signal.reason==='timeout'?{kind:'요청 시간 초과',text:'10초 안에 응답하지 않았습니다. 다시 비교해 주세요.'}:
        cause instanceof ComparisonApiError?{kind:cause.kind==='validation'?'입력 오류':'서버 오류',text:cause.message}:
        {kind:'네트워크 오류',text:'비교 서버에 연결하지 못했습니다. 연결 상태를 확인하고 다시 시도해 주세요.'});
    } finally {window.clearTimeout(timeout);if(sequence.current===id){setLoading(false);current.current=null;}}
  }
  const number=(key:keyof FormValues,optional=false)=><div className="field" key={key}><label htmlFor={`after-${key}`}>변경 {labels[key]}{optional&&<span>선택</span>}</label><div className="input-unit"><GroupedInput id={`after-${key}`} inputMode="numeric" autoComplete="off" value={form[key]} onChange={event=>change(key,event.target.value)} aria-invalid={!!errors[key]} aria-describedby={errors[key]?`after-${key}-error`:undefined}/><span>{key==='age'?'세':'원'}</span></div>{errors[key]&&<small className="field-error" id={`after-${key}-error`}>{errors[key]}</small>}</div>;
  return <section className="what-if panel" aria-labelledby="what-if-heading"><div className="section-heading"><span className="step">03</span><div><h2 id="what-if-heading">상황이 바뀐다면?</h2><p>소득과 지출, 취업상태를 바꿔 현재와 비교해 보세요.</p></div></div>
    {!opened?<><p className="hint">방금 계산한 현재 상황을 복사해 변경 시나리오를 만듭니다.</p><button type="button" className="what-if-open" onClick={()=>setOpened(true)}>현재 상황으로 비교 시작 <span aria-hidden="true">→</span></button></>:<>
      <div className="baseline-summary"><strong>현재 상황 · Before</strong><p>{baseline.input_summary.region??'지역 미입력'} · {valueText('age',baseline.input_summary.age)} · {valueText('student_status',baseline.input_summary.student_status)} · {valueText('employment_status',baseline.input_summary.employment_status)}</p><p>월소득 {money(baseline.input_summary.monthly_income)} · 월세 {money(baseline.input_summary.monthly_rent)} · 저축 상한 {valueText('user_savings_capacity',baseline.input_summary.user_savings_capacity)}</p><small>현재 입력을 수정하면 비교는 닫힙니다. 현재 상황을 다시 계산해 비교를 시작하세요.</small></div>
      <form onSubmit={submit} noValidate aria-label="변경 시나리오"><h3>변경 시나리오 · After</h3><p className="hint">현재 값을 복사했습니다. 한 항목만 바꾸거나 그대로 비교해도 됩니다.</p><div className="form-grid">{number('monthly_income')}{number('monthly_rent')}{number('user_savings_capacity',true)}<div className="field"><label htmlFor="after-employment_status">변경 취업 상태</label><select id="after-employment_status" value={form.employment_status} onChange={event=>change('employment_status',event.target.value)}><option value="employed">취업</option><option value="unemployed">미취업</option><option value="">모름 / 미입력</option></select></div></div><p className="hint">저축 상한 빈칸: 별도 상한 없음 · 0원: 저축하지 않음</p><details className="additional-inputs"><summary>나이·지역·재학·그 외 지출도 변경하기</summary><div className="form-grid">{number('age',true)}<div className="field"><label htmlFor="after-region">변경 거주 지역</label><input id="after-region" value={form.region} autoComplete="off" maxLength={80} onChange={event=>change('region',event.target.value)}/></div><div className="field"><label htmlFor="after-student_status">변경 재학 상태</label><select id="after-student_status" value={form.student_status} onChange={event=>change('student_status',event.target.value)}><option value="true">재학 중</option><option value="false">재학하지 않음</option><option value="">모름 / 미입력</option></select></div>{number('monthly_fixed_expenses')}{number('other_monthly_expenses')}</div></details><div className="comparison-actions"><button type="button" className="reset-comparison" onClick={reset}>현재 값으로 다시 설정</button><button className="submit" type="submit" disabled={loading}>{loading?'두 상황을 비교하고 있어요…':'Before / After 비교하기'}</button></div></form>
      <div className="comparison-result-region" aria-busy={loading}><h3 ref={heading} tabIndex={-1} className={result?'comparison-result-heading':'sr-only'}>시나리오 비교 결과</h3>{loading&&<p role="status" className="comparison-loading">현재와 변경 상황을 각각 계산하고 있습니다.</p>}{error&&<div role="alert" className="error-message"><strong>{error.kind}</strong><p>{error.text}</p><button type="button" onClick={()=>submit()}>비교 다시 시도</button></div>}{result&&<><ComparisonView result={result}/><ExplanationPanel comparison={result}/></>}</div>
    </>}
  </section>;
}

