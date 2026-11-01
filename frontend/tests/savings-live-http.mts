// 기존 API 클라이언트로 실제 HTTP를 호출한다. fetch mock 없음.
import assert from 'node:assert/strict';
import {calculateSavings} from '../src/savings-api.ts';
const base=process.env.SIMULATION_API_ORIGIN??'http://127.0.0.1:8100';
const profile={age:24,region:'안산시',student_status:true,employment_status:'unemployed' as const,monthly_income:1500000,monthly_rent:450000,monthly_fixed_expenses:200000,other_monthly_expenses:350000,user_savings_capacity:300000};
const request={profile,monthly_payment:200000,term_months:12,annual_base_rate_percent:'3'};
const example=await calculateSavings(request,undefined,base);
assert.equal(example.total_principal_krw,2400000);assert.equal(example.estimated_interest_before_tax_krw,39000);assert.equal(example.estimated_maturity_before_tax_krw,2439000);
assert.equal(example.budget_comparison.savable_amount_krw,300000);assert.equal(example.budget_comparison.exceeds_budget_cap,false);
const over=await calculateSavings({...request,monthly_payment:400000},undefined,base);
assert.equal(over.monthly_payment,400000);assert.equal(over.budget_comparison.excess_krw,100000);assert.equal(over.total_principal_krw,4800000);
for(const [cap,mode,amount] of [[null,'UNSPECIFIED',500000],[0,'EXPLICIT_ZERO',0]] as const){
  const output=await calculateSavings({...request,profile:{...profile,user_savings_capacity:cap}},undefined,base);
  assert.equal(output.budget_comparison.savings_capacity_mode,mode);assert.equal(output.budget_comparison.savable_amount_krw,amount);
}
const deficit=await calculateSavings({...request,profile:{...profile,monthly_income:0}},undefined,base);
assert.equal(deficit.budget_comparison.has_deficit,true);assert.equal(deficit.cashflow.policy_benefit_applied,0);
await assert.rejects(()=>calculateSavings({...request,annual_base_rate_percent:'NaN'},undefined,base),/입력 형식/);
const unsupported=await fetch(`${base}/api/synthetic/savings/recurring`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...request,calculation_method:'COMPOUND'})});
assert.equal(unsupported.status,422);assert.equal((await unsupported.json()).errors[0].type,'UNSUPPORTED_ASSUMPTION');
console.log('M3.2 실제 HTTP: 원금 2,400,000원 / 세전이자 39,000원 / 만기 2,439,000원; 상한/미지정/0/적자/422 통과 (fetch mock 없음)');
