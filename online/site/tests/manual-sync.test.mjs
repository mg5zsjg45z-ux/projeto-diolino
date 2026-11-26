import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fresh,mutate,active} from '../lib/domain.mjs';
import {exportSync,snapshot,reconcile,applySync,kinds} from '../lib/manual-sync.mjs';
const study=(s,topic='Tema',duration_min=25)=>mutate(s,'save',{kind:'study',values:{date:'2026-11-04',time:'10:00',topic,duration_min,format:'Leitura'}});
test('manual exchange preserves unrelated rows, stable aliases, edits and repeated imports',()=>{
 let a=fresh(),b=fresh();study(a,'A');study(b,'B');
 b=applySync(b,'b',exportSync(a,'a')).state;
 assert.equal(active(b,'study').length,2);
 a=applySync(a,'a',exportSync(b,'b')).state;
 b=applySync(b,'b',exportSync(a,'a')).state;
 assert.equal(active(a,'study').length,2);assert.equal(active(b,'study').length,2);
 const row=active(a,'study').find(r=>r.topic==='A');mutate(a,'save',{kind:'study',id:row.id,values:{...row,duration_min:50}});
 const incoming=exportSync(a,'a'),plan=reconcile(snapshot(b,'b'),incoming);
 assert.equal(plan.conflicts.length,1);
 const next=applySync(b,'b',incoming,{[plan.conflicts[0].key]:'incoming'});
 assert.equal(active(next.state,'study').find(r=>r.topic==='A').duration_min,50);
 assert.equal(active(b,'study').find(r=>r.topic==='A').duration_min,25);
});
test('manual preview maps plan IDs, preserves deletions and refuses invalid/ambiguous files',()=>{
 const a=fresh(),b=fresh();mutate(a,'plans/create',{values:{title:'Plano',area:'Medicina',status:'Ativo',priority:'Normal'},steps:['Etapa']});
 mutate(b,'plans/create',{values:{title:'Outro',area:'Pessoal',status:'Ativo',priority:'Normal'},steps:[]});
 const next=applySync(b,'b',exportSync(a,'a')).state,step=active(next,'plan_steps')[0];
 assert.equal(active(next,'plans').find(r=>r.id===step.plan_id).title,'Plano');
 mutate(next,'delete',{kind:'plan_steps',id:step.id});
 assert.equal(reconcile(snapshot(next,'b'),exportSync(a,'a')).counts.blocked,1);
 const bad=exportSync(a,'a');bad.records.plans[0].sync_ids=[];
 assert.throws(()=>reconcile(snapshot(b,'b'),bad));
});
test('possible match without identity supports retaining two independent records',()=>{
 const a=fresh(),b=fresh();study(a,'Tema',25);study(b,'Tema',40);
 const file=exportSync(a,'a'),plan=reconcile(snapshot(b,'b'),file);
 assert.equal(plan.conflicts[0].possible,true);
 const next=applySync(b,'b',file,{[plan.conflicts[0].key]:'separate'});
 assert.equal(active(next.state,'study').length,2);
});
test('online-only modules remain in account data and are excluded from Windows exchange',()=>{
 const s=fresh();mutate(s,'save',{kind:'daily_tasks',values:{date:'2026-11-04',title:'Tarefa web',estimate_min:20,status:'Pendente',micro_steps:'[]'}});mutate(s,'save',{kind:'habits',values:{name:'Alongar',frequency:'Diário',notes:''}});const h=active(s,'habits')[0];mutate(s,'save',{kind:'habit_marks',values:{habit_id:h.id,date:'2026-11-04',status:'Concluído',notes:''}});mutate(s,'save',{kind:'bible_notes',values:{edition:'BPM',book_code:'GEN',book_name:'Gênesis',chapter:'1',verse:'1',marked:'Sim',comment:''}});const file=exportSync(s,'site');assert.equal(active(s,'daily_tasks').length,1);for(const kind of ['daily_tasks','habits','habit_marks','strength_plan','bible_notes']){assert.equal(Object.hasOwn(file.records,kind),false);assert.equal(kinds.includes(kind),false);}
});
