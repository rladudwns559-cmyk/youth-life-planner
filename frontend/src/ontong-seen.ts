import {useEffect,useState} from 'react';

/**
 * Which 온통청년 policies were already in the list on an earlier day, kept in this browser only
 * (policy numbers and dates, nothing about the person). "New" means not in the list on the last
 * earlier day this browser opened it, so reloading on the same day keeps the same new ones.
 * The first visit only records; nothing is called new until a later day.
 */
export const ONTONG_SEEN_KEY='aix_ontong_seen_v1';
type Snapshot={date:string;ids:string[]};
type Stored={baseline:Snapshot|null;current:Snapshot};

const isDay=(v:unknown):v is string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v);
function snap(v:unknown):Snapshot|null{
  if(!v||typeof v!=='object')return null;
  const s=v as {date?:unknown;ids?:unknown};
  if(!isDay(s.date)||!Array.isArray(s.ids))return null;
  return {date:s.date,ids:s.ids.filter((x):x is string=>typeof x==='string'&&x.length<=40).slice(0,20000)};
}
export function readSeen():Stored|null{
  try{const raw=localStorage.getItem(ONTONG_SEEN_KEY);if(!raw||raw.length>2_000_000)return null;const v=JSON.parse(raw);const current=snap(v?.current);return current?{baseline:snap(v.baseline),current}:null;}catch{return null;}
}

/** Rolls the record forward when the day changes and returns what counts as new today. */
export function visit(ids:string[],today:string,prev:Stored|null):{next:Stored;baseline:Snapshot|null}{
  if(!prev)return {next:{baseline:null,current:{date:today,ids}},baseline:null};
  if(prev.current.date<today)return {next:{baseline:prev.current,current:{date:today,ids}},baseline:prev.current};
  // Same day: keep the baseline, and remember ids added later today so tomorrow compares fairly.
  const merged=[...new Set([...prev.current.ids,...ids])];
  return {next:{baseline:prev.baseline,current:{date:prev.current.date,ids:merged}},baseline:prev.baseline};
}

export function useSeenPolicies(ids:string[]|null,today:string){
  const [state,setState]=useState<{since:string|null;fresh:Set<string>}>({since:null,fresh:new Set()});
  const key=ids?ids.length+':'+(ids[0]??'')+':'+(ids[ids.length-1]??''):'';
  useEffect(()=>{
    if(!ids){setState({since:null,fresh:new Set()});return;}
    const {next,baseline}=visit(ids,today,readSeen());
    try{localStorage.setItem(ONTONG_SEEN_KEY,JSON.stringify(next));}catch{/* private mode: show nothing new */}
    if(!baseline){setState({since:null,fresh:new Set()});return;}
    const old=new Set(baseline.ids);
    setState({since:baseline.date,fresh:new Set(ids.filter(id=>!old.has(id)))});
  },[key,today]); // eslint-disable-line react-hooks/exhaustive-deps
  return state;
}

export function forgetSeen(){try{localStorage.removeItem(ONTONG_SEEN_KEY);}catch{/* nothing stored */}}
