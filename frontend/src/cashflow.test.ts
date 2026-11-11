import {describe,it,expect} from 'vitest';
import {calculateCashflow,MAX_KRW,type CashflowInput,type CashflowResult} from './cashflow';
import parity from './testing/cashflow-parity.json';

describe('browser cashflow port',()=>{
  it('matches every Python-calculated case exactly',()=>{
    const cases=parity.cases as {input:CashflowInput;expected:CashflowResult}[];
    expect(cases.length).toBeGreaterThanOrEqual(200);
    for(const {input,expected} of cases)expect(calculateCashflow(input)).toEqual(expected);
  });
  it('keeps a deficit visible and never saves from it',()=>{
    const r=calculateCashflow({monthly_income:1000000,monthly_rent:700000,monthly_fixed_expenses:300000,other_monthly_expenses:200000,user_savings_capacity:null});
    expect(r.disposable_after_policy).toBe(-200000);expect(r.savable_amount).toBe(0);expect(r.policy_benefit_applied).toBe(0);
  });
  it.each([[-1],[1.5],[MAX_KRW+1],[Number.NaN]])('rejects %s instead of calculating',value=>{
    expect(()=>calculateCashflow({monthly_income:value,monthly_rent:0,monthly_fixed_expenses:0,other_monthly_expenses:0,user_savings_capacity:null})).toThrow(RangeError);
  });
});
