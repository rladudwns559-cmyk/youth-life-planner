// 실제 FastAPI 서버가 필요하다. fetch를 mock으로 대체하지 않는다.
import assert from 'node:assert/strict';
import { simulate } from '../src/api.ts';

const base = process.env.SIMULATION_API_ORIGIN ?? 'http://127.0.0.1:8100';
const profile = {age:24,region:'안산시',student_status:true,employment_status:'unemployed' as const,monthly_income:1500000,monthly_rent:450000,monthly_fixed_expenses:200000,other_monthly_expenses:350000,user_savings_capacity:300000};
const before = await simulate(profile, undefined, base);
assert.deepEqual(before.policies.map(p=>p.overall_status),['PASS','PASS','UNKNOWN']);
assert.equal(before.cashflow.disposable_after_policy,500000);
assert.equal(before.cashflow.savable_amount,300000);
const after = await simulate({...profile,employment_status:'employed',monthly_income:1800000,monthly_rent:550000,user_savings_capacity:500000},undefined,base);
assert.deepEqual(after.policies.map(p=>p.overall_status),['PASS','FAIL','UNKNOWN']);
assert.equal(after.cashflow.disposable_after_policy,700000);
assert.equal(after.cashflow.savable_amount,500000);
assert.equal(after.cashflow.policy_benefit_applied,0);
await assert.rejects(()=>simulate({...profile,monthly_income:-1},undefined,base),/입력 형식과 범위/);
console.log('실제 HTTP 검증: 시나리오 전/후 및 422 오류 응답 통과 (fetch mock 없음)');
