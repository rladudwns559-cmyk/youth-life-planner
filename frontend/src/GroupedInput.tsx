import {useLayoutEffect,useRef,type InputHTMLAttributes} from 'react';

export function formatGroupedNumber(raw:string):string {
 if(!/^-?\d+(?:\.\d*)?$/.test(raw))return raw;
 const [integer,fraction]=raw.split('.');
 return integer.replace(/\B(?=(\d{3})+(?!\d))/g,',')+(fraction===undefined?'':'.'+fraction);
}
export function stripNumberGroups(text:string):string{
 return text.replace(/\d[\d,]*/g,part=>/^\d{1,3}(?:,\d{3})+$/.test(part)?part.replace(/,/g,''):part);
}
type Props=Omit<InputHTMLAttributes<HTMLInputElement>,'value'> & {value:string;mode?:'number'|'search'};
function positionAt(display:string,index:number){
 let i=0,count=0;
 while(i<display.length&&count<index){if(display[i]!==',')count++;i++;}
 return i;
}
export default function GroupedInput({value,onChange,onKeyDown,mode='number',...props}:Props){
 const ref=useRef<HTMLInputElement>(null);
 const pending=useRef<{value:string;index:number}|null>(null);
 const format=(raw:string)=>mode==='search'?(/^\d+$/.test(raw)?formatGroupedNumber(raw):raw):formatGroupedNumber(raw);
 const displayed=format(value);
 useLayoutEffect(()=>{
  const p=pending.current,el=ref.current;
  if(p&&el&&p.value===value&&document.activeElement===el){
   const pos=positionAt(displayed,p.index);el.setSelectionRange(pos,pos);pending.current=null;
  }
 });
 return <input {...props} ref={ref} value={displayed} onKeyDown={event=>{
  onKeyDown?.(event);
  if(event.defaultPrevented)return;
  const el=event.currentTarget,start=el.selectionStart,end=el.selectionEnd;
  if(start===null||start!==end||!/^[-\d,.]+$/.test(el.value))return;
  if(event.key==='Backspace'&&start>1&&el.value[start-1]===',')el.setSelectionRange(start-2,start);
  if(event.key==='Delete'&&el.value[start]===',')el.setSelectionRange(start,start+2);
 }} onChange={event=>{
  const el=event.currentTarget,typed=el.value,pos=el.selectionStart??typed.length;
  const raw=mode==='search'?(/^[0-9,]*$/.test(typed)?typed.replace(/,/g,''):stripNumberGroups(typed)):typed.replace(/,/g,'');
  const index=typed.slice(0,pos).replace(/,/g,'').length;
  pending.current={value:raw,index};
  el.value=raw;
  onChange?.(event);
  el.value=format(raw);
  if(document.activeElement===el){const next=positionAt(el.value,index);el.setSelectionRange(next,next);}
 }}/>;
}
