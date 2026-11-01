import type {SimulationInput} from './api';
import type {SavingsResult} from './savings-api';
export interface ProductRate {min_months:number;max_months:number;base_rate_percent:string|null;max_total_rate_percent:string|null;evidence_locator:string}
export interface OfficialSource {source_id:string;official_url:string;title:string;document_id:string;source_date:string;verified_on:string;license_label:string;license_url:string;raw_sha256:string}
export interface OfficialProduct {
  product_id:string;product_name:string;institution:string;snapshot_version:string;source_id:string;evidence_locator:string;
  basis_date:string;collected_on:string;verified_on:string;official_material_status:string;key_fields_status:string;subscription_status:string;
  target:string;term_description:string;minimum_monthly_payment:number|null;maximum_monthly_payment:number|null;payment_step:number|null;
  rate_options:ProductRate[];max_preferential_bonus_percentage_points:string|null;preferential_conditions:string[];
  accumulation_method:string;rate_type:string;interest_method:string;deposit_timing:string;date_basis:string;rounding_method:string;
  enrollment_method:string|null;product_detail_url:string|null;unknown_fields:string[];cross_check_notes:string[];
  calculation_status:string;calculation_reason_codes:string[];calculation_reasons:string[];freshness:string;user_eligibility:string;
}
export interface ProductCatalog {dataset_version:string;evaluated_on:string;sources:OfficialSource[];products:OfficialProduct[];information_count:number;compatible_count:number;disclaimer:string;review_after_days:number;review_policy:string}
export interface ProductComparisonInput {profile:SimulationInput;after_profile?:SimulationInput;monthly_payment:number;term_months:number;product_ids:string[]}
export interface ProductComparison {
  dataset_version:string;evaluated_on:string;monthly_payment:number;term_months:number;information_count:number;calculated_count:number;
  results:{product_id:string;product:OfficialProduct;calculation_supported:boolean;selected_base_rate_percent:string|null;selected_max_total_rate_percent:string|null;reason_codes:string[];reasons:string[];
    calculation:Pick<SavingsResult,'total_principal_krw'|'estimated_interest_before_tax_krw'|'estimated_maturity_before_tax_krw'>|null}[];
  budget:SavingsResult['budget_comparison'];after_budget:SavingsResult['budget_comparison']|null;sources:OfficialSource[];
  comparison_note:string;disclaimer:string;direct_maturity_comparison_supported:boolean;ranking:null;
}
export class ProductApiError extends Error {
  kind:'validation'|'server';
  constructor(kind:'validation'|'server'){super(kind==='validation'?'상품 선택과 월 납입액·기간을 확인해 주세요.':'공식 상품 자료를 불러오지 못했습니다. 잠시 뒤 다시 시도해 주세요.');this.kind=kind;}
}
async function read<T>(response:Response):Promise<T>{
  if(!response.ok)throw new ProductApiError(response.status===422?'validation':'server');
  try{return await response.json();}catch{throw new ProductApiError('server');}
}
export async function getProducts(signal?:AbortSignal,base=''):Promise<ProductCatalog>{
  return read(await fetch(`${base}/api/financial-products`,{signal,cache:'no-store'}));
}
export async function compareProducts(input:ProductComparisonInput,signal?:AbortSignal,base=''):Promise<ProductComparison>{
  return read(await fetch(`${base}/api/financial-products/compare`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(input),signal,cache:'no-store'}));
}
