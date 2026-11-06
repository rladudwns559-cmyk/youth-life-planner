import GroupedInput from './GroupedInput';
import { useEffect, useRef, useState } from 'react';
import { simulate, type PolicyResult, type RuleResult, type SimulationResult } from './api';
import { defaults, labels, parseForm, type FormValues } from './form';
import WhatIf from './WhatIf';
import SavingsPanel from './SavingsPanel';
import ProductComparisonPanel from './ProductComparisonPanel';
import SavingsMatches from './SavingsMatches';
import AssetPrograms from './AssetPrograms';
import RegionalPrograms from './RegionalPrograms';
import type {ComparisonResult} from './comparison-api';
import { EmptyResult, ServiceGuide } from './ServiceShell';
import {PortalHeader,PortalHome,PortalFooter,PageHeading,BackendPending,NeedsBudget} from './PortalShell';
import {usePortalRoute,usePageTransition,publicBackendPending} from './portal-routing';
import ProductExplorer from './ProductExplorer';
import './launch-design.css';
import './polish.css';

const money = (amount: number) => `${amount.toLocaleString('ko-KR')}원`;
const fieldNames: Record<string, string> = { age: '만 나이', region: '거주 지역', employment_status: '취업 상태', student_status: '재학 상태', household_income: '정책 기준의 가구소득' };
const statusNames = { PASS: '충족', FAIL: '미충족', UNKNOWN: '확인 필요' };
function conditionText(rule: RuleResult) {
  const { field, operator, value } = rule.expected_condition;
  const shown = value === 'unemployed' ? '미취업' : value === 'employed' ? '취업' : typeof value === 'number' && field === 'household_income' ? money(value) : String(value);
  const suffix = operator === 'gte' ? '이상' : operator === 'lte' ? '이하' : '일치';
  return `${fieldNames[field ?? ''] ?? field} · ${shown} ${suffix}`;
}
function PolicyCard({ policy }: { policy: PolicyResult }) {
  return <article className="policy-card">
    <div className="policy-heading"><div><span className="eyebrow">{policy.policy_id} · 합성 정책</span><h3>{policy.policy_name}</h3></div><span className={`badge ${policy.overall_status.toLowerCase()}`}>{policy.overall_status}</span></div>
    <p className="policy-status">{policy.display_status}</p>
    <ul className="conditions">{policy.rule_results.filter(rule => rule.expected_condition.field).map(rule => <li key={rule.rule_id}><span className={`condition-dot ${rule.status.toLowerCase()}`} aria-hidden="true" /><span>{conditionText(rule)}</span><strong>{statusNames[rule.status]}</strong></li>)}</ul>
    {policy.missing_fields.length > 0 && <p className="missing">추가 확인: {policy.missing_fields.map(field => fieldNames[field] ?? field).join(', ')}.{policy.missing_fields.includes('household_income') && ' 생활비 소득으로 대신 판단하지 않습니다.'}</p>}
    <details><summary>판정 근거 보기</summary>{policy.rule_results.map(rule => <div className="raw-reason" key={rule.rule_id}><span>{rule.rule_id} · {rule.reason_code}</span><span>입력값: {rule.evaluated_value === null ? '확인되지 않음' : String(rule.evaluated_value)}</span>{rule.evidence_refs.map(ref => <code key={ref}>{ref}</code>)}</div>)}<p className="muted">위 경로는 저장소의 합성 근거이며 실제 정책 공고가 아닙니다.</p></details>
  </article>;
}

