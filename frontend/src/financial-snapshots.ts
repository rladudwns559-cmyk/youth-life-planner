import historical from './public-data/product-expanded.json';
import renewalJSON from './public-data/financial-renewals.json';
import ended from './public-data/financial-sales-ended.json';

export type FinancialProduct=typeof historical.catalog.products[number];
export type FinancialCode='FIT'|'PARTIAL'|'TERM'|'BUDGET'|'INPUT'|'SCHEDULE'|'REVIEW'|'STALE'|'MISSING'|'UNSET';
export type FinancialRate={base_rate_percent:string;max_total_rate_percent:string|null;evidence_locator:string;sources:{url:string;title:string;reviewed_on:string;basis_date:string|null}[]};
type Table={product_ids:string[];boundaries:number[];months:Record<string,number>;patterns:number[][][]};
type RecordEntry={status:'CURRENT'|'UNCONFIRMED'|'DISCONTINUED';checked_on:string;valid_until:string|null;product:FinancialProduct;reason:string;rate_hold_reason?:string|null;compiled:{tables:Record<string,Table>;codebook:FinancialCode[]}|null};
type RenewalData={built_on:string;records:Record<string,RecordEntry>;recommendations:{rate_by_product:Record<string,Record<string,FinancialRate>>;order_calendar:Record<string,Record<string,number>>;order_pool:string[][]}};
const renewal=renewalJSON as unknown as RenewalData;

export function productRecheck(id:string,asOf:string){
 const record=renewal.records[id];return record&&asOf>=record.checked_on?record:null;
}
export function financialProducts(asOf:string):FinancialProduct[]{
 return historical.catalog.products.map(p=>productRecheck(p.product_id,asOf)?.product??p);
}
export function productEvidenceExpired(id:string,asOf:string){
 const r=productRecheck(id,asOf);
 return r?r.status==='CURRENT'&&(!r.valid_until||asOf>r.valid_until):asOf<historical.built_on||asOf>historical.valid_until;
}
/** Date routing and Python table lookup only. No eligibility/interest arithmetic. */
export function renewedDecision(id:string,amount:number|null,months:number,asOf:string):FinancialCode|null{
 const r=productRecheck(id,asOf);if(!r)return null;
 if(r.status!=='CURRENT')return 'REVIEW';
 if(!r.valid_until||asOf>r.valid_until)return 'STALE';
 const t=r.compiled?.tables[r.product.kind];if(!t)return 'MISSING';
 const row=amount===null?t.boundaries.length:t.boundaries.reduce((found,b,i)=>b<=amount?i:found,0);
 const value=t.patterns[t.months[String(months)]]?.[row]?.[t.product_ids.indexOf(id)];
 return typeof value==='number'?r.compiled!.codebook[value]??'MISSING':'MISSING';
}
export function renewedRate(id:string,months:number,asOf:string):FinancialRate|null|undefined{
 const r=productRecheck(id,asOf);if(!r)return undefined;
 if(r.status!=='CURRENT'||!r.valid_until||asOf>r.valid_until)return null;
 return renewal.recommendations.rate_by_product[id]?.[String(months)]??null;
}
export function renewedRank(id:string,kind:string,months:number,asOf:string):number|null{
 if(asOf<renewal.built_on)return null;
 const pool=renewal.recommendations.order_pool[renewal.recommendations.order_calendar[kind]?.[String(months)]??-1];
 if(!pool)return null;
 const i=pool.indexOf(id);return i<0?Number.MAX_SAFE_INTEGER:i;
}
export function financialFreshness(asOf:string){
 const seen=Object.values(renewal.records).filter(r=>r.checked_on<=asOf);
 const current=seen.filter(r=>r.status==='CURRENT');
 const active=current.filter(r=>r.valid_until&&asOf<=r.valid_until);
 const legacyActive=asOf>=historical.built_on&&asOf<=historical.valid_until;
 return {hasRechecks:seen.length>0,checked:seen.length,active:active.length,rateVerified:active.filter(r=>renewal.recommendations.rate_by_product[r.product.product_id]).length,held:seen.length-current.length,
  notRechecked:historical.catalog.products.length-seen.length,
  verifiedOn:seen.map(r=>r.checked_on).sort().at(-1)??historical.catalog.reviewed_on,
  validUntil:active.length?active.map(r=>r.valid_until!).sort()[0]:current.map(r=>r.valid_until!).sort().at(-1)??historical.valid_until,
  expired:!legacyActive&&active.length===0};
}
export function discontinuedRechecks(asOf:string){return ended.closures.filter(p=>p.checked_on<=asOf);}
