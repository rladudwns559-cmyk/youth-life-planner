import prepared from './public-data/current-support-web.json';

// Shared, UI-free lookups over the prepared support table. Kept apart from RegionalPrograms
// so pages that only need status or location (the home deadlines) do not depend on that screen.
export type SupportProgram=typeof prepared.programs[number];
export type RegionStatus='PASS'|'FAIL'|'UNKNOWN';
export type Intake='VERIFIED_OPEN'|'WINDOW_GUIDANCE'|'CONTINUOUS_GUIDANCE'|'UPCOMING'|'CLOSED'|'NO_INTAKE'|'UNKNOWN'|'REVIEW_REQUIRED';
export const intakeLabels:Record<Intake,string>={VERIFIED_OPEN:'공식 접수중 확인 · 잔여 확인',WINDOW_GUIDANCE:'공고상 신청기간 · 잔여 확인',CONTINUOUS_GUIDANCE:'상시 제도 안내 · 접수 확인',UPCOMING:'공고상 모집 예정',CLOSED:'확인한 회차 마감',NO_INTAKE:'신규모집 미운영',UNKNOWN:'현재 접수 추가 확인',REVIEW_REQUIRED:'최신 공고 재확인'};
const tables=prepared as unknown as {regions:Record<string,RegionStatus[]>;calendar:Record<string,number>;schedule_pool:Intake[][]};
export const programIndex=new Map(prepared.programs.map((p,i)=>[p.program_id,i]));
export function koreaToday(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
export function readRegionalDecision(id:string,regionKey:string,asOf=koreaToday()){
 const i=programIndex.get(id)??-1;
 return {region:i<0?'UNKNOWN' as RegionStatus:tables.regions[regionKey]?.[i]??'UNKNOWN',intake:i<0?'REVIEW_REQUIRED' as Intake:tables.schedule_pool[tables.calendar[asOf]]?.[i]??'REVIEW_REQUIRED',overall:'UNKNOWN' as const};
}
export function locationText(p:SupportProgram){return p.provinces.length?(p.provinces.join('·')+(p.city?' '+p.city:'')):'전국';}
