import test from 'node:test';
import assert from 'node:assert/strict';
import {TECM_PLAN,TECM_AREAS,buildTecmTasks} from '../src/tecmPlan.mjs';

test('39 semanas, oito horas por semana e duas semanas por área',()=>{
  const tasks=buildTecmTasks([],0,100);
  assert.equal(tasks.length,234);
  assert.equal(tasks[0].due,'2026-12-01');
  assert.equal(tasks.at(-1).due,'2027-08-29');
  assert.equal(new Set(tasks.map(t=>t.id)).size,234);
  for(let week=0;week<39;week++){
    const block=tasks.slice(week*6,week*6+6);
    assert.equal(block.reduce((sum,t)=>sum+t.estimated_minutes,0),480);
    assert.ok(block.every(t=>t.plan===TECM_PLAN&&t.priority==='Alta'&&t.state==='A fazer'&&t.estimated_minutes<=120));
  }
  for(const area of TECM_AREAS)assert.equal(tasks.filter(t=>t.title.split(' · ')[1]===area).length,12);
});
test('preserva tarefas anteriores, respeita o piso de IDs e não duplica',()=>{
  const existing={id:5,plan:'Outro'};
  const tasks=buildTecmTasks([existing],50,100);
  assert.equal(tasks[0],existing);
  assert.equal(tasks[1].id,51);
  assert.equal(buildTecmTasks(tasks),tasks);
  const archived=[{...tasks[1],archived_at:101}];
  assert.equal(buildTecmTasks(archived),archived);
});
