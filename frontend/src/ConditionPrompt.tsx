import {useEffect,useRef} from 'react';

export default function ConditionPrompt({onClose}:{onClose:(edit:boolean)=>void}){
 const ref=useRef<HTMLDialogElement>(null);
 useEffect(()=>{
  const dialog=ref.current!;
  const trigger=document.activeElement instanceof HTMLElement?document.activeElement:null;
  const previous=document.body.style.overflow;
  if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','');
  document.body.style.overflow='hidden';
  return ()=>{if(typeof dialog.close==='function'&&dialog.open)dialog.close();document.body.style.overflow=previous;trigger?.focus({preventScroll:true});};
 },[]);
 return <dialog ref={ref} className="support-condition-prompt" aria-labelledby="support-condition-title" aria-describedby="support-condition-description" onCancel={e=>{e.preventDefault();onClose(false);}}>
  <span className="support-prompt-icon" aria-hidden="true">!</span>
  <h2 id="support-condition-title">내 조건을 먼저 입력해 주세요</h2>
  <p id="support-condition-description">지역·나이·취업 상태·월세 거주 여부 중 한 가지 이상 알려주세요. 모르는 항목은 비워두셔도 괜찮아요.</p>
  <div><button type="button" onClick={()=>onClose(false)}>닫기</button><button type="button" className="support-prompt-primary" autoFocus onClick={()=>onClose(true)}>조건 입력하기</button></div>
 </dialog>;
}
