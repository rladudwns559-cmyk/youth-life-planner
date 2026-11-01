import {useEffect,useLayoutEffect,useRef,useState} from 'react';
export type PortalRoute='home'|'budget'|'catalog'|'programs'|'savings'|'alerts'|'guide';
const known=new Set<PortalRoute>(['home','budget','catalog','programs','savings','alerts','guide']);
const legacy:Record<string,PortalRoute>={'programs/list':'catalog',main:'home','input-heading':'budget','result-heading':'budget','saving-period':'budget','asset-programs':'programs','asset-alerts':'alerts','service-guide':'guide'};
export function resolveRoute(hash:string):PortalRoute {const key=hash.replace(/^#\/?/,'').split('?')[0];const next=known.has(key as PortalRoute)?key as PortalRoute:legacy[key]??'home';return next==='alerts'?'guide':publicBackendPending&&next==='budget'?'savings':next;}
export const routeLinks:Record<PortalRoute,string>={home:'#/',budget:'#/budget',programs:'#/programs',catalog:'#/programs/list',savings:'#/savings',alerts:'#/alerts',guide:'#/guide'};
export const publicBackendPending=import.meta.env.VITE_PUBLIC_BACKEND_PENDING==='true';
export function usePortalRoute(){
  const [route,setRoute]=useState<PortalRoute>(()=>resolveRoute(window.location.hash));
  const [visited,setVisited]=useState<Set<PortalRoute>>(()=>new Set([resolveRoute(window.location.hash)]));
  const modality=useRef<'pointer'|'keyboard'>('pointer');
  useEffect(()=>{
    const update=()=>{if(/^#portal-[a-z]+-title$/.test(window.location.hash))return;const next=resolveRoute(window.location.hash);setVisited(old=>new Set([...old,next]));setRoute(next);};
    const pointer=()=>{modality.current='pointer';};const keyboard=()=>{modality.current='keyboard';};
    window.addEventListener('hashchange',update);window.addEventListener('pointerdown',pointer);window.addEventListener('keydown',keyboard);
    return()=>{window.removeEventListener('hashchange',update);window.removeEventListener('pointerdown',pointer);window.removeEventListener('keydown',keyboard);};
  },[]);
  return {route,visited,modality};
}
export function usePageTransition(route:PortalRoute,modality:React.RefObject<'pointer'|'keyboard'>){
  const ref=useRef<HTMLDivElement>(null);
  useLayoutEffect(()=>{
    const node=ref.current?.querySelector<HTMLElement>('[data-portal-page]:not([hidden])');if(!node)return;
    const heading=node.querySelector<HTMLElement>('[data-page-heading]');heading?.focus();
    // Pointer route entries bridge content changes; keyboard navigation remains instant.
    if(modality.current==='keyboard'||typeof node.animate!=='function')return;
    const reduced=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const animation=node.animate(reduced?[{opacity:.7},{opacity:1}]:[{opacity:.25,transform:'translateY(10px)'},{opacity:1,transform:'translateY(0)'}],{duration:reduced?150:220,easing:'cubic-bezier(0.23, 1, 0.32, 1)'});
    return()=>animation.cancel();
  },[route,modality]);
  return ref;
}
