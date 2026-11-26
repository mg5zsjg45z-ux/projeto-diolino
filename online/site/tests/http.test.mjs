import {test} from 'node:test';
import assert from 'node:assert/strict';
const base=`http://127.0.0.1:${process.env.DIOLINO_HTTP_TEST_PORT||5173}`;
test('authentication, origin protection and persistent CRUD in isolated local D1',async()=>{
 assert.equal((await fetch(base+'/api/export')).status,401);
 const login=await fetch(base+'/signin-with-chatgpt?return_to=/',{redirect:'manual',headers:{Host:new URL(process.env.DIOLINO_HTTP_TEST_ORIGIN||base).host}});
 const cookie=login.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');
 assert.ok(cookie);
 const headers={Cookie:cookie,Origin:base,'Content-Type':'application/json'};
 const post=(path,body,extra={})=>fetch(base+'/api/'+path,{method:'POST',headers:{...headers,...extra},body:JSON.stringify(body)});
 assert.equal((await post('check',{day:'2026-10-23',key:'bath_1',checked:true},{Origin:'https://invalid.example'})).status,403);
 const response=await post('save',{kind:'study',values:{date:'2026-10-23',topic:'Teste isolado '+Date.now(),duration_min:60,format:'Leitura'}});assert.equal(response.status,200,await response.clone().text());let {id}=await response.json();
 const overview=await (await fetch(base+'/api/overview?day=2026-10-23',{headers:{Cookie:cookie}})).json();assert.equal(overview.pillars.medicine_status.done,true);
 const exported=await (await fetch(base+'/api/export',{headers:{Cookie:cookie}})).json();assert.ok(exported.records.study.some(r=>r.id===id));
 assert.equal((await post('delete',{kind:'study',id})).status,200);
 const rows=await (await fetch(base+'/api/records?kind=study',{headers:{Cookie:cookie}})).json();assert.ok(!rows.some(r=>r.id===id));
 const noteResponse=await post('notebook/save',{values:{date:'2026-10-26',title:'Teste de exclusão isolado',content:'Texto fictício',favorite:'Não'}});
 assert.equal(noteResponse.status,200,await noteResponse.clone().text());const note=await noteResponse.json();
 assert.equal((await post('notebook/save',{id:note.id,expected_updated_at:'stale',values:{date:'2026-10-26',title:'Não sobrescrever',content:'Conflito'}})).status,400);
 assert.equal((await post('delete',{kind:'notebook',id:note.id})).status,200);
 const remaining=await (await fetch(base+'/api/records?kind=notebook',{headers:{Cookie:cookie}})).json();assert.ok(!remaining.some(r=>r.id===note.id));
 const exportedAfter=await (await fetch(base+'/api/export',{headers:{Cookie:cookie}})).json();assert.ok(exportedAfter.records.notebook.find(r=>r.id===note.id).deleted_at);assert.ok(exportedAfter.audit.some(r=>r.kind==='notebook'&&r.id===note.id&&r.action==='excluir'&&r.before.content==='Texto fictício'));
 assert.equal((await post('preferences',{modules:{agenda:false,notebook:true,planning:true,bible:true}})).status,200);
 const prefs=await (await fetch(base+'/api/preferences',{headers:{Cookie:cookie}})).json();assert.equal(prefs.modules.agenda,false);
 await post('preferences',{modules:{agenda:true,notebook:true,planning:true,bible:true}});

});

test('manual exchange previews before writing, requires authentication and rejects stale confirmation',async()=>{
 assert.equal((await fetch(base+'/api/sync/export')).status,401);
 const login=await fetch(base+'/signin-with-chatgpt?return_to=/',{redirect:'manual',headers:{Host:new URL(process.env.DIOLINO_HTTP_TEST_ORIGIN||base).host}});
 const cookie=login.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');
 const headers={Cookie:cookie,Origin:base,'Content-Type':'application/json'};
 const post=(path,data,extra={})=>fetch(base+'/api/'+path,{method:'POST',headers:{...headers,...extra},body:JSON.stringify(data)});
 const file=await (await fetch(base+'/api/sync/export',{headers:{Cookie:cookie}})).json();
 assert.equal(file.format,'diolino-sync-1');
 const id=Math.max(0,...file.records.study.map(r=>r.id))+1,topic='Troca manual isolada '+Date.now();
 file.records.study.push({id,date:'2026-11-04',time:'12:00',topic,duration_min:25,format:'Leitura',sync_ids:['isolated-http:study:'+id]});
 assert.equal((await post('sync/preview',{file},{Origin:'https://invalid.example'})).status,403);
 let response=await post('sync/preview',{file});assert.equal(response.status,200,await response.clone().text());
 const plan=await response.json();assert.equal(plan.counts.new,1);
 let records=await (await fetch(base+'/api/records?kind=study',{headers:{Cookie:cookie}})).json();
 assert.ok(!records.some(r=>r.topic===topic));
 response=await post('sync/apply',{file,revision:plan.revision,choices:{}});assert.equal(response.status,200,await response.clone().text());
 assert.equal((await post('sync/apply',{file,revision:plan.revision,choices:{}})).status,409);
 records=await (await fetch(base+'/api/records?kind=study',{headers:{Cookie:cookie}})).json();
 assert.equal(records.filter(r=>r.topic===topic).length,1);
 const again=await (await post('sync/preview',{file})).json();assert.equal(again.counts.new,0);
});
