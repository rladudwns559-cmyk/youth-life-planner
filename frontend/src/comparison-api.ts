import type { SimulationInput, SimulationResult, Status, RuleResult } from './api';

export interface InputChange { field: keyof SimulationInput; before: string | number | boolean | null; after: string | number | boolean | null }
export interface RuleComparison { rule_id: string; field: string; before: RuleResult; after: RuleResult; input_changed: boolean; status_changed: boolean; explanation: string }
export interface PolicyTransition { policy_id: string; policy_name: string; before_status: Status; after_status: Status; status_changed: boolean; rules: RuleComparison[]; explanation: string }
export interface ComparisonResult {
  synthetic: true; test_only: true; before: SimulationResult; after: SimulationResult;
  numeric_deltas: Record<'monthly_income' | 'monthly_rent' | 'monthly_fixed_expenses' | 'other_monthly_expenses' | 'total_monthly_income' | 'total_monthly_expenses' | 'disposable_before_policy' | 'disposable_after_policy' | 'savable_amount' | 'policy_benefit_applied',number> & {user_savings_capacity:number|null};
  policy_transitions: PolicyTransition[]; changed_input_fields: InputChange[];
  explanation_facts: Record<string,unknown>; explanations: string[];
  unknown_information: {policy_id:string;before_status:Status;after_status:Status;before_missing_fields:string[];after_missing_fields:string[]}[];
  benefit_applied_krw: 0; disclaimer: string;
}
export class ComparisonApiError extends Error {
  kind: 'validation' | 'server';
  constructor(kind: 'validation' | 'server', message: string) { super(message); this.kind=kind; }
}
export async function compare(before:SimulationInput, after:SimulationInput, signal?:AbortSignal, base=''):Promise<ComparisonResult> {
  const response=await fetch(`${base}/api/synthetic/compare`,{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({before,after}),cache:'no-store',signal,
  });
  if (!response.ok) throw new ComparisonApiError(response.status===422?'validation':'server',response.status===422
    ? '비교 입력의 형식과 범위를 확인해 주세요.' : '서버에서 비교를 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.');
  try { return await response.json(); }
  catch { throw new ComparisonApiError('server','서버의 비교 응답을 읽지 못했습니다. 다시 시도해 주세요.'); }
}
