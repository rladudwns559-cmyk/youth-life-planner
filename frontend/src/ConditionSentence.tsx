import {useState} from 'react';
import {parseConditions,describeParsed,type ParsedConditions} from './condition-parser';
import './condition-sentence.css';

/**
 * One sentence instead of seven boxes: what was understood is filled into the form below and
 * shown back, so the person can see and correct it. The sentence stays on this screen only.
 */
export default function ConditionSentence({onApply}:{onApply:(p:ParsedConditions)=>void}){
  const [text,setText]=useState('');
  const [result,setResult]=useState<ParsedConditions|null>(null);
  function submit(e:React.FormEvent){
    e.preventDefault();
    const parsed=parseConditions(text);
    setResult(parsed);
    if(describeParsed(parsed).length)onApply(parsed);
  }
  const rows=result?describeParsed(result):[];
  return <form className="condition-sentence" onSubmit={submit} aria-labelledby="condition-sentence-title">
    <h3 id="condition-sentence-title">내 상황을 한 문장으로 적어 보세요</h3>
    <div className="condition-sentence-row">
      <label htmlFor="condition-sentence-input" className="sr-only">내 상황 문장</label>
      <input id="condition-sentence-input" type="text" maxLength={300} value={text} onChange={e=>setText(e.target.value)}
        placeholder="예: 안산 사는 24살 대학생이고 월세 살아요" aria-describedby="condition-sentence-help"/>
      <button type="submit" className="finder-primary" disabled={!text.trim()}>조건 채우기</button>
    </div>
    <p id="condition-sentence-help">지역·나이·학력·취업 상태·월세·혼인 여부를 알아들으면 아래 칸에 채워 드려요. 적은 문장은 이 화면에서만 읽고 저장하거나 보내지 않아요.</p>
    {result&&<div className="condition-sentence-result" role="status">
      {rows.length>0&&<><p><b>이렇게 이해했어요</b> · 다르면 아래 칸에서 바로 고칠 수 있어요.</p>
        <ul>{rows.map(r=><li key={r.label}><span>{r.label}</span>{r.value}</li>)}</ul></>}
      {result.notes.map(n=><p key={n} className="condition-sentence-note">{n}</p>)}
    </div>}
  </form>;
}