export default function App() {
  const [legacyOpen,setLegacyOpen]=useState(false);
  const {route,visited,modality}=usePortalRoute();
  const transitionRef=usePageTransition(route,modality);
  const [savingPeriod,setSavingPeriod]=useState('');
  const periodMonths=/^\d+$/.test(savingPeriod)&&Number(savingPeriod)>=1&&Number(savingPeriod)<=120?Number(savingPeriod):null;
  const [scenarioComparison,setScenarioComparison]=useState<ComparisonResult|null>(null);
  const [form, setForm] = useState<FormValues>({ ...defaults });
  const [errors, setErrors] = useState<Partial<Record<keyof FormValues, string>>>({});
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  useEffect(() => () => controller.current?.abort(), []);
  function change(key: keyof FormValues, value: string) {
    setScenarioComparison(null);
    controller.current?.abort();
    setLoading(false); setResult(null); setError(''); setErrors({});
    setForm(previous => ({ ...previous, [key]: value }));
  }
  async function submit(event: React.FormEvent) {
    setScenarioComparison(null);
    event.preventDefault();
    if(publicBackendPending)return;
    const parsed = parseForm(form);
    setErrors(parsed.errors); setError(''); setResult(null);
    if (!parsed.input) return;
    controller.current?.abort();
    const request = new AbortController(); controller.current = request; setLoading(true);
    const timeout = window.setTimeout(() => request.abort('timeout'), 10000);
    try {
      const response = await simulate(parsed.input, request.signal);
      if (!request.signal.aborted) {
        setResult(response);
        window.setTimeout(() => resultHeading.current?.focus(), 0);
      }
    } catch (cause) {
      if (request.signal.aborted && request.signal.reason !== 'timeout') return;
      setError(cause instanceof Error && !(cause instanceof TypeError) && !request.signal.aborted ? cause.message : '계산 서버에 연결하지 못했습니다. 서버 실행 상태를 확인하고 다시 시도해 주세요.');
    } finally {
      window.clearTimeout(timeout);
      if (controller.current === request) setLoading(false);
    }
  }
  const numeric = (key: keyof FormValues, optional = false) => <div className="field" key={key}><label htmlFor={key}>{labels[key]}{optional && <span>선택</span>}</label><div className="input-unit"><GroupedInput id={key} name={key} inputMode="numeric" autoComplete="off" value={form[key]} onChange={e => change(key, e.target.value)} aria-invalid={!!errors[key]} aria-describedby={errors[key] ? `${key}-error` : optional ? `${key}-hint` : undefined} /><span>{key === 'age' ? '세' : '원'}</span></div>{optional && <small id={`${key}-hint`}>{key === 'age' ? '모르면 비워 두세요.' : '빈칸: 별도 상한 없음 · 0: 저축하지 않음'}</small>}{errors[key] && <small className="field-error" id={`${key}-error`}>{errors[key]}</small>}</div>;
  return <div className="portal-root">
    <PortalHeader route={route}/>
    <main id="main" className="portal-main"><div ref={transitionRef}>
      {route==='home'&&<div data-portal-page="home"><PortalHome/></div>}
      {visited.has('budget')&&<div data-portal-page="budget" hidden={route!=='budget'} className="portal-page">
        <PageHeading page="budget" eyebrow="월 예산 · 정책 조건 · What-if" title="나의 경제생활 진단" description="알고 있는 정보부터 입력하고, 내 생활의 변화도 함께 살펴보세요."/>
        <BackendPending/>
        <aside className="demo-notice"><strong>정책 계산은 합성 3개로 시연합니다.</strong><span>실제 신청·수급 가능성을 확정하지 않으며, 정책 지원금은 예산에 반영하지 않습니다.</span></aside>
      <div className="workspace-heading"><h2>나의 경제생활 진단</h2><p>알고 있는 정보부터 입력해 주세요. 모르는 정보는 비워 두어도 괜찮아요.</p></div>
      <div className="workspace">
        <section className="input-panel panel" aria-labelledby="input-heading"><div className="section-heading"><span className="step">01</span><div><h2 id="input-heading">나의 현재 상황</h2><p>입력한 정보는 저장하지 않습니다.</p></div></div>
          <form onSubmit={submit} noValidate><fieldset disabled={loading||publicBackendPending}><legend>기본 정보</legend><div className="form-grid">{numeric('age', true)}<div className="field"><label htmlFor="region">거주 지역 <span>선택</span></label><input id="region" autoComplete="off" placeholder="예: 안산시" value={form.region} onChange={e => change('region', e.target.value)} maxLength={80} /><small>합성 예시는 ‘안산시’와 정확히 비교합니다.</small></div>
          <div className="field"><label htmlFor="student_status">재학 상태</label><select id="student_status" value={form.student_status} onChange={e => change('student_status', e.target.value)}><option value="true">재학 중</option><option value="false">재학하지 않음</option><option value="">모름 / 미입력</option></select></div>
          <div className="field"><label htmlFor="employment_status">취업 상태</label><select id="employment_status" value={form.employment_status} onChange={e => change('employment_status', e.target.value)}><option value="employed">취업</option><option value="unemployed">미취업</option><option value="">모름 / 미입력</option></select></div></div><p className="hint">재학과 취업은 각각 입력합니다. 모르는 정보는 추측하지 않아도 됩니다.</p>
          </fieldset><fieldset disabled={loading||publicBackendPending}><legend>한 달의 수입과 지출</legend><p className="hint">생활비 소득은 정책의 가구소득·소득인정액과 다릅니다.</p><div className="form-grid">{numeric('monthly_income')}{numeric('monthly_rent')}{numeric('monthly_fixed_expenses')}{numeric('other_monthly_expenses')}</div><p className="hint">고정지출에는 월세를 제외하고 입력해 주세요.</p>{numeric('user_savings_capacity', true)}<div className="field saving-goal-field"><label htmlFor="saving-period">목표 저축 기간 <span>상품 자동 매칭용</span></label><div className="input-unit"><GroupedInput id="saving-period" inputMode="numeric" autoComplete="off" placeholder="예: 12" value={savingPeriod} onChange={e=>setSavingPeriod(e.target.value)} aria-invalid={savingPeriod!==''&&periodMonths===null} aria-describedby="saving-period-hint"/><span>개월</span></div><small id="saving-period-hint">1~120개월. 기간을 정하면 저축 투입 상한에 맞는 공식 적금이 자동으로 표시돼요.</small>{savingPeriod!==''&&periodMonths===null&&<small className="field-error">기간은 1~120 사이의 정수로 입력해 주세요.</small>}</div></fieldset>
          {Object.keys(errors).length > 0 && <p role="alert" className="error-message">입력값을 확인해 주세요. 금액은 쉼표 없이 원 단위 정수로 입력합니다.</p>}
          <button className="submit" type="submit" disabled={loading||publicBackendPending}>{publicBackendPending?'계산 서버 연결 준비 중':loading ? '계산하고 있어요…' : '내 상황으로 계산하기'}<span aria-hidden="true">→</span></button><p className="privacy-note">로그인 없이 · 소득·지출 저장 없이 · 외부 AI 전송 없이</p></form>
        </section>
        <section className="results" aria-labelledby="result-heading" aria-busy={loading}>
          <div className="section-heading"><span className="step">02</span><div><h2 id="result-heading" ref={resultHeading} tabIndex={-1}>나의 계산 결과</h2><p>{result ? '방금 제출한 입력으로 계산했습니다.' : '입력을 마친 뒤 계산 버튼을 눌러 주세요.'}</p></div></div>
          {error && <div role="alert" className="error-message"><strong>연결을 확인해 주세요.</strong><p>{error}</p><button type="button" onClick={() => document.querySelector<HTMLButtonElement>('button[type="submit"]')?.click()}>다시 시도</button></div>}
          {loading && <div role="status" className="empty-state"><span aria-hidden="true">…</span><h3>정책 조건과 월 예산을 확인하고 있어요.</h3></div>}
          {!result && !loading && !error && <EmptyResult />}
          {result && <><div className="budget-card panel"><div className="budget-label">한 달 여유자금</div><div className={`budget-value ${result.cashflow.disposable_after_policy < 0 ? 'deficit' : ''}`} data-testid="disposable">{money(result.cashflow.disposable_after_policy)}</div><p className="budget-caption">{result.cashflow.disposable_after_policy < 0 ? '지출이 수입보다 큽니다. 적자를 그대로 표시했습니다.' : '월 총수입에서 월세·고정지출·기타지출을 뺀 금액입니다.'}</p><div className="budget-metrics"><div><span>월 총수입</span><strong>{money(result.cashflow.total_monthly_income)}</strong></div><div><span>월 총지출</span><strong>{money(result.cashflow.total_monthly_expenses)}</strong></div><div><span>저축 투입 상한</span><strong data-testid="savable">{money(result.cashflow.savable_amount)}</strong></div></div><details><summary>수입·지출 상세</summary><dl className="breakdown"><div><dt>생활비 소득</dt><dd>{money(result.input_summary.monthly_income)}</dd></div><div><dt>월세</dt><dd>{money(result.input_summary.monthly_rent)}</dd></div><div><dt>고정지출 (월세 제외)</dt><dd>{money(result.input_summary.monthly_fixed_expenses)}</dd></div><div><dt>기타지출</dt><dd>{money(result.input_summary.other_monthly_expenses)}</dd></div><div><dt>사용자 저축 상한</dt><dd>{result.input_summary.user_savings_capacity === null ? '별도 상한 없음' : money(result.input_summary.user_savings_capacity)}</dd></div></dl></details><div className="benefit-note">정책 지원금 반영 <strong>{money(result.cashflow.policy_benefit_applied)}</strong><span>합성 정책 결과를 실제 수입으로 더하지 않습니다.</span></div></div>
          <details className="portal-archive"><summary>합성 정책 엔진 검증 결과 · 실제 추천 아님</summary><div className="policy-section-heading"><h3>정책 조건 살펴보기 <span>3</span></h3><p>합성 판정 · 실제 정책 신청 판단 아님</p></div><div className="policy-list">{result.policies.map(policy => <PolicyCard key={policy.policy_id} policy={policy} />)}</div><p className="result-footnote">제출 정보: {result.input_summary.age ?? '나이 미입력'}{result.input_summary.age !== null ? '세' : ''} · {result.input_summary.region ?? '지역 미입력'} · 재학 {result.input_summary.student_status === null ? '미입력' : result.input_summary.student_status ? '중' : '아님'} · {result.input_summary.employment_status === null ? '취업 정보 미입력' : result.input_summary.employment_status === 'employed' ? '취업' : '미취업'}<br />합성 기준일 {result.evaluation_date} · 데이터 {result.dataset_version}</p></details></>}
          {result && <WhatIf baseline={result} onComparisonChange={setScenarioComparison} />}
        </section>
      </div>
        <PortalFooter/>
      </div>}
      {(visited.has('programs')||visited.has('catalog'))&&<div data-portal-page={route==='catalog'?'catalog':'programs'} hidden={route!=='programs'&&route!=='catalog'} className="portal-page">
        {route==='catalog'?<PageHeading page="catalog" backTo="programs" eyebrow="정부·지자체·공익기관 공고" title="청년지원사업 보기" description="분야별 공고와 신청 일정을 살펴보고, 관심 있는 사업의 공식 신청 페이지를 확인하세요."/>:<PageHeading page="programs" eyebrow="정부·지자체·공익기관 지원정보" title="나에게 필요한 청년 지원" description="지역·나이·취업·월세 조건으로 전국과 내 지역의 지원사업을 함께 찾아보세요."/>}
        <RegionalPrograms browse={route==='catalog'} listPage={route==='catalog'}/>
        {!publicBackendPending&&<details className="portal-archive"><summary>기존 자산형성 10개 기초 추천 검증 자료</summary><AssetPrograms baseline={result} after={scenarioComparison?.after} goalMonths={periodMonths}/></details>}
        <PortalFooter/>
      </div>}
      {visited.has('savings')&&<div data-portal-page="savings" hidden={route!=='savings'} className="portal-page">
        <PageHeading page="savings" eyebrow="은행 적금 · 정기예금 · 공식 근거" title="내 조건에 맞는 상품 찾기" description="납입 금액과 기간, 가입 대상, 우대조건을 함께 비교하세요."/>
        <ProductExplorer monthlyAmount={publicBackendPending?undefined:result?.cashflow.savable_amount} termMonths={periodMonths} afterAmount={scenarioComparison?.after.cashflow.savable_amount}/>
        {!publicBackendPending&&<details className="portal-archive" onToggle={e=>setLegacyOpen(e.currentTarget.open)}><summary>기존 계산 검증 자료 · 일반 상품 추천 아님</summary><p>이전 합성 계산·4상품 비교·과거 자료의 재현을 위한 개발 검증 영역입니다.</p>
        {legacyOpen&&(result?<>
          <div className="portal-savings-period"><label htmlFor="matching-period">비교할 저축 기간</label><GroupedInput id="matching-period" inputMode="numeric" value={savingPeriod} placeholder="예: 12개월" onChange={e=>setSavingPeriod(e.target.value)}/><p>1~120개월 · 생활비 화면에서 입력한 기간과 함께 바뀝니다.</p></div>
          <SavingsMatches baseline={result} after={scenarioComparison?.after} termMonths={periodMonths}/>
          <SavingsPanel baseline={result}/>
          <details className="legacy-product-details"><summary>이전 IBK 상품 자료 비교 · 2025년 기준</summary><ProductComparisonPanel baseline={result} after={scenarioComparison?.after}/></details>
        </>:<NeedsBudget/>)}
        </details>}
        <PortalFooter/>
      </div>}
      {visited.has('guide')&&<div data-portal-page="guide" hidden={route!=='guide'} className="portal-page">
        <PageHeading page="guide" eyebrow="서비스 이용 안내" title="근거를 알고, 내 선택에 활용하세요." description="자료 범위와 검토일, 상품 조건을 읽는 방법을 안내합니다."/>
        <ServiceGuide/><PortalFooter/>
      </div>}
    </div></main>
  </div>;
}
