import directory from './public-data/nationwide-districts.json';
import {policyGroups,POLICY_GROUPS,type OntongPolicy,type PolicyGroup} from './ontong-policies';

/**
 * Counts for the "지역별 청년정책" page, from the open 온통청년 policies.
 * A nationwide policy counts once in "전국 대상"; a regional one counts in every province it
 * names (so provinces do not add up to the regional total). No population weighting.
 */
const cities=directory.cities as Record<string,string[]>;
const parents=directory.parent as Record<string,string>;
export const PROVINCES=Object.keys(cities);
const emptyGroups=()=>Object.fromEntries(POLICY_GROUPS.map(g=>[g,0])) as Record<PolicyGroup,number>;

export type ProvinceStat={province:string;count:number;byGroup:Record<PolicyGroup,number>};
export type RegionStats={
  total:number; national:number; regional:number;
  nationalByGroup:Record<PolicyGroup,number>;
  provinces:ProvinceStat[]; average:number; averageByGroup:Record<PolicyGroup,number>;
};

const isOpen=(p:OntongPolicy,asOf:string)=>p.apply.mode!=='PERIOD'||p.apply.end>=asOf;

export function regionStats(list:OntongPolicy[],asOf:string):RegionStats{
  const open=list.filter(p=>isOpen(p,asOf));
  const stats=new Map(PROVINCES.map(p=>[p,{province:p,count:0,byGroup:emptyGroups()}]));
  const nationalByGroup=emptyGroups();
  let national=0;
  for(const p of open){
    const groups=policyGroups(p);
    if(p.regions.includes('*')){national++;for(const g of groups)nationalByGroup[g]++;continue;}
    for(const province of new Set(p.regions.map(r=>r.split('|')[0]))){
      const s=stats.get(province);if(!s)continue;
      s.count++;for(const g of groups)s.byGroup[g]++;
    }
  }
  const provinces=[...stats.values()];
  const average=provinces.reduce((a,s)=>a+s.count,0)/provinces.length;
  const averageByGroup=emptyGroups();
  for(const g of POLICY_GROUPS)averageByGroup[g]=provinces.reduce((a,s)=>a+s.byGroup[g],0)/provinces.length;
  return {total:open.length,national,regional:open.length-national,nationalByGroup,provinces,average,averageByGroup};
}

/** Policies naming each district of one province (a ward also counts for its city). Province-wide ones are left out. */
export function cityCounts(list:OntongPolicy[],province:string,asOf:string):{city:string;count:number}[]{
  const counts=new Map<string,number>();
  for(const p of list){
    if(!isOpen(p,asOf)||p.regions.includes('*')||p.regions.includes(province))continue;
    const named=new Set(p.regions.filter(r=>r.startsWith(province+'|')).map(r=>{const c=r.slice(province.length+1);return parents[province+'|'+c]??c;}));
    for(const c of named)counts.set(c,(counts.get(c)??0)+1);
  }
  return [...counts].map(([city,count])=>({city,count})).sort((a,b)=>b.count-a.count||a.city.localeCompare(b.city,'ko'));
}

/** "주거 정책은 17개 광역 평균보다 32% 적어요" style sentences, largest gaps first. */
export function comparisonNotes(s:ProvinceStat,avg:Record<PolicyGroup,number>):{group:PolicyGroup;diff:number;text:string}[]{
  return POLICY_GROUPS.filter(g=>avg[g]>0).map(g=>{
    const diff=Math.round((s.byGroup[g]-avg[g])/avg[g]*100);
    const text=diff===0?`${g} 정책은 평균과 같아요`:`${g} 정책은 평균보다 ${Math.abs(diff)}% ${diff>0?'많아요':'적어요'}`;
    return {group:g,diff,text};
  }).sort((a,b)=>Math.abs(b.diff)-Math.abs(a.diff));
}
