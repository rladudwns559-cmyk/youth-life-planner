import {Fragment} from 'react';
import data from './public-data/youth-centers.json';
import directory from './public-data/nationwide-districts.json';
import './youth-center-help.css';

export type YouthCenter=typeof data.centers[number];

/** Centers verified for the selected area. A district (일반구) falls back to its city. */
export function centersFor(province:string,city:string):YouthCenter[]{
  if(!province||!city||city==='__OTHER__')return [];
  const parent=(directory.parent as Record<string,string>)[province+'|'+city]??city;
  return data.centers.filter(c=>c.province===province&&(c.city===city||c.city===parent));
}

const tel=(phone:string)=>'tel:'+phone.replace(/[^\d+]/g,'');

export default function YouthCenterHelp({province,city}:{province:string;city:string}){
  const centers=centersFor(province,city);
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
    <div className="center-help-national">
      <p>{centers.length>0?'다른 지역의 청년센터는':province?'이 지역 청년센터는 아직 직접 확인한 자료가 없어요. 전국 청년센터는':'전국 청년센터는'} 온통청년에서 지역을 골라 찾을 수 있어요.</p>
      <a href={n.url} target="_blank" rel="noopener noreferrer">{n.name} ↗</a>
      <span>온통청년 전화상담 <a href={tel(n.phone)}>{n.phone}</a> · {n.phone_hours}</span>
    </div>
  </aside>;
}
