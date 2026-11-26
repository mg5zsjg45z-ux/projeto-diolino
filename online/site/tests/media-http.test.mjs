import {test} from 'node:test';
import assert from 'node:assert/strict';
import {PART_SIZE,STORAGE_LIMIT,MAX_FILE_SIZE} from '../lib/media.mjs';
const base=process.env.DIOLINO_HTTP_TEST_ORIGIN||`http://127.0.0.1:${process.env.DIOLINO_HTTP_TEST_PORT||5173}`;
async function session(){const response=await fetch(base+'/signin-with-chatgpt?return_to=/',{redirect:'manual'});return response.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');}
test('private multipart upload, resume, ranges, invalid requests and cancellation',async()=>{
 assert.equal((await fetch(base+'/api/files')).status,401);
 const cookie=await session(),headers={Cookie:cookie,Origin:base,'Content-Type':'application/json'};
 const post=(action,data={},id='')=>fetch(base+'/api/files?action='+action+'&id='+id,{method:'POST',headers,body:JSON.stringify(data)});
 const list=await (await fetch(base+'/api/files',{headers:{Cookie:cookie}})).json();assert.equal(list.limit,STORAGE_LIMIT);assert.equal(list.max_file,MAX_FILE_SIZE);
 const denied=await fetch(base+'/api/files?action=init',{method:'POST',headers:{...headers,Origin:'https://outside.example'},body:'{}'});assert.equal(denied.status,403);
 assert.equal((await post('init',{name:'bad.exe',size:1,category:'Pessoal',fingerprint:'a'.repeat(64)})).status,400);
 const created=await post('init',{name:'multipart-isolado.pdf',size:PART_SIZE+31,category:'Pessoal',fingerprint:'a'.repeat(64)});assert.equal(created.status,200,await created.clone().text());const {id}=await created.json();
 try{
  assert.equal((await fetch(base+'/api/files?id='+id)).status,401);
  assert.equal((await post('complete',{},id)).status,409);
  const first=new Uint8Array(PART_SIZE);first.set(new TextEncoder().encode('%PDF-1.4\n'));
  async function part(n,bytes){return fetch(base+'/api/files?action=part&id='+id+'&part='+n,{method:'POST',headers:{...headers,'Content-Type':'application/octet-stream'},body:bytes});}
  assert.equal((await part(1,new Uint8Array(17))).status,400);
  assert.equal((await part(1,first)).status,200);
  const status=await (await post('status',{},id)).json();assert.equal(status.parts.length,1);assert.equal(status.parts[0].part_number,1);
  assert.equal((await part(2,new Uint8Array(31).fill(65))).status,200);
  const complete=await post('complete',{},id);assert.equal(complete.status,200,await complete.clone().text());
  const range=await fetch(base+'/api/files?id='+id,{headers:{Cookie:cookie,Range:'bytes=0-8'}});assert.equal(range.status,206);assert.equal(await range.text(),'%PDF-1.4\n');assert.equal(range.headers.get('cache-control'),'private, no-store');
  assert.equal((await fetch(base+'/api/files?id='+id,{headers:{Cookie:cookie,Range:'bytes=999999999-'}})).status,416);
  const wrong=await post('status',{},'not-owner-or-missing');assert.equal(wrong.status,404);
 }finally{assert.equal((await post('delete',{},id)).status,200);}
 assert.equal((await fetch(base+'/api/files?id='+id,{headers:{Cookie:cookie}})).status,404);
 const pending=await (await post('init',{name:'cancelamento.pdf',size:1024,category:'Outros',fingerprint:'b'.repeat(64)})).json();assert.equal((await post('delete',{},pending.id)).status,200);
 const after=await (await fetch(base+'/api/files',{headers:{Cookie:cookie}})).json();assert.equal(after.used,list.used);
});

test('200 MiB multipart file fits the operational limit without a large request',async()=>{
 const cookie=await session(),headers={Cookie:cookie,Origin:base,'Content-Type':'application/json'},post=(action,data={},id='')=>fetch(base+'/api/files?action='+action+'&id='+id,{method:'POST',headers,body:JSON.stringify(data)});
 const size=200*1024*1024,created=await post('init',{name:'teste-sintetico-200MiB.mp4',size,category:'Outros',fingerprint:'c'.repeat(64)});assert.equal(created.status,200,await created.clone().text());const {id}=await created.json();
 try{
  const block=new Uint8Array(PART_SIZE);block.set([0,0,0,24,102,116,121,112]);
  for(let part=1;part<=size/PART_SIZE;part++){const response=await fetch(base+'/api/files?action=part&id='+id+'&part='+part,{method:'POST',headers:{...headers,'Content-Type':'application/octet-stream'},body:block});assert.equal(response.status,200,await response.clone().text());}
  const complete=await post('complete',{},id);assert.equal(complete.status,200,await complete.clone().text());
  const tail=await fetch(base+'/api/files?id='+id,{headers:{Cookie:cookie,Range:'bytes=-16'}});assert.equal(tail.status,206);assert.equal((await tail.arrayBuffer()).byteLength,16);
 }finally{await post('delete',{},id);}
});
