import {describe,expect,it} from 'vitest';
import snapshot from './public-data/asset-programs-public.json';
import {koreaDay,routePublicSnapshot} from './asset-programs-api';

type Snapshot=Parameters<typeof routePublicSnapshot>[0];
const data=snapshot as unknown as Snapshot;
const byId=(r:ReturnType<typeof routePublicSnapshot>,id:string)=>r.programs.find(p=>p.program.program_id===id)!;

describe('public policy-savings snapshot is routed by date, not computed in the browser',()=>{
  it('uses the precomputed row for a covered day, with every source read in the first week',()=>{
    const out=routePublicSnapshot(data,'2026-11-09');
    const future=byId(out,'KR-YOUTH-FUTURE');
    expect(future.intake).toMatchObject({status:'CLOSED',fresh:true,phase:'기신청자 심사'});
    expect(out.programs.every(r=>r.intake.fresh)).toBe(true);
    expect(out.program_count).toBe(10);
  });
  it('turns the continuously open housing account into "recheck required" once its sources are older than 7 days',()=>{
    expect(byId(routePublicSnapshot(data,'2026-11-15'),'KR-YOUTH-HOUSING').intake).toMatchObject({status:'OPEN',fresh:true});
    expect(byId(routePublicSnapshot(data,'2026-11-16'),'KR-YOUTH-HOUSING').intake).toMatchObject({status:'REVIEW_REQUIRED',fresh:false});
  });
  it('follows the official phases and drops freshness once the verification is older than 7 days',()=>{
    expect(byId(routePublicSnapshot(data,'2026-11-15'),'KR-YOUTH-FUTURE').intake.fresh).toBe(true);
    const opening=byId(routePublicSnapshot(data,'2026-11-16'),'KR-YOUTH-FUTURE').intake;
    expect(opening.phase).toBe('심사 통과자 계좌개설');
    expect(opening.fresh).toBe(false);
  });
  it('never shows an open/upcoming status as current when the day is outside the table',()=>{
    for(const day of ['2026-01-01','2030-01-01']){
      const out=routePublicSnapshot(data,day);
      expect(out.programs.every(r=>r.intake.fresh===false&&r.intake.phase===null)).toBe(true);
      expect(out.programs.some(r=>['OPEN','UPCOMING','UNKNOWN'].includes(r.intake.status))).toBe(false);
      expect(out.counts.OPEN+out.counts.UPCOMING+out.counts.UNKNOWN).toBe(0);
    }
  });
  it('keeps counts consistent with the displayed rows and adds no money or calculation',()=>{
    const out=routePublicSnapshot(data,'2026-11-09');
    expect(Object.values(out.counts).reduce((a,b)=>a+b,0)).toBe(out.programs.length);
    expect(out.policy_benefit_applied_krw).toBe(0);
    expect(out.actual_product_calculation_count).toBe(0);
    expect(out.programs.every(r=>r.calculation===null&&r.benefit_applied_krw===0)).toBe(true);
  });
  it('lists nationwide programs before regional ones and does not drop or duplicate any',()=>{
    const out=routePublicSnapshot(data,'2026-11-09');
    expect(out.programs[0].program.program_id).toBe('KR-YOUTH-FUTURE');
    const firstRegional=out.programs.findIndex(r=>r.program.regions.length>0);
    expect(out.programs.slice(0,firstRegional).every(r=>r.program.regions.length===0)).toBe(true);
    expect(out.programs.slice(firstRegional).every(r=>r.program.regions.length>0)).toBe(true);
    expect(new Set(out.programs.map(r=>r.program.program_id)).size).toBe(10);
  });
  it('formats the Korea calendar day',()=>{
    expect(koreaDay(new Date('2026-11-08T15:30:00Z'))).toBe('2026-11-09');
    expect(koreaDay(new Date('2026-11-08T14:59:00Z'))).toBe('2026-11-08');
  });
});
