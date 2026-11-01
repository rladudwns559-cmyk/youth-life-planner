import {publicBackendPending} from './portal-routing';
import type {SimulationInput} from './api';
export type IntakeStatus='OPEN'|'UPCOMING'|'CLOSED'|'NO_INTAKE'|'UNKNOWN'|'REVIEW_REQUIRED';
export type Bucket='CATALOG'|'CURRENT_CANDIDATE'|'WATCHLIST'|'BUDGET_SHORTFALL'|'NOT_MATCHED';
export interface AssetFacts {province:string|null;birth_date:string|null;owns_home:boolean|null;}
export interface AssetCheck {key:string;label:string;status:'PASS'|'FAIL'|'UNKNOWN';note:string;}
export interface AssetProgram {
  program_id:string;edition:string;title:string;authority:string;category:string;regions:string[];source_ids:string[];
  contribution_note:string;benefit_summary:string;income_note:string;age_note:string;term_months:number[];
  monthly_minimum:number|null;monthly_maximum:number|null;data_status:'DRAFT';coverage:'CONDITION_SLICE';
}
export interface AssetRow {
  program:AssetProgram;sources:{source_id:string;url:string;title:string;published_on:string|null;verified_on:string;locator:string}[];
  intake:{status:IntakeStatus;label:string;fresh:boolean;phase:string|null;application:{starts_at:string;ends_at_exclusive:string;time_note:string}|null;note:string};
  notification_key:string;revision:string;calculation:null;benefit_applied_krw:0;bucket:Bucket;reasons:string[];
  assessment:null|{status:'FAIL'|'UNKNOWN';display_status:string;checks:AssetCheck[];remaining_checks:AssetCheck[];budget:AssetCheck;allocation_krw:number|null;unallocated_capacity_krw:number|null;goal_matches:boolean|null;income_note:string};
}
export interface AssetResponse {
  schema_version:'asset-discovery-response-v1';dataset_version:string;evaluated_at:string;review_after_days:number;source_mode:'VERIFIED_SNAPSHOT';
  program_count:number;counts:Record<IntakeStatus,number>;recommendation_counts:Record<Bucket,number>;personalized:boolean;province:string|null;monthly_capacity:number|null;
  programs:AssetRow[];input_notes:string[];policy_benefit_applied_krw:0;actual_product_calculation_count:0;
  notifications:{change_contract:'asset-program-events-v1';delivery_enabled:boolean;subscriptions_stored:boolean};disclaimer:string;after?:AssetResponse|null;
}
const statuses=['OPEN','UPCOMING','CLOSED','NO_INTAKE','UNKNOWN','REVIEW_REQUIRED'];
function valid(value:unknown):value is AssetResponse {
  if(!value||typeof value!=='object')return false;
  const d=value as AssetResponse;
  return d.schema_version==='asset-discovery-response-v1'&&d.source_mode==='VERIFIED_SNAPSHOT'
    &&Array.isArray(d.programs)&&d.program_count===d.programs.length&&typeof d.personalized==='boolean'
    &&d.programs.every(r=>r&&r.program&&typeof r.program.program_id==='string'&&typeof r.program.title==='string'
      &&r.program.coverage==='CONDITION_SLICE'&&r.intake&&statuses.includes(r.intake.status)&&r.calculation===null&&r.benefit_applied_krw===0
      &&Array.isArray(r.sources)&&r.sources.length>0&&r.sources.every(s=>typeof s.url==='string'&&s.url.startsWith('https://'))
      &&Array.isArray(r.reasons)&&(r.assessment===null||(['FAIL','UNKNOWN'].includes(r.assessment.status)&&Array.isArray(r.assessment.checks)&&Array.isArray(r.assessment.remaining_checks))))
    &&d.policy_benefit_applied_krw===0&&d.actual_product_calculation_count===0&&Array.isArray(d.input_notes)
    &&typeof d.notifications?.delivery_enabled==='boolean'&&typeof d.notifications?.subscriptions_stored==='boolean'&&typeof d.disclaimer==='string';
}
export async function getAssetPrograms(profile:SimulationInput|null,after:SimulationInput|null,facts:AssetFacts,goal:number|null,signal:AbortSignal):Promise<AssetResponse>{
  const response=await fetch(publicBackendPending?'/asset-programs-public.json':profile?'/api/asset-programs/recommendations':'/api/asset-programs',{
    method:profile?'POST':'GET',cache:'no-store',signal,
    ...(profile?{headers:{'Content-Type':'application/json'},body:JSON.stringify({profile,...(after?{after_profile:after}:{}),supplement:facts,goal_months:goal})}:{}),
  });
  if(!response.ok)throw new Error(response.status===422?'추가 입력의 날짜와 지역을 확인해 주세요.':'공식 지원사업 자료를 불러오지 못했습니다. 다시 시도해 주세요.');
  const data:unknown=await response.json();
  if(!valid(data)||data.personalized!==(profile!==null)||(after!==null)!==(data.after!=null)||(data.after!=null&&!valid(data.after)))throw new Error('지원사업 응답 형식을 확인하지 못했습니다.');
  return data;
}
