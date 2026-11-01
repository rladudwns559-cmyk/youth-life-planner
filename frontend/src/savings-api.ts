import type { SimulationInput, SimulationResult } from './api';

export interface SavingsInput {
  profile: SimulationInput; monthly_payment: number; term_months: number; annual_base_rate_percent: string;
}
export interface SavingsResult {
  synthetic: true; test_only: true; monthly_payment: number; term_months: number;
  annual_base_rate_percent: string; annual_rate_ratio: string;
  total_principal_krw: number; estimated_interest_before_tax_krw: number; estimated_maturity_before_tax_krw: number;
  unrounded_interest_krw: string; calculation_method: string;
  assumptions: Record<string,string>; rounding: Record<string,string>; unsupported_conditions: string[];
  cashflow: SimulationResult['cashflow'];
  budget_comparison: {savable_amount_krw: number; requested_monthly_payment_krw: number; exceeds_budget_cap: boolean;
    excess_krw: number; has_deficit: boolean; savings_capacity_mode: 'UNSPECIFIED' | 'EXPLICIT_ZERO' | 'EXPLICIT_LIMIT';
    user_savings_capacity_krw: number | null; policy_benefit_applied: 0; message: string};
  disclaimer: string;
}
export class SavingsApiError extends Error {
  kind: 'validation' | 'server';
  constructor(kind: 'validation' | 'server') {
    super(kind === 'validation' ? '적금 입력 형식·범위 또는 지원하는 계산 방식을 확인해 주세요.' : '적금 계산 서버에서 오류가 발생했습니다. 잠시 뒤 다시 시도해 주세요.');
    this.kind=kind;
  }
}
export async function calculateSavings(input: SavingsInput, signal?: AbortSignal, base=''): Promise<SavingsResult> {
  const response=await fetch(`${base}/api/synthetic/savings/recurring`, {
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(input),signal,cache:'no-store',
  });
  if (!response.ok) throw new SavingsApiError(response.status===422 ? 'validation' : 'server');
  try { return await response.json(); }
  catch { throw new SavingsApiError('server'); }
}
