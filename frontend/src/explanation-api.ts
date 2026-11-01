import type { SimulationInput, Status } from './api';

export interface ExplanationMoney {field:string;label:string;before:number|null;after:number|null;delta:number|null;text:string}
export interface ExplanationPolicy {policy_id:string;before_status:Status;after_status:Status;text:string;rules:{rule_id:string;field:string;before_status:Status;after_status:Status;before_reason:string;after_reason:string;before_missing:string[];after_missing:string[];source_refs:string[]}[]}
export interface ExplanationUnknown {policy_id:string;before_status:Status;after_status:Status;before_missing_fields:string[];after_missing_fields:string[]}
export interface ExplanationResult {
  synthetic:true;test_only:true;explanation_source:'deterministic'|'deterministic_fallback'|'llm'|'validated_test_double';
  explanation_text:string;fallback:boolean;fallback_reason:string|null;ai_attempted:boolean;ai_executed:boolean;ai_success:boolean;
  validation_passed:boolean;external_transmission:false;provider_kind:'none'|'ollama_local'|'test_double';related_policy_ids:string[];
  document:{summary:string;changed_facts:ExplanationMoney[];policy_explanations:ExplanationPolicy[];unknown_information:ExplanationUnknown[];next_actions:{policy_id:string;field:string;text:string}[]};
  unknown_information:ExplanationUnknown[];facts:{assumptions:string[];dataset_version:string;evaluation_date:string};disclaimer:string;
}
export class ExplanationApiError extends Error {
  kind:'validation'|'server'|'response';
  constructor(kind:'validation'|'server'|'response',message:string){super(message);this.kind=kind;}
}
export async function requestExplanation(before:SimulationInput,after:SimulationInput,signal?:AbortSignal,base=''):Promise<ExplanationResult>{
  const response=await fetch(`${base}/api/synthetic/explain`,{method:'POST',headers:{'Content-Type':'application/json'},cache:'no-store',
    body:JSON.stringify({before,after,mode:'ai_if_available'}),signal});
  if(!response.ok)throw new ExplanationApiError(response.status===422?'validation':'server',response.status===422?'설명 입력의 형식과 범위를 확인해 주세요.':'설명 서버에서 응답하지 못했습니다.');
  let value:ExplanationResult;
  try{value=await response.json();}
  catch{throw new ExplanationApiError('response','설명 응답을 읽지 못했습니다.');}
  if(value?.synthetic!==true||!value.document||typeof value.document.summary!=='string'||!Array.isArray(value.document.changed_facts)||
    !Array.isArray(value.document.policy_explanations)||!Array.isArray(value.document.next_actions)||!Array.isArray(value.unknown_information)||
    !Array.isArray(value.facts?.assumptions)||!['llm','deterministic','deterministic_fallback','validated_test_double'].includes(value.explanation_source)){
    throw new ExplanationApiError('response','설명 응답 형식이 올바르지 않습니다.');
  }
  const status=(s:unknown)=>s==='PASS'||s==='FAIL'||s==='UNKNOWN';
  if(value.external_transmission!==false||!value.document.changed_facts.every(f=>typeof f.text==='string')||
    !value.document.policy_explanations.every(p=>typeof p.policy_id==='string'&&typeof p.text==='string'&&status(p.before_status)&&status(p.after_status)&&Array.isArray(p.rules)&&p.rules.every(r=>Array.isArray(r.source_refs)))||
    !value.unknown_information.every(u=>Array.isArray(u.before_missing_fields)&&Array.isArray(u.after_missing_fields))||
    value.explanation_source==='llm'&&(!value.ai_executed||!value.ai_success||value.fallback)){
    throw new ExplanationApiError('response','설명 응답 형식이 올바르지 않습니다.');
  }
  return value;
}

