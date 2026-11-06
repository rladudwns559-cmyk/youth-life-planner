export type DeadlineSource={intake_mode:string;ends_on:string|null};
/** Presentation order only; a published deadline does not prove active intake. */
export function deadlineOrder(p:DeadlineSource,asOf:string):number{
 if(p.intake_mode!=='WINDOW'||!p.ends_on||p.ends_on<asOf||!/^\d{4}-\d{2}-\d{2}$/.test(p.ends_on))return Infinity;
 const d=new Date(p.ends_on+'T00:00:00Z');
 return Number.isFinite(d.valueOf())&&d.toISOString().slice(0,10)===p.ends_on?d.valueOf():Infinity;
}
