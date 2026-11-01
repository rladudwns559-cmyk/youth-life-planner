import type { SimulationInput } from './api';

export const defaults = {
  age: '24', region: '안산시', student_status: 'true', employment_status: 'employed',
  monthly_income: '1500000', monthly_rent: '450000', monthly_fixed_expenses: '200000',
  other_monthly_expenses: '350000', user_savings_capacity: '300000',
};
export type FormValues = typeof defaults;
export const labels: Record<keyof FormValues, string> = {
  age: '만 나이', region: '거주 지역', student_status: '재학 상태', employment_status: '취업 상태',
  monthly_income: '월 생활비 소득', monthly_rent: '월세', monthly_fixed_expenses: '월 고정지출',
  other_monthly_expenses: '월 기타지출', user_savings_capacity: '사용자 저축 상한',
};
export function parseForm(form: FormValues): { input?: SimulationInput; errors: Partial<Record<keyof FormValues, string>> } {
  const errors: Partial<Record<keyof FormValues, string>> = {};
  const number = (key: keyof FormValues, max: number, optional = false): number | null => {
    const raw = form[key].trim();
    if (!raw && optional) return null;
    if (!/^\d+$/.test(raw) || !Number.isSafeInteger(Number(raw)) || Number(raw) > max) {
      errors[key] = `${labels[key]}: 0~${max.toLocaleString('ko-KR')} 범위의 정수를 입력해 주세요.`;
      return null;
    }
    return Number(raw);
  };
  const age = number('age', 120, true);
  const monthly_income = number('monthly_income', 1e12);
  const monthly_rent = number('monthly_rent', 1e12);
  const monthly_fixed_expenses = number('monthly_fixed_expenses', 1e12);
  const other_monthly_expenses = number('other_monthly_expenses', 1e12);
  const user_savings_capacity = number('user_savings_capacity', 1e12, true);
  if (form.region.trim().length > 80) errors.region = '지역은 80자 이내로 입력해 주세요.';
  if (Object.keys(errors).length) return { errors };
  return { errors, input: {
    age, region: form.region.trim() || null,
    student_status: form.student_status === '' ? null : form.student_status === 'true',
    employment_status: form.employment_status === '' ? null : form.employment_status as 'employed' | 'unemployed',
    monthly_income: monthly_income!, monthly_rent: monthly_rent!, monthly_fixed_expenses: monthly_fixed_expenses!,
    other_monthly_expenses: other_monthly_expenses!, user_savings_capacity,
  } };
}
