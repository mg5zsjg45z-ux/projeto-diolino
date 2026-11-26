import test from 'node:test';
import assert from 'node:assert/strict';
import {migrateTasks,nextTaskId,dailyTasks,parseCapture,setTaskState,shouldReconcileLegacyTasks} from '../src/taskModel.ts';
import {newSession,observe,change,finish,studyDurationMinutes} from '../src/focusModel.ts';
import {upsertStudy} from '../src/studyModel.ts';

const empty={tasks:[],studies:[],agenda:[],reviews:[]};
const legacy={id:'daily-1',text:'x'.repeat(160),minutes:30,date:'2026-11-25',done:false,steps:[{id:'s',text:'Ler',done:true}]};
test('migration survives restore and retry, preserving dates, identity, steps and long titles',()=>{
  const w=migrateTasks(empty,[legacy,legacy],false,[22],1000);
  assert.equal(w.tasks.length,1);
  const [task]=w.tasks;
  assert.deepEqual([task.id,task.due,task.date,task.estimated_minutes,task.title,task.steps],[23,null,legacy.date,30,legacy.text,legacy.steps]);
  assert.deepEqual(migrateTasks(structuredClone(w),[legacy],false,[],2000),w);
  const restored=migrateTasks({...empty,tasks:[{...task,title:task.title.slice(0,120)}]},[legacy],true,[],3000);
  assert.equal(restored.tasks[0].title,legacy.text);
  assert.equal(migrateTasks(empty,[legacy],true,[],0).tasks.length,1);
  const archived={...task,archived_at:2300};
  assert.ok(nextTaskId([archived])>archived.id);
  assert.equal(dailyTasks([archived],'2026-11-25').length,0);
  const done=setTaskState(task,'Concluído',400);
  assert.deepEqual(done.steps,legacy.steps);
  assert.equal(dailyTasks([done],legacy.date)[0].completed_at,400);
});
test('completed task migration reconciles a pending legacy row by identity',()=>{
  const migrated={...empty,dailyMigration:2,tasks:[{id:1,title:'Anterior',date:legacy.date,due:null,plan:'Pessoal',priority:'Normal',state:'A fazer',steps:[],estimated_minutes:null,legacy_daily_id:legacy.id,completed_at:null,updated_at:1}]};
  const extra={...legacy,id:'pending-extra',text:'Pendente preservada'};
  const next=migrateTasks(migrated,[legacy,extra],true,[],2000);
  assert.equal(next.tasks.length,2);
  assert.equal(next.tasks.find(row=>row.legacy_daily_id===extra.id)?.title,extra.text);
});
test('a pending legacy copy is reconciled even after migration was marked complete',()=>{
  assert.equal(shouldReconcileLegacyTasks({dailyMigration:2},true),true);
  assert.equal(shouldReconcileLegacyTasks({dailyMigration:2},false),false);
  assert.equal(shouldReconcileLegacyTasks({},false),true);
});
test('study edits apply to the latest workspace and keep other-window additions',()=>{
  const first={id:1,date:'2026-11-25',time:'08:00',topic:'Original',duration_min:30,format:'Leitura',source:null,learning:null,notes:null,attachment_path:null,attachment_name:null};
  const fromOtherWindow={id:2,date:'2026-11-26',time:'09:00',topic:'Outra janela',duration_min:20,format:'Leitura',source:null,learning:null,notes:null,attachment_path:null,attachment_name:null};
  const saved=upsertStudy([first,fromOtherWindow],first.id,{...first,topic:'Editado'});
  assert.equal(saved.length,2);
  assert.equal(saved.find(row=>row.id===1)?.topic,'Editado');
  assert.equal(saved.find(row=>row.id===2)?.topic,'Outra janela');
  assert.equal(upsertStudy(saved,null,{...first,id:undefined,topic:'Novo'}).find(row=>row.topic==='Novo')?.id,3);
});
test('daily filters and optional capture respect the selected civil date',()=>{
  const [t]=migrateTasks(empty,[legacy],false,[],0).tasks;
  const overdue={...t,id:3,due:'2026-11-24'};
  assert.deepEqual(dailyTasks([t,overdue,{...t,id:5,date:'2026-12-31'}],'2026-11-26').map(t=>t.id),[3,1]);
  assert.deepEqual(parseCapture('Ler capítulo #Bíblia p1 amanhã 30m','2026-12-31'),
    {title:'Ler capítulo',plan:'Bíblia',priority:'Alta',due:'2027-01-01',estimated_minutes:30});
});
function work(s,ms) {
  const start=s.checkpoint;
  for(let elapsed=0;elapsed<ms;elapsed+=1000)s=observe(s,'one',start+Math.min(ms,elapsed+1000));
  return s;
}
for(const mode of ['Pomodoro','Flowtime','Livre'])test(mode+' excludes pauses and confirms exactly once',()=>{
  let s=newSession(mode,{id:80,title:'Leitura'},mode==='Pomodoro'?25:null,'one',new Date(2026,10,26,12).getTime());
  s=work(s,180000);
  s=change(s,'paused','paused',s.checkpoint);
  s=change(s,'running','resumed',s.checkpoint+300000);
  s=work(s,120000);
  s=change(s,'review','ended',s.checkpoint);
  const w=finish({...empty,activeFocus:s},s.id,false,true,s.checkpoint);
  assert.equal(w.focusSessions[0].active_seconds,300);
  assert.equal(w.focusSessions[0].task_id,80);
  assert.equal(w.studies.length,1);
  assert.equal(w.studies[0].duration_min,5);
  assert.equal(finish(w,s.id,false,true,s.checkpoint),w);
  const discarded=finish({...empty,activeFocus:s},s.id,true,true,s.checkpoint);
  assert.equal(discarded.studies.length,0);
  assert.equal(discarded.focusSessions[0].status,'discarded');
});
test('suspension, clock rollback and reopening never credit the unobserved gap',()=>{
  const s=work(newSession('Pomodoro',null,25,'one',1000),4000);
  for(const [owner,now] of [['one',9000000],['two',9000000],['one',0]]) {
    const recovered=observe(s,owner,now);
    assert.equal(recovered.status,'paused');
    assert.equal(recovered.active_seconds,4);
    assert.equal(recovered.events.at(-1).name,'recovered');
  }
  assert.equal(observe(s,'two',s.checkpoint+1000),s);
});
test('focus study durations match the study editor tenth-minute precision',()=>{
  assert.equal(studyDurationMinutes(7000),0.1);
  assert.equal(studyDurationMinutes(16000),0.3);
  assert.equal(studyDurationMinutes(60000),1);
});
test('local midnight splits credited time and a fixed timer stops at the limit',()=>{
  const start=new Date(2026,10,26,23,59,30).getTime();
  const s=work(newSession('Pomodoro',null,1,'one',start),61000);
  assert.equal(s.status,'review');
  assert.deepEqual(s.days,{'2026-11-26':30000,'2026-11-27':30000});
  assert.equal(finish({...empty,activeFocus:s},s.id,false,false,s.checkpoint).studies.length,0);
});
