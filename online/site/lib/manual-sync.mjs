import {definitions,validate} from './domain.mjs';
export const FORMAT='diolino-sync-1';
// These records are supported by the online account and its full backups, but
// the Windows exchange format has no compatible desktop model for them yet.
export const siteOnlyKinds=['daily_tasks','habits','habit_marks','strength_plan','bible_notes'];
export const kinds=['plans','workout',...Object.keys(definitions.schema).filter(k=>!['plans','workout','notebook',...siteOnlyKinds].includes(k)),'notebook'];
const natural={study:['date','time','topic'],workout:['date','time','name'],food:['date','time','meal','food_name'],hydration:['date','time','drink'],sleep:['date','start','type'],body:['date','time'],bible:['date','time','passage'],medication:['date','time','name'],health:['date','time'],exams:['date','name'],agenda:['date','time','title'],plans:['title','area'],plan_steps:['plan_id','title'],sets:['workout_id','exercise','set_number'],energy:['date','weight_kg','height_cm','age_years'],notebook:['date','title']};
const clone=v=>structuredClone(v);
function stable(v){if(Array.isArray(v))return v.map(stable);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,stable(v[k])]));return v;}
const equal=(a,b)=>JSON.stringify(stable(a))===JSON.stringify(stable(b));
export function normalized(kind,row){
 let result;
 if(kind==='notebook'){
  result={title:row.title,date:row.date,content:row.content,labels:row.labels||'',favorite:row.favorite||'Não'};
  if(!/^\d{4}-\d{2}-\d{2}$/.test(result.date)||new Date(result.date).toISOString().slice(0,10)!==result.date)throw Error('Data de anotação inválida.');
  if(['title','content','labels'].some(k=>typeof result[k]!=='string'||result[k].length>20000)||!['Sim','Não'].includes(result.favorite))throw Error('Anotação inválida ou acima de 20.000 caracteres.');
 }else result=validate(kind,row);
 if(kind==='food'&&row._nutrition){let n=clone(row._nutrition);if(!n.food)n={metadata:n.metadata,food:{code:n.code,name:n.name,nutrients:n.nutrients}};if(!n.metadata||!n.food?.nutrients||!Number.isInteger(n.food.code)||!n.food.name||['name','edition','year','version','source_url','sha256'].some(k=>!n.metadata[k])||['kcal','protein_g','carbs_g','fat_g','fiber_g'].some(k=>!(k in n.food.nutrients)))throw Error('Referência nutricional inválida.');result._nutrition=n;}
 return result;
}
export function snapshot(state,device){
 const meta=state.manual_sync||{device,aliases:{}};
 const records={};
 for(const kind of kinds)records[kind]=(state.records[kind]||[]).map(row=>({...normalized(kind,row),id:row.id,deleted_at:row.deleted_at||null,sync_ids:[...new Set([`${meta.device}:${kind}:${row.id}`,...(meta.aliases[`${kind}:${row.id}`]||[])])]}));
 return {format:FORMAT,source:meta.device,records};
}
export function exportSync(state,device){const data=snapshot(state,device);data.exported_at=new Date().toISOString();for(const kind of kinds)data.records[kind]=data.records[kind].filter(r=>!r.deleted_at);return data;}
export function reconcile(current,incoming,choices={}){
 if(incoming?.format!==FORMAT||!incoming.records||typeof incoming.records!=='object'||Array.isArray(incoming.records)||typeof incoming.source!=='string'||!incoming.source||incoming.source.length>100)throw Error('Use um arquivo exportado pelo botão de troca manual do Diolino.');
 const result=clone(current),mapping=new Map(),operations=[],conflicts=[],counts={new:0,same:0,conflicts:0,blocked:0,updated:0};
 for(const kind of kinds){
  const rows=incoming.records[kind]||[];if(!Array.isArray(rows)||rows.length>10000)throw Error('Lista de registros inválida.');
  const local=result.records[kind]||=[],seen=new Set(),claimed=new Set(),seenAliases=new Set();
  for(const raw of rows){
   if(!raw||!Number.isSafeInteger(raw.id)||raw.id<1||seen.has(raw.id))throw Error('Identificador inválido ou duplicado.');seen.add(raw.id);if(raw.deleted_at)continue;
   const aliases=raw.sync_ids;if(!Array.isArray(aliases)||!aliases.length||aliases.length>100||aliases.some(a=>typeof a!=='string'||!a||a.length>250||seenAliases.has(a)))throw Error('Vínculo de sincronização inválido ou repetido.');aliases.forEach(a=>seenAliases.add(a));
   const values=normalized(kind,raw);
   if(['sets','plan_steps'].includes(kind)){const [parent,field]=kind==='sets'?['workout','workout_id']:['plans','plan_id'];const mapped=mapping.get(`${parent}:${values[field]}`);if(mapped===undefined){counts.blocked++;continue;}values[field]=mapped;}
   const matches=local.filter(r=>r.sync_ids.some(a=>aliases.includes(a)));if(matches.length>1)throw Error('Vínculos ambíguos. Nenhum dado foi importado.');let match=matches[0];
   if(!match){const identical=local.filter(r=>!claimed.has(r.id)&&!r.deleted_at&&equal(normalized(kind,r),values));if(identical.length>1)throw Error('Há registros iguais ambíguos. Revise as duplicações antes de importar.');match=identical[0];}
   if(!match&&['daily','routine','profile'].includes(kind))match=local.find(r=>!r.deleted_at&&(kind==='profile'||r.date===values.date));
   const key=`${kind}:${raw.id}`;let possible=false;
   if(!match&&natural[kind]){const similar=local.filter(r=>!r.deleted_at&&!claimed.has(r.id)&&natural[kind].every(k=>r[k]===values[k]));if(similar.length>1)throw Error('Há registros semelhantes ambíguos. Revise antes de importar.');if(similar.length){possible=true;if(choices[key]!=='separate')match=similar[0];}}
   if(match&&claimed.has(match.id))throw Error('Mais de um registro do arquivo aponta para o mesmo registro local.');
   if(match?.deleted_at){counts.blocked++;continue;}
   let rid,action;
   if(match){rid=match.id;if(equal(normalized(kind,match),values)){counts.same++;action='same';}else{counts.conflicts++;conflicts.push({key,kind,local:clone(match),incoming:clone(values),possible});action=choices[key]==='incoming'?'update':'keep';if(action==='update'){counts.updated++;Object.assign(match,values);}}match.sync_ids=[...new Set([...match.sync_ids,...aliases])];}
   else{rid=Math.max(0,...local.map(r=>r.id))+1;action='new';match={...values,id:rid,sync_ids:[...aliases],deleted_at:null};local.push(match);counts.new++;}
   mapping.set(key,rid);claimed.add(rid);operations.push({kind,id:rid,action,values,aliases:match.sync_ids});
  }
 }
 return {candidate:result,operations,conflicts,counts};
}
export function applySync(state,device,incoming,choices={}){
 const plan=reconcile(snapshot(state,device),incoming,choices),next=clone(state),now=new Date().toISOString();
 next.manual_sync ||= {device,aliases:{}};
 for(const op of plan.operations){
  next.manual_sync.aliases[`${op.kind}:${op.id}`]=op.aliases;
  if(!['new','update'].includes(op.action))continue;
  const rows=next.records[op.kind]||=[],index=rows.findIndex(r=>r.id===op.id),before=index>=0?rows[index]:null;
  const row={...op.values,id:op.id,created_at:before?.created_at||now,updated_at:now,deleted_at:null};
  if(index>=0)rows[index]=row;else rows.push(row);
  next.audit.push({kind:op.kind,id:op.id,action:'importar manualmente',at:now,before});
 }
 next.nextId=Math.max(0,...Object.values(next.records).flat().map(r=>r.id))+1;
 return {state:next,counts:plan.counts};
}
