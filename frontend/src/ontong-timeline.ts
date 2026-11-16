import {rankPolicies,SCHOOL_NAMES,type OntongPolicy,type OntongProfile} from './ontong-policies';

/**
 * How the 온통청년 list changes as the person gets older: each year ahead, which policies
 * open (a lower age limit is reached, or a university student moves on to 졸업 예정 and 졸업)
 * and which close (an upper age limit is passed). It uses today's postings, so it shows
 * the shape of the years ahead, not future announcements.
 */
export type Stage={key:string;years:number;age:number;school?:string;count:number;opened:OntongPolicy[];closed:OntongPolicy[];schoolChanged:boolean};

// University students are assumed to reach 졸업 예정 in a year and 졸업 the year after.
export function schoolAfter(school:string|undefined,years:number):string|undefined{
  if(school==='univ_student')return years>=2?'univ_grad':years===1?'univ_expected':school;
  if(school==='univ_expected')return years>=1?'univ_grad':school;
  return school;
}
export const assumesGraduation=(school?:string)=>school==='univ_student'||school==='univ_expected';

export function futureStages(list:OntongPolicy[],profile:OntongProfile,asOf:string,known:string[]=[],maxYears=20,maxAge=40):Stage[]|null{
  const now=Number(profile.age);
  if(profile.age.trim()===''||!Number.isFinite(now))return null;
  const fitting=(p:OntongProfile)=>rankPolicies(list,p,asOf,known);
  const first=fitting(profile);
  const stages:Stage[]=[{key:'now',years:0,age:now,school:profile.school,count:first.length,opened:[],closed:[],schoolChanged:false}];
  let prev=new Map(first.map(r=>[r.p.id,r.p]));
  let prevSchool=profile.school;
  for(let y=1;y<=maxYears&&now+y<=maxAge;y++){
    const school=schoolAfter(profile.school,y);
    const rows=fitting({...profile,age:String(now+y),school});
    const next=new Map(rows.map(r=>[r.p.id,r.p]));
    const opened=[...next.values()].filter(p=>!prev.has(p.id));
    const closed=[...prev.values()].filter(p=>!next.has(p.id));
    const schoolChanged=school!==prevSchool;
    if(opened.length||closed.length||schoolChanged)stages.push({key:'y'+y,years:y,age:now+y,school,count:rows.length,opened,closed,schoolChanged});
    prev=next;prevSchool=school;
  }
  return stages;
}

export const stageLabel=(s:Stage)=>[s.years===0?'지금':`${s.years}년 뒤`,`만 ${s.age}세`,s.schoolChanged&&s.school?SCHOOL_NAMES[s.school]:''].filter(Boolean).join(' · ');
