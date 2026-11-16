import directory from './public-data/nationwide-districts.json';

/** One policy from the daily 온통청년 Open API list (tools/youthcenter_policy_fetch.py). */
export type OntongPolicy={
  id:string; title:string; category:string; subcategory:string; org:string; summary:string;
  regions:string[]; age:[number|null,number|null]|null; jobs:{groups:string[];other:boolean}|null;
  income:string|null; extra:string|null;
  apply:{mode:'ALWAYS'|'OTHER'}|{mode:'PERIOD';start:string;end:string};
  url:string; apply_url:string|null; updated:string|null;
};
export type OntongPolicyList={fetched_on:string|null;source:{title:string;institution:string;attribution:string;url:string};total:number;policies:OntongPolicy[]};
export type Fit='PASS'|'FAIL'|'UNKNOWN';
export type OntongProfile={province:string;city:string;age:string;employment:string};

const parents=directory.parent as Record<string,string>;
const parentOf=(province:string,city:string)=>parents[province+'|'+city]??city;

/** PASS when the policy covers the chosen area, UNKNOWN when only part of it or no city was chosen. */
export function regionFit(p:OntongPolicy,province:string,city:string):Fit{
  if(p.regions.includes('*'))return 'PASS';
  if(!province)return 'FAIL';
  if(p.regions.includes(province))return 'PASS';
  const local=p.regions.filter(r=>r.startsWith(province+'|')).map(r=>r.slice(province.length+1));
  if(!local.length)return 'FAIL';
  if(!city||city==='__OTHER__')return 'UNKNOWN';
  const parent=parentOf(province,city);
  if(local.includes(city)||local.includes(parent))return 'PASS';
  // A city chosen whose wards are listed one by one: part of the city is covered.
  if(local.some(c=>parentOf(province,c)===city))return 'UNKNOWN';
  return 'FAIL';
}

export function ageFit(p:OntongPolicy,age:string):Fit{
  if(!p.age)return 'PASS';
  if(age.trim()==='')return 'UNKNOWN';
  const n=Number(age);const [low,high]=p.age;
  return (low!==null&&n<low)||(high!==null&&n>high)?'FAIL':'PASS';
}

export function jobFit(p:OntongPolicy,employment:string):Fit{
  if(!p.jobs)return 'PASS';
  if(!employment||employment==='unknown')return 'UNKNOWN';
  if(p.jobs.groups.includes(employment))return 'PASS';
  return p.jobs.other?'UNKNOWN':'FAIL';
}

/** The five 온통청년 fields; old names and repeated values in the data are folded together. */
export const POLICY_GROUPS=['일자리','주거','교육','복지·문화','참여'] as const;
export type PolicyGroup=typeof POLICY_GROUPS[number];
const groupOf=(name:string):PolicyGroup|null=>name.startsWith('일자리')?'일자리':name.startsWith('주거')?'주거':name.startsWith('교육')?'교육':/복지|문화|금융/.test(name)?'복지·문화':name.startsWith('참여')?'참여':null;
const parts=(s:string)=>[...new Set(s.split(',').map(x=>x.replace('…','').trim()).filter(Boolean))];
export function policyGroups(p:Pick<OntongPolicy,'category'>):PolicyGroup[]{
  const names=parts(p.category);
  return POLICY_GROUPS.filter(g=>names.some(n=>groupOf(n)===g));
}
export const categoryText=(p:Pick<OntongPolicy,'category'|'subcategory'>)=>[parts(p.category).join(' · '),parts(p.subcategory).join(' · ')].filter(Boolean).join(' · ');
export const SOON_DAYS=14;
export const closesSoon=(p:OntongPolicy,asOf:string)=>p.apply.mode==='PERIOD'&&p.apply.end>=asOf&&Math.round((Date.parse(p.apply.end+'T00:00:00Z')-Date.parse(asOf+'T00:00:00Z'))/86_400_000)<=SOON_DAYS;

export const ageText=(p:OntongPolicy)=>!p.age?'나이 제한 없음':p.age[0]!==null&&p.age[1]!==null?`만 ${p.age[0]}~${p.age[1]}세`:p.age[0]!==null?`만 ${p.age[0]}세 이상`:`만 ${p.age[1]}세 이하`;
const jobWords:Record<string,string>={employed:'근로 중',unemployed:'일하지 않음',self_employed:'자영업·프리랜서·창업'};
export const jobText=(p:OntongPolicy)=>!p.jobs?'취업 상태 제한 없음':[...p.jobs.groups.map(g=>jobWords[g]??g),...(p.jobs.other?['기타']:[])].join(' · ');
/** Where the policy applies, naming the chosen province first when it is one of them. */
export function regionText(p:OntongPolicy,province=''){
  if(p.regions.includes('*'))return '전국';
  const mine=province?p.regions.find(r=>r===province||r.startsWith(province+'|')):undefined;
  const first=(mine??p.regions[0]).replace('|',' ');
  return p.regions.length>1?`${first} 외 ${p.regions.length-1}곳`:first;
}

