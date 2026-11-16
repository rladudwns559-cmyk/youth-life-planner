import {useEffect,useState} from 'react';
import type {OntongPolicyList} from './ontong-policies';

let cached:Promise<OntongPolicyList>|null=null;
/** The policy list is large, so it is its own file, fetched once and only when a screen needs it. */
export function loadPolicyList():Promise<OntongPolicyList>{
  cached??=import('./public-data/youth-policies.json').then(m=>m.default as unknown as OntongPolicyList).catch(e=>{cached=null;throw e;});
  return cached;
}

export function usePolicyList(given?:OntongPolicyList,enabled=true){
  const [list,setList]=useState<OntongPolicyList|null>(given??null);
  const [failed,setFailed]=useState(false);
  useEffect(()=>{
    if(given){setList(given);return;}
    if(!enabled)return;
    let live=true;
    loadPolicyList().then(l=>{if(live)setList(l);}).catch(()=>{if(live)setFailed(true);});
    return()=>{live=false;};
  },[given,enabled]);
  return {list,failed};
}
