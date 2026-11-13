/* "What if I receive this support?" — an explicit assumption laid next to the real result.
   The parity-tested calculator (cashflow.ts) keeps policy benefits at 0; this never changes it
   and its output is never passed on to product recommendations. */
import {MAX_KRW,type CashflowResult} from './cashflow';

export const MAX_MONTHS=60;
export interface AssumedSupport{
  monthly_support:number; months:number;
  disposable_now:number; disposable_assumed:number;
  savable_now:number; savable_assumed:number;
  monthly_gain:number;   // extra amount that can go to savings each month
  total_gain:number;     // monthly_gain × months
  capped:boolean;        // the savings limit kept part of the support out of savings
}

export function assumeSupport(result:CashflowResult,monthlySupport:number,months:number):AssumedSupport{
  if(!Number.isSafeInteger(monthlySupport)||monthlySupport<0||monthlySupport>MAX_KRW)throw new RangeError('INVALID_SUPPORT');
  if(!Number.isSafeInteger(months)||months<1||months>MAX_MONTHS)throw new RangeError('INVALID_MONTHS');
  const disposable=result.disposable_after_policy+monthlySupport;
  const capacity=result.user_savings_capacity;
  // Same clamp as the calculator: a deficit stays, only the savable part is clamped.
  const savable=capacity===null?Math.max(0,disposable):Math.max(0,Math.min(disposable,capacity));
  const gain=savable-result.savable_amount;
  return {monthly_support:monthlySupport,months,disposable_now:result.disposable_after_policy,disposable_assumed:disposable,
    savable_now:result.savable_amount,savable_assumed:savable,monthly_gain:gain,total_gain:gain*months,
    capped:capacity!==null&&disposable>capacity&&gain<monthlySupport};
}