const squash=(s:string)=>s.replace(/\d{4}\s*년도?|\(.*?\)|[\s·ㆍ・･「」『』<>《》"'“”‘’\-_.,:]/g,'');
/** True when a title looks like one of our hand-checked programs, so it is not listed twice. */
export function looksKnown(title:string,known:string[]){
  const t=squash(title);
  if(t.length<4)return false;
  return known.some(k=>{const s=squash(k);return s===t||(Math.min(s.length,t.length)>=8&&(s.includes(t)||t.includes(s)));});
}

export type RankedPolicy={p:OntongPolicy;region:Fit;age:Fit;job:Fit};
const specificity=(p:OntongPolicy,province:string)=>p.regions.includes('*')?2:p.regions.includes(province)?1:0;
const endOf=(p:OntongPolicy)=>p.apply.mode==='PERIOD'?p.apply.end:p.apply.mode==='ALWAYS'?'9999-12-30':'9999-12-31';

/** Open policies in the chosen area (or nationwide), with how each condition compares. */
function inArea(list:OntongPolicy[],profile:OntongProfile,asOf:string,known:string[],query:string):RankedPolicy[]{
  const q=query.trim().toLowerCase();
  return list
    .filter(p=>p.apply.mode!=='PERIOD'||p.apply.end>=asOf)
    .filter(p=>!q||(p.title+' '+p.summary+' '+p.subcategory).toLowerCase().includes(q))
    .map(p=>({p,region:regionFit(p,profile.province,profile.city),age:ageFit(p,profile.age),job:jobFit(p,profile.employment)}))
    .filter(r=>r.region!=='FAIL'&&!looksKnown(r.p.title,known));
}
const order=(province:string)=>(a:RankedPolicy,b:RankedPolicy)=>specificity(a.p,province)-specificity(b.p,province)||endOf(a.p).localeCompare(endOf(b.p))||a.p.title.localeCompare(b.p.title,'ko');

/** Policies that do not clash with the chosen conditions: local first, then by closing date. */
export function rankPolicies(list:OntongPolicy[],profile:OntongProfile,asOf:string,known:string[]=[],query=''):RankedPolicy[]{
  return inArea(list,profile,asOf,known,query).filter(r=>r.age!=='FAIL'&&r.job!=='FAIL').sort(order(profile.province));
}

const jobNames:Record<string,string>={employed:'근로 중',unemployed:'현재 일하지 않음',self_employed:'자영업·프리랜서'};
/** Why a policy in the area was left out, in plain words. */
export function gapText(r:RankedPolicy,profile:OntongProfile):string[]{
  const out:string[]=[];
  if(r.age==='FAIL')out.push(`${ageText(r.p)} 대상 · 지금 만 ${profile.age}세`);
  if(r.job==='FAIL')out.push(`${jobText(r.p)} 대상 · 지금 ${jobNames[profile.employment]??profile.employment}`);
  return out;
}

export type Opening={key:string;label:string;policies:OntongPolicy[]};
/**
 * Policies in the area left out only because of age or employment, and the ones that would
 * open with a different employment status or when the person gets older (a younger age limit
 * never reopens, so only policies the person is too young for are counted for age).
 */
export function leftOut(list:OntongPolicy[],profile:OntongProfile,asOf:string,known:string[]=[],query=''){
  const area=inArea(list,profile,asOf,known,query);
  const excluded=area.filter(r=>r.age==='FAIL'||r.job==='FAIL').sort(order(profile.province));
  const openings:Opening[]=[];
  for(const e of ['employed','unemployed','self_employed']){
    if(e===profile.employment||profile.employment==='unknown'||!profile.employment)continue;
    const opened=excluded.filter(r=>r.job==='FAIL'&&r.age!=='FAIL'&&jobFit(r.p,e)!=='FAIL').map(r=>r.p);
    if(opened.length)openings.push({key:'job-'+e,label:`${jobNames[e]}이면`,policies:opened});
  }
  if(profile.age.trim()!==''){
    const now=Number(profile.age);
    for(const later of [1,2,3]){
      // Opens in exactly this year: the lower age limit is reached now+later.
      const opened=excluded.filter(r=>r.age==='FAIL'&&r.job!=='FAIL'&&r.p.age?.[0]===now+later).map(r=>r.p);
      if(opened.length)openings.push({key:'age-'+later,label:`${later}년 뒤 만 ${now+later}세가 되면`,policies:opened});
    }
  }
  return {excluded,openings};
}
