import type {SimulationInput} from './api';

export interface MatchingSource {
  source_id:string;bank_id:'KAKAO'|'KBANK'|'TOSS';official_url:string;document_url:string|null;
  document_name:string;rate_basis_date:string|null;verified_on:string;evidence_locator:string;
}
export interface MatchingProduct {
  product_id:string;bank_id:MatchingSource['bank_id'];institution:string;product_name:string;
  minimum_monthly_payment:number|null;maximum_monthly_payment:number|null;payment_step:number|null;
  min_months:number|null;max_months:number|null;allowed_months:number[]|null;
  preferential_conditions:string[];rate_note:string;eligibility_note:string;term_note:string;unknown_fields:string[];
}
export interface MatchingRow {
  product:MatchingProduct;source:MatchingSource;selected_base_rate_percent:string|null;selected_max_rate_percent:string|null;
  reason_codes:string[];reasons:string[];user_eligibility:'NOT_EVALUATED';preferential_conditions_met:'UNCONFIRMED';calculation:null;
}
export interface MatchingScenario {
  monthly_amount:number;term_months:number;matches:MatchingRow[];excluded:MatchingRow[];review_required:MatchingRow[];
  matched_count:number;excluded_count:number;review_count:number;total_count:number;
}
export interface SavingsMatchesResponse {
  dataset_version:string;evaluated_on:string;review_after_days:number;current:MatchingScenario;after:MatchingScenario|null;
  changes:{added:string[];removed:string[];retained:string[]}|null;actual_product_calculation_count:0;ranking:null;
  external_transmission:false;disclaimer:string;
}
export async function requestSavingsMatches(profile:SimulationInput,termMonths:number,after:SimulationInput|null,signal:AbortSignal):Promise<SavingsMatchesResponse> {
  const response=await fetch('/api/financial-products/match',{
    method:'POST',headers:{'Content-Type':'application/json'},cache:'no-store',signal,
    body:JSON.stringify({profile,term_months:termMonths,...(after?{after_profile:after}:{})}),
  });
  if(!response.ok)throw new Error(response.status===422?'기간과 입력 조건을 확인해 주세요.':'공식 적금 자료를 불러오지 못했습니다. 다시 시도해 주세요.');
  const data:unknown=await response.json();
  if(!data || typeof data!=='object')throw new Error('상품 응답 형식을 확인하지 못했습니다.');
  const value=data as SavingsMatchesResponse;
  const validScenario=(s:MatchingScenario)=>s && Number.isSafeInteger(s.monthly_amount) && Number.isInteger(s.term_months)
    && Array.isArray(s.matches) && Array.isArray(s.excluded) && Array.isArray(s.review_required)
    && s.matches.every(r=>r.product && r.source && typeof r.product.product_id==='string' && typeof r.source.official_url==='string');
  if(!validScenario(value.current) || value.current.term_months!==termMonths
    || (value.after!==null&&(!validScenario(value.after)||value.after.term_months!==termMonths))
    || ((after!==null)!==(value.after!==null))
    || value.actual_product_calculation_count!==0 || value.ranking!==null || value.external_transmission!==false
    || typeof value.disclaimer!=='string')throw new Error('상품 응답 형식을 확인하지 못했습니다.');
  return value;
}
