import {useEffect,useRef,useState} from 'react';
import type {ComparisonResult} from './comparison-api';
import {requestExplanation,ExplanationApiError,type ExplanationResult} from './explanation-api';

const statusLabel={PASS:'이용 가능성 높음',FAIL:'현재 조건과 맞지 않음',UNKNOWN:'추가 확인 필요'};
const fieldLabel:Record<string,string>={age:'만 나이',region:'거주 지역',employment_status:'취업 상태',student_status:'재학 상태',household_income:'정책 기준의 가구소득'};
const failures:Record<string,string>={PROVIDER_NOT_CONFIGURED:'실제 AI 모델이 설정되지 않았습니다.',TIMEOUT:'AI 응답 시간이 초과됐습니다.',PROVIDER_UNAVAILABLE:'AI 제공업체에 연결하지 못했습니다.',INVALID_JSON:'AI 응답 구조를 확인할 수 없었습니다.',NUMBER_MISMATCH:'AI 응답의 금액이 계산 결과와 달랐습니다.',POLICY_STATE_MISMATCH:'AI 응답의 정책 정보가 계산 결과와 달랐습니다.',UNKNOWN_MISSING:'AI 응답에서 미확인 정보가 달라졌습니다.',RESPONSE_TOO_LONG:'AI 응답이 길이 제한을 넘었습니다.',UNSUPPORTED_ACTION:'AI가 근거 없는 확인 행동을 만들었습니다.',UNSUPPORTED_NARRATIVE:'AI 설명이 허용된 표현 범위를 벗어났습니다.',GENERATION_FAILED:'AI 설명 생성에 실패했습니다.'};

export default function ExplanationPanel({comparison}:{comparison:ComparisonResult}){
  const [result,setResult]=useState<ExplanationResult|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const current=useRef<AbortController|null>(null);
  const version=useRef(0);
  useEffect(()=>{++version.current;current.current?.abort();setResult(null);setError('');setLoading(false);
    return()=>{++version.current;current.current?.abort();};},[comparison]);
  async function generate(){
    current.current?.abort();const controller=new AbortController();current.current=controller;
    const id=++version.current;setLoading(true);setError('');setResult(null);
    const timeout=window.setTimeout(()=>controller.abort('timeout'),12000);
    try{
      const response=await requestExplanation(comparison.before.input_summary,comparison.after.input_summary,controller.signal);
      if(response.facts.dataset_version!==comparison.before.dataset_version||response.facts.evaluation_date!==comparison.before.evaluation_date){
        throw new ExplanationApiError('response','계산 데이터 기준이 바뀌었습니다. 두 상황을 다시 비교해 주세요.');
      }
      if(version.current===id&&!controller.signal.aborted)setResult(response);
    }catch(cause){
      if(version.current!==id||controller.signal.aborted&&controller.signal.reason!=='timeout')return;
      setError(controller.signal.reason==='timeout'?'설명 요청 시간이 초과됐습니다. 기존 비교 결과는 그대로입니다.':
        cause instanceof ExplanationApiError?cause.message:'설명 서버에 연결하지 못했습니다. 기존 비교 결과는 그대로입니다.');
    }finally{
      window.clearTimeout(timeout);if(version.current===id){setLoading(false);current.current=null;}
    }
  }
  return <section className="explanation-panel" aria-labelledby="explanation-heading" aria-busy={loading}>
    <h3 id="explanation-heading">이 결과를 쉽게 이해하기</h3>
    <p className="hint">Python이 계산한 사실을 설명합니다. 외부 AI로 전송하지 않으며, 로컬 모델이 없으면 정형 설명을 제공합니다.</p>
    <button type="button" className="what-if-open" disabled={loading} onClick={generate}>{loading?'설명을 준비하고 있어요…':result?'설명 다시 생성':'한국어 설명 생성'}</button>
    {loading&&<p role="status">설명을 준비하는 동안 위 비교 결과를 계속 확인할 수 있습니다.</p>}
    {error&&<div role="alert" className="error-message"><p>{error}</p><button type="button" onClick={generate}>설명 다시 시도</button></div>}
    {result&&<div className="explanation-output" data-testid="explanation-result">
      <p className="explanation-mode"><strong>{result.explanation_source==='llm'?'생성형 AI 설명':result.explanation_source==='validated_test_double'?'시험용 응답 · 실제 AI 아님':result.fallback?'정형 설명으로 대체':'정형 설명'}</strong></p>
      {result.fallback&&<p className="hint">{failures[result.fallback_reason??'']??'AI 응답을 사용하지 않았습니다.'} 기존 Python 결과로 작성했습니다.</p>}
      <p className="explanation-summary">{result.document.summary}</p>
      <h4>월 예산이 달라진 이유</h4><ul>{result.document.changed_facts.map(f=><li key={f.field}>{f.text}</li>)}</ul>
      <h4>정책별 변화 이유</h4>{result.document.policy_explanations.map(p=><article className="explanation-policy" key={p.policy_id}>
        <strong>{p.policy_id} · 합성 정책</strong><p>{statusLabel[p.before_status]} → {statusLabel[p.after_status]}</p><p>{p.text}</p>
        <details><summary>설명에 사용한 조건과 근거</summary>{p.rules.map(r=><div className="raw-reason" key={r.rule_id}>
          <span>{fieldLabel[r.field]??r.field}: {r.before_status} → {r.after_status}</span><span>{r.before_reason} → {r.after_reason}</span>
          {r.source_refs.map(ref=><code key={ref}>{ref}</code>)}</div>)}</details>
      </article>)}
      <h4>추가 확인사항</h4>{result.unknown_information.length===0?<p>이번 합성 비교에서 미확인으로 남은 정보가 없습니다.</p>:<ul>{result.unknown_information.map(u=><li key={u.policy_id}>
        {u.policy_id}: 변경 전 {u.before_missing_fields.map(f=>fieldLabel[f]??f).join(', ')||'누락 없음'} / 변경 후 {u.after_missing_fields.map(f=>fieldLabel[f]??f).join(', ')||'누락 없음'}</li>)}</ul>}
      <ul>{result.document.next_actions.map(a=><li key={`${a.policy_id}-${a.field}`}>{a.policy_id}: {a.text}</li>)}</ul>
      <details><summary>설명 방식과 계산 가정</summary><p>실제 AI 실행: {result.ai_executed?'예':'아니요'} · AI 설명 검증 통과: {result.ai_success?'예':'아니요'}</p><ul>{result.facts.assumptions.map(a=><li key={a}>{a}</li>)}</ul><p>AI 출력 검증은 위험을 줄이는 장치이며 자연어의 모든 오류를 제거하는 보장은 아닙니다.</p></details>
      <p className="result-footnote">{result.disclaimer}</p>
    </div>}
  </section>;
}
