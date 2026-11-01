// 실제 FastAPI+브라우저 클라이언트 경로. fetch mock 없음.
import assert from 'node:assert/strict';
import {getProducts,compareProducts} from '../src/products-api.ts';
const base=process.env.SIMULATION_API_ORIGIN??'http://127.0.0.1:8100';
const profile={age:24,region:'안산시',student_status:true,employment_status:'unemployed' as const,monthly_income:1500000,monthly_rent:450000,monthly_fixed_expenses:200000,other_monthly_expenses:350000,user_savings_capacity:300000};
const list=await getProducts(undefined,base);assert.equal(list.information_count,3);assert.equal(list.compatible_count,0);
assert(list.products.every(p=>p.basis_date==='2025-12-31'&&p.accumulation_method==='FLEXIBLE'));
const request={profile,after_profile:{...profile,monthly_income:1800000,monthly_rent:550000,user_savings_capacity:500000},monthly_payment:400000,term_months:12,product_ids:list.products.map(p=>p.product_id)};
const result=await compareProducts(request,undefined,base);
assert.equal(result.calculated_count,0);assert.equal(result.ranking,null);assert(result.results.every(r=>r.calculation===null));
assert(result.results.every(r=>r.reason_codes.includes('ACCUMULATION_UNSUPPORTED')));
assert(result.results.find(r=>r.product_id==='IBK-DDAY-SAVINGS')!.reason_codes.includes('ABOVE_MAXIMUM'));
assert.equal(result.budget.excess_krw,100000);assert.equal(result.after_budget!.exceeds_budget_cap,false);
assert.equal(result.budget.policy_benefit_applied,0);assert.equal(result.after_budget!.policy_benefit_applied,0);
await assert.rejects(()=>compareProducts({...request,product_ids:['MISSING']},undefined,base),/상품 선택/);
console.log('M3.3 실제 HTTP: 공식 과거 스냅샷3/계산0, 자유적립식 거부, 한도 초과, 전후 예산 30만→50만, 지원금0, 잘못된 ID422 통과 (fetch mock 없음)');
