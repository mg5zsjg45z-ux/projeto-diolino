const parse=value=>{if(!/^\d{4}-\d{2}-\d{2}$/.test(value))throw Error('Data inválida.');const d=new Date(value+'T12:00:00Z');if(!Number.isFinite(d.getTime())||d.toISOString().slice(0,10)!==value)throw Error('Data inválida.');return d;};
const format=d=>d.toISOString().slice(0,10);
export function plannerPeriod(value,mode){
 const start=parse(value);let count=1;
 if(mode==='week'){start.setUTCDate(start.getUTCDate()-(start.getUTCDay()+6)%7);count=7;}
 else if(mode==='month'){start.setUTCDate(1);count=new Date(Date.UTC(start.getUTCFullYear(),start.getUTCMonth()+1,0)).getUTCDate();}
 else if(mode!=='day')throw Error('Período inválido.');
 return Array.from({length:count},(_,index)=>{const d=new Date(start);d.setUTCDate(start.getUTCDate()+index);return format(d)});
}
export function shiftPlannerDate(value,mode,amount){
 const d=parse(value);if(mode==='month'){const original=d.getUTCDate();d.setUTCDate(1);d.setUTCMonth(d.getUTCMonth()+amount);d.setUTCDate(Math.min(original,new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,0)).getUTCDate()));}
 else d.setUTCDate(d.getUTCDate()+amount*(mode==='week'?7:1));return format(d);
}

export function plannerHour(time){const match=/^(\d{2}):(\d{2})$/.exec(time||'');return match&&Number(match[1])<24&&Number(match[2])<60?Number(match[1]):null;}
export function visiblePlannerHours(events,full=false){const hours=new Set(Array.from({length:full?24:17},(_,i)=>i+(full?0:6)));for(const event of events){const hour=plannerHour(event.time);if(hour!==null)hours.add(hour)}return [...hours].sort((a,b)=>a-b);}
