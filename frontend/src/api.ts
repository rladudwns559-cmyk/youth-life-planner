export type Status = 'PASS' | 'FAIL' | 'UNKNOWN';
export interface SimulationInput {
  age: number | null; region: string | null; student_status: boolean | null;
  employment_status: 'employed' | 'unemployed' | null;
  monthly_income: number; monthly_rent: number; monthly_fixed_expenses: number;
  other_monthly_expenses: number; user_savings_capacity: number | null;
}
export interface RuleResult {
  rule_id: string; status: Status; reason_code: string;
  evaluated_value: string | number | boolean | null;
  expected_condition: {field?: string; operator: string; value?: string | number | boolean; child_ids?: string[]};
  missing_fields: string[]; evidence_refs: string[];
}
export interface PolicyResult {
  policy_id: string; policy_name: string; overall_status: Status; display_status: string;
  missing_fields: string[]; rule_results: RuleResult[];
}
export interface SimulationResult {
  synthetic: true; test_only: true; dataset_version: string; evaluation_date: string;
  input_summary: SimulationInput; policies: PolicyResult[];
  cashflow: { monthly_income: number; essential_monthly_expenses: number; other_monthly_expenses: number;
    total_monthly_expenses: number; policy_benefit_applied: number; total_monthly_income: number;
    disposable_before_policy: number; disposable_after_policy: number; user_savings_capacity: number | null; savable_amount: number };
}

export async function simulate(input: SimulationInput, signal?: AbortSignal, base = ''): Promise<SimulationResult> {
  const response = await fetch(`${base}/api/synthetic/simulate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input), cache: 'no-store', signal,
  });
  if (!response.ok) throw new Error(response.status === 422
    ? '입력 형식과 범위를 확인한 뒤 다시 계산해 주세요.'
    : '계산 서버에 연결하지 못했습니다. 서버 실행 상태를 확인하고 다시 시도해 주세요.');
  return response.json();
}
