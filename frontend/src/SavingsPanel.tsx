import GroupedInput from './GroupedInput';
import { useEffect, useRef, useState } from 'react';
import type { SimulationResult } from './api';
import { calculateSavings, SavingsApiError, type SavingsResult } from './savings-api';

const money=(value:number)=>`${value.toLocaleString('ko-KR')}원`;
const defaults={payment:'200000',months:'12',rate:'3'};
type Form=typeof defaults;
const labels:Record<keyof Form,string>={payment:'적금 월 납입액',months:'적금 기간',rate:'적금 연 기본금리'};

export default function SavingsPanel({baseline}:{baseline:SimulationResult}) {
  const [form,setForm]=useState<Form>({...defaults});
  const [errors,setErrors]=useState<Partial<Record<keyof Form,string>>>({});
  const [result,setResult]=useState<SavingsResult|null>(null);
  const [error,setError]=useState('');const [loading,setLoading]=useState(false);
  const controller=useRef<AbortController|null>(null);
  useEffect(()=>()=>controller.current?.abort(),[]);
  function change(key:keyof Form,value:string) {
    controller.current?.abort();setLoading(false);setResult(null);setError('');setErrors({});
    setForm(previous=>({...previous,[key]:value}));
  }
  async function submit(event:React.FormEvent) {
    event.preventDefault();
    const next:Partial<Record<keyof Form,string>>={};
    for (const key of Object.keys(form) as (keyof Form)[]) if (!form[key].trim()) next[key]='값을 입력해 주세요.';
    if (!next.payment && (!/^\d+$/.test(form.payment) || Number(form.payment)>1e12)) next.payment='0~1,000,000,000,000원 정수를 입력해 주세요.';
    if (!next.months && (!/^\d+$/.test(form.months) || Number(form.months)<1 || Number(form.months)>120)) next.months='1~120개월 정수를 입력해 주세요.';
    if (!next.rate && (!/^(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,4})?$/.test(form.rate) || Number(form.rate)>100)) next.rate='0~100%, 소수 넷째 자리 이내로 입력해 주세요.';
    setErrors(next);setError('');setResult(null);
    if (Object.keys(next).length) return;
    controller.current?.abort();const request=new AbortController();controller.current=request;setLoading(true);
    const timer=window.setTimeout(()=>request.abort('timeout'),10000);
    try {
      const output=await calculateSavings({profile:baseline.input_summary,monthly_payment:Number(form.payment),term_months:Number(form.months),annual_base_rate_percent:form.rate},request.signal);
      if (!request.signal.aborted) setResult(output);
    } catch (cause) {
      if (request.signal.aborted && request.signal.reason!=='timeout') return;
      setError(request.signal.reason==='timeout' ? '적금 계산 응답 시간이 초과되었습니다. 다시 시도해 주세요.' : cause instanceof SavingsApiError ? cause.message : '적금 계산 서버에 연결하지 못했습니다. 연결 상태를 확인하고 다시 시도해 주세요.');
    } finally {window.clearTimeout(timer);if(controller.current===request)setLoading(false);}
  }
  const capacity=baseline.input_summary.user_savings_capacity;
  return <section className="savings-panel panel" aria-labelledby="savings-heading" aria-busy={loading}>
    <div className="section-heading"><span className="step">04</span><div><h2 id="savings-heading">매달 모으면, 만기에 얼마일까요?</h2><p>가상 정액적금 1개 · 실제 은행 상품이나 추천이 아닙니다.</p></div></div>
    <p className="hint">현재 상황의 저축 투입 상한 <strong>{money(baseline.cashflow.savable_amount)}</strong> · 사용자 상한 {capacity===null ? '미지정' : capacity===0 ? '0원으로 지정' : money(capacity)}</p>
    <p className="hint">매월 초 같은 금액 납입 · 고정 기본금리 · 단리 · 세전</p>
    <form onSubmit={submit} noValidate><div className="savings-inputs">{(Object.keys(form) as (keyof Form)[]).map(key=><div className="field" key={key}>
      <label htmlFor={`savings-${key}`}>{labels[key]}</label><div className="input-unit"><GroupedInput id={`savings-${key}`} inputMode={key==='rate'?'decimal':'numeric'} autoComplete="off" value={form[key]} onChange={e=>change(key,e.target.value)} aria-invalid={!!errors[key]} aria-describedby={errors[key]?`savings-${key}-error`:undefined}/><span>{key==='payment'?'원':key==='months'?'개월':'%'}</span></div>
      {errors[key]&&<small className="field-error" id={`savings-${key}-error`}>{errors[key]}</small>}</div>)}</div>
      {Object.keys(errors).length>0&&<p role="alert" className="error-message">적금 입력값을 확인해 주세요. 빈칸은 0으로 계산하지 않습니다.</p>}
      {error&&<p role="alert" className="error-message">{error}</p>}
      <button type="submit" className="submit" disabled={loading}>{loading?'적금 계산 중…':'적금 만기 계산하기'}<span aria-hidden="true">→</span></button>
    </form>
    {loading&&<p role="status">서버에서 만기금액을 계산하고 있어요.</p>}
    {result&&<div data-testid="savings-result" className="savings-result" aria-live="polite">
      <p className="eyebrow">가상 적금 · 세전 예상 결과</p><dl className="savings-amounts">
        <div><dt>총 납입원금</dt><dd data-testid="savings-principal">{money(result.total_principal_krw)}</dd></div>
        <div><dt>예상 세전이자</dt><dd data-testid="savings-interest">{money(result.estimated_interest_before_tax_krw)}</dd></div>
        <div><dt>예상 세전 만기금액</dt><dd data-testid="savings-maturity">{money(result.estimated_maturity_before_tax_krw)}</dd></div>
      </dl><p className="hint">월 {money(result.monthly_payment)} · {result.term_months}개월 · 연 {result.annual_base_rate_percent}%</p>
      <div className={result.budget_comparison.exceeds_budget_cap||result.budget_comparison.has_deficit?'savings-warning':'savings-budget'} role={result.budget_comparison.exceeds_budget_cap||result.budget_comparison.has_deficit?'alert':'status'}><strong>{result.budget_comparison.exceeds_budget_cap?'저축 투입 상한 초과':result.budget_comparison.has_deficit?'현재 월 예산 적자':'현재 예산과의 비교'}</strong><p>{result.budget_comparison.message}</p></div>
      <p className="hint">{result.rounding.description}</p><p className="hint">{result.disclaimer}</p>
      <details><summary>이 계산에서 지원하지 않는 조건</summary><ul>{result.unsupported_conditions.map(item=><li key={item}>{item}</li>)}</ul><p className="hint">위 조건이 있는 실제 상품의 만기금액으로 사용하지 마세요.</p></details>
    </div>}
    <p className="hint">입력 한도: 월 납입액 0~1조 원, 기간 1~120개월, 연 기본금리 0~100%. 실제 상품의 가입조건이 아닌 시뮬레이션 입력 한도입니다.</p>
  </section>;
}
