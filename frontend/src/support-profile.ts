// Opt-in memory of the support finder conditions, kept only in this browser.
// Stores region, age and two choices; never income, address or anything typed freely.
import prepared from './public-data/current-support-web.json';

export const PROFILE_KEY='aix_support_profile_v1';
export type SavedProfile={province:string;city:string;age:string;employment:string;rent:string};

const EMPLOYMENT=new Set(['unknown','employed','unemployed','self_employed']);
const RENT=new Set(['unknown','yes','no']);
const PROVINCES=new Set(prepared.provinces as string[]);

/** Returns the saved conditions, or null when nothing valid is stored or storage is blocked. */
export function readProfile():SavedProfile|null{
  try{
    const raw=localStorage.getItem(PROFILE_KEY);if(!raw||raw.length>1000)return null;
    const v=JSON.parse(raw);if(!v||typeof v!=='object')return null;
    const province=typeof v.province==='string'&&(v.province===''||PROVINCES.has(v.province))?v.province:'';
    const city=typeof v.city==='string'&&v.city.length<=40&&province?v.city:'';
    const age=typeof v.age==='string'&&/^(\d{1,3})?$/.test(v.age)&&(v.age===''||Number(v.age)<=120)?v.age:'';
    const employment=EMPLOYMENT.has(v.employment)?v.employment:'unknown';
    const rent=RENT.has(v.rent)?v.rent:'unknown';
    return {province,city,age,employment,rent};
  }catch{return null;}
}

/** true when saved; false when the browser refused. */
export function writeProfile(p:SavedProfile):boolean{
  try{localStorage.setItem(PROFILE_KEY,JSON.stringify({province:p.province,city:p.city,age:p.age,employment:p.employment,rent:p.rent}));return true;}catch{return false;}
}

export function clearProfile(){try{localStorage.removeItem(PROFILE_KEY);}catch{/* nothing stored */}}
