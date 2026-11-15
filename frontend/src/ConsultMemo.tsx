import {useEffect,useRef,useState} from 'react';
import centers from './public-data/youth-centers.json';
import {centersFor} from './YouthCenterHelp';
import './consult-memo.css';

export type MemoItem={
  id:string; title:string; place:string; status:string; deadline:string|null;
  matches:{label:string;word:string}[]; gaps:{label:string;text:string}[];
  checks:{text:string;done:boolean}[]; url:string;
};
export type MemoProfile={region:string;age:string;employment:string;rent:string};

/** One printable page: my conditions, chosen programs with what is still unknown, and where to ask. */
export function ConsultMemoSheet({items,profile,province,city,asOf}:{items:MemoItem[];profile:MemoProfile;province:string;city:string;asOf:string}){
  const local=centersFor(province,city);
  return <article className="consult-memo" aria-label="상담 준비 메모">
    <header><h2>청년 지원사업 상담 준비 메모</h2><p>작성 {asOf} · 청년 경제생활 시뮬레이터</p></header>
    <section><h3>내 조건</h3><dl className="memo-profile">
      <div><dt>지역</dt><dd>{profile.region}</dd></div><div><dt>나이</dt><dd>{profile.age}</dd></div>
      <div><dt>취업 상태</dt><dd>{profile.employment}</dd></div><div><dt>주거</dt><dd>{profile.rent}</dd></div>
    </dl><p className="memo-note">소득·재산·거주기간은 이 서비스에서 확인하지 않았어요. 상담 때 함께 확인하세요.</p></section>
    <section><h3>알아볼 사업 {items.length}개</h3>
      <ol className="memo-programs">{items.map(it=><li key={it.id}>
        <h4>{it.title}</h4>
        <p className="memo-meta">{it.place} · {it.status}{it.deadline?' · '+it.deadline:''}</p>
        {it.matches.length>0&&<p className="memo-matches">{it.matches.map(m=>m.label+' '+m.word).join(' · ')}</p>}
        {it.gaps.length>0&&<ul className="memo-gaps">{it.gaps.map(g=><li key={g.label}><b>{g.label}</b> {g.text}</li>)}</ul>}
        <p className="memo-sub">물어볼 것·확인할 것</p>
        <ul className="memo-checks">{it.checks.map(c=><li key={c.text}><span aria-hidden="true">{c.done?'☑':'☐'}</span> {c.text}{c.done&&<span className="sr-only"> (확인함)</span>}</li>)}</ul>
        <p className="memo-url">공식 안내 {it.url}</p>
      </li>)}</ol>
    </section>
    <section><h3>물어볼 곳</h3><ul className="memo-centers">
      {local.map(c=><li key={c.id}><b>{c.name}</b> {c.phone} · {c.address} · {c.hours}</li>)}
      <li><b>온통청년 전화상담</b> {centers.national.phone} ({centers.national.phone_hours}) · 전국 청년센터 찾기 {centers.national.url}</li>
    </ul></section>
    <section className="memo-blank"><h3>상담 메모</h3><div aria-hidden="true"/><div aria-hidden="true"/><div aria-hidden="true"/></section>
    <footer>이 메모는 신청 자격을 확정하지 않습니다. 모집 상태·마감일은 {asOf} 기준 자료이며, 신청 전 공식 안내에서 다시 확인하세요.</footer>
  </article>;
}

export default function ConsultMemo({items,profile,province,city,asOf,source}:{items:MemoItem[];profile:MemoProfile;province:string;city:string;asOf:string;source:string}){
  const [open,setOpen]=useState(false);
  const ref=useRef<HTMLDialogElement>(null);
  useEffect(()=>{
    const d=ref.current;if(!d||!open)return;
    if(typeof d.showModal==='function'&&!d.open)d.showModal();else d.setAttribute('open','');
    const after=()=>document.body.classList.remove('printing-memo');
    window.addEventListener('afterprint',after);
    return()=>{window.removeEventListener('afterprint',after);after();if(typeof d.close==='function'&&d.open)d.close();};
  },[open]);
  function print(){document.body.classList.add('printing-memo');window.print();}
  return <div className="consult-memo-entry">
    <button type="button" className="consult-memo-open" disabled={!items.length} onClick={()=>setOpen(true)}>상담 준비 메모 만들기 ({items.length})</button>
    <small>{items.length?source+' 사업으로 만들어요. 인쇄하거나 PDF로 저장해 청년센터 상담 때 보여 주세요.':'관심 저장(☆)하거나 비교에 담은 사업이 있으면 메모로 묶을 수 있어요.'}</small>
    {open&&<dialog ref={ref} className="consult-dialog" aria-label="상담 준비 메모 미리보기" onCancel={e=>{e.preventDefault();setOpen(false);}}>
      <div className="consult-memo-actions"><button type="button" className="finder-primary" onClick={print}>인쇄 · PDF로 저장</button><button type="button" onClick={()=>setOpen(false)} autoFocus>닫기</button>
        <p>인쇄 창에서 ‘PDF로 저장’을 고르면 파일로 남길 수 있어요. 메모는 이 기기 밖으로 보내지 않아요.</p></div>
      <ConsultMemoSheet items={items} profile={profile} province={province} city={city} asOf={asOf}/>
    </dialog>}
  </div>;
}
