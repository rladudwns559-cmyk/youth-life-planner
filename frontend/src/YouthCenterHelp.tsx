import {Fragment,useState} from 'react';
import data from './public-data/youth-centers.json';
import apiData from './public-data/youth-centers-api.json';
import directory from './public-data/nationwide-districts.json';
import './youth-center-help.css';

export type YouthCenter=typeof data.centers[number];
/** One center from the daily 온통청년 Open API list (tools/youthcenter_fetch.py). */
export type ApiCenter={id:string;province:string;city:string;district_label:string;name:string;address:string;phone:string|null;url:string|null};
export type ApiCenterList={fetched_on:string|null;source:{title:string;institution:string;attribution:string;url:string};total:number;centers:ApiCenter[]};

const api=apiData as unknown as ApiCenterList;
const parents=directory.parent as Record<string,string>;
const parentOf=(province:string,city:string)=>parents[province+'|'+city]??city;

/** Centers verified for the selected area. A district (일반구) falls back to its city. */
export function centersFor(province:string,city:string):YouthCenter[]{
  if(!province||!city||city==='__OTHER__')return [];
  const parent=parentOf(province,city);
  return data.centers.filter(c=>c.province===province&&(c.city===city||c.city===parent));
}

const digits=(s:string|null)=>(s??'').replace(/\D/g,'');
const squash=(s:string)=>s.replace(/\s+/g,'');

/**
 * Centers from the 온통청년 list for the selected area, leaving out ones already shown from
 * the hand-verified list. A ward and its city see each other's centers. 세종 has no districts,
 * so the whole province is the area there.
 */
export function apiCentersFor(province:string,city:string,list:ApiCenterList=api):ApiCenter[]{
  if(!province||city==='__OTHER__')return [];
  const cities=(directory.cities as Record<string,string[]>)[province]??[];
  if(!city&&cities.length>0)return [];
  const verified=centersFor(province,city);
  const known=(c:ApiCenter)=>verified.some(v=>(c.phone&&digits(v.phone)===digits(c.phone))||squash(v.name)===squash(c.name));
  const parent=parentOf(province,city);
  return list.centers.filter(c=>c.province===province&&(cities.length===0||c.city===city||c.city===parent||(c.city!==''&&parentOf(province,c.city)===city))&&!known(c));
}

const tel=(phone:string)=>'tel:'+phone.replace(/[^\d+]/g,'');
const SHOWN=6;

function ApiCenters({centers,list}:{centers:ApiCenter[];list:ApiCenterList}){
  const [all,setAll]=useState(false);
  const shown=all?centers:centers.slice(0,SHOWN);
  return <div className="center-help-api">
    <ul className="center-help-list">{shown.map(c=><li key={c.id}>
      <strong>{c.name}</strong>
      <dl>
        <div><dt>전화</dt><dd>{c.phone?<a href={tel(c.phone)} aria-label={c.name+' 전화 '+c.phone}>{c.phone}</a>:'자료에 없음'}</dd></div>
        <div><dt>주소</dt><dd>{c.address||'자료에 없음'}</dd></div>
      </dl>
      {c.url&&<a href={c.url} target="_blank" rel="noopener noreferrer" aria-label={c.name+' 누리집'}>센터 누리집 ↗</a>}
    </li>)}</ul>
    {centers.length>SHOWN&&<button type="button" className="center-help-more" aria-expanded={all} onClick={()=>setAll(v=>!v)}>{all?'접기':`${centers.length-SHOWN}곳 더 보기`}</button>}
    <small className="center-help-source">{list.source.attribution} · <a href={list.source.url} target="_blank" rel="noopener noreferrer">{list.source.title}</a>{list.fetched_on&&<> · {list.fetched_on} 수집</>}. 운영 시간과 상담 예약은 방문 전에 전화로 확인하세요.</small>
  </div>;
}

export default function YouthCenterHelp({province,city,list=api}:{province:string;city:string;list?:ApiCenterList}){
  const centers=centersFor(province,city);
  const more=apiCentersFor(province,city,list);
  const any=centers.length+more.length>0;
  const cities=(directory.cities as Record<string,string[]>)[province]??[];
  const needCity=!!province&&!city&&cities.length>0&&list.centers.length>0;
  const n=data.national;
  return <aside className="center-help" aria-label="청년센터 상담 안내">
    <h3>조건이 헷갈리면 청년센터에 물어보세요</h3>
    <p className="center-help-lead">소득·거주기간처럼 이 화면에서 확인하지 못한 조건은 청년센터에서 내 상황에 맞춰 물어볼 수 있어요.</p>
    {centers.length>0&&<ul className="center-help-list">{centers.map(c=><li key={c.id}>
      <strong>{c.name}</strong>
      <dl>
        <div><dt>전화</dt><dd><a href={tel(c.phone)} aria-label={c.name+' 전화 '+c.phone}>{c.phone}</a></dd></div>
        <div><dt>주소</dt><dd>{c.address}</dd></div>
        <div><dt>방문 시간</dt><dd>{c.hours}</dd></div>
        {c.services&&<div><dt>하는 일</dt><dd>{c.services}</dd></div>}
      </dl>
      <a href={c.url} target="_blank" rel="noopener noreferrer" aria-label={c.name+' 누리집'}>센터 누리집 ↗</a>
      <small>출처 {c.sources.map((s,i)=><Fragment key={i}>{i>0&&' · '}<a href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a></Fragment>)} · 확인 {c.sources.map(s=>s.verified_on).sort()[0]}. 운영 시간과 상담 예약은 방문 전에 전화로 확인하세요.</small>
    </li>)}</ul>}
    {more.length>0&&<ApiCenters key={province+'|'+city} centers={more} list={list}/>}
    {needCity&&<p className="center-help-hint">시·군·구를 고르면 그 지역 청년센터를 보여드려요.</p>}
    <div className="center-help-national">
      <p>{any?'다른 지역의 청년센터는':province&&city?'이 지역 청년센터 정보가 아직 없어요. 전국 청년센터는':'전국 청년센터는'} 온통청년에서 지역을 골라 찾을 수 있어요.</p>
      <a href={n.url} target="_blank" rel="noopener noreferrer">{n.name} ↗</a>
      <span>온통청년 전화상담 <a href={tel(n.phone)}>{n.phone}</a> · {n.phone_hours}</span>
    </div>
  </aside>;
}
