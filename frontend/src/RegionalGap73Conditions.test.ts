import {it,expect} from 'vitest';
import {readPersonalDecision} from './RegionalPrograms';
it.each(['employed','unemployed','self_employed'])('keeps historical employment and means tests unknown for %s',employment=>{
 for(const [id,regionKey] of [
 ['GAP73-JN-GANGJIN-RENT-Q4-2026','전남|강진군'],
 ['GAP73-JN-YEONGAM-EXAM-NOV-2026','전남|영암군'],
 ['GAP73-UJB-EXOTIC-2026','경기|의정부시'],
 ]){
  const d=readPersonalDecision(id,regionKey,{age:'25',employment,rent:'yes'},'2026-11-01');
  expect(d.employment).toBe('UNKNOWN');
  expect(d.summary.eligibility).toBe('UNKNOWN');expect(d.summary.benefit_applied_krw).toBe(0);
 }
});

