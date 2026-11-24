import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {devices,desktopSync} from '../lib/device-sync.mjs';
import {fresh} from '../lib/domain.mjs';

function database(){
 const sqlite=new DatabaseSync(':memory:');
 sqlite.exec('CREATE TABLE accounts(owner TEXT PRIMARY KEY,revision INTEGER NOT NULL,data TEXT NOT NULL)');
 const db={
  prepare(sql){let values=[];return {
   bind(...args){values=args;return this;},
   async first(){return sqlite.prepare(sql).get(...values)||null;},
   async all(){return {results:sqlite.prepare(sql).all(...values)};},
   async run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...values).changes)}};}
  };},
  async batch(statements){sqlite.exec('BEGIN IMMEDIATE');try{const result=[];for(const statement of statements)result.push(await statement.run());sqlite.exec('COMMIT');return result;}catch(error){sqlite.exec('ROLLBACK');throw error;}}
 };
 return {sqlite,db};
}
const origin='https://diolino-test.example';
const request=(path,body,headers={})=>new Request(origin+path,{...(body===undefined?{}:{method:'POST',body:JSON.stringify(body)}),headers:{'Content-Type':'application/json',Origin:origin,...headers}});

test('device credentials preserve account isolation, origin checks, revision CAS, backups and revocation',async()=>{
 const {sqlite,db}=database(),env={DB:db,DIOLINO_DISPATCH_TOKEN:'synthetic-dispatch-token-never-production'},a={userId:'owner-a',email:'a@example.test'},b={userId:'owner-b',email:'b@example.test'};
 try{
  assert.equal((await devices(request('/api/devices'),env,null)).status,401);
  assert.equal((await devices(request('/api/devices',{action:'create'},{Origin:'https://evil.example'}),env,a)).status,403);
  assert.equal((await devices(request('/api/devices',{action:'create'}),{DB:db},a)).status,503);
  const created=await devices(request('/api/devices',{action:'create',label:'Synthetic Windows'}),env,a);
  assert.equal(created.status,200);
  const connection=await created.json();assert.equal(connection.format,'diolino-site-connection-1');assert.equal(connection.device_token.length,64);
  const stored=sqlite.prepare('SELECT * FROM desktop_devices').get();assert.notEqual(stored.token_hash,connection.device_token);assert.equal(stored.owner,a.userId);
  const listed=await (await devices(request('/api/devices'),env,a)).json();assert.equal(listed.devices.length,1);assert.ok(!JSON.stringify(listed).includes(connection.device_token));assert.ok(!JSON.stringify(listed).includes(stored.token_hash));
  assert.equal((await (await devices(request('/api/devices'),env,b)).json()).devices.length,0);
  assert.equal((await desktopSync(request('/api/desktop-sync'),env)).status,401);
  const auth={Authorization:'Bearer '+connection.device_token};
  const current=await (await desktopSync(request('/api/desktop-sync',undefined,auth),env)).json();assert.equal(current.revision,-1);
  const file={...current.file,source:'synthetic-pc'};file.records.study.push({id:1,date:'2026-11-04',topic:'Synthetic fixture',duration_min:25,format:'Leitura',sync_ids:['synthetic-pc:study:1']});
  let plan=await (await desktopSync(request('/api/desktop-sync',{action:'preview',file},auth),env)).json();assert.equal(plan.counts.new,1);
  assert.equal((await desktopSync(request('/api/desktop-sync',{action:'apply',file,revision:42},auth),env)).status,409);
  let accepted=await desktopSync(request('/api/desktop-sync',{action:'apply',file,revision:plan.revision},auth),env);assert.equal(accepted.status,200,await accepted.clone().text());
  let result=await accepted.json();assert.equal(result.file.records.study[0].topic,'Synthetic fixture');assert.equal(result.revision,0);
  // Another account's records are never touched by the device credential.
  const other=fresh();other.records.study=[{id:1,date:'2026-11-04',topic:'Other owner',duration_min:60,format:'Leitura'}];
  sqlite.prepare('INSERT INTO accounts VALUES(?,?,?)').run(b.userId,0,JSON.stringify(other));
  file.records.study[0].duration_min=40;
  plan=await (await desktopSync(request('/api/desktop-sync',{action:'preview',file},auth),env)).json();
  accepted=await desktopSync(request('/api/desktop-sync',{action:'apply',file,revision:plan.revision,choices:{'study:1':'incoming'}},auth),env);
  result=await accepted.json();assert.equal(result.file.records.study[0].duration_min,40);
  assert.equal(JSON.parse(sqlite.prepare('SELECT data FROM accounts WHERE owner=?').get(b.userId).data).records.study[0].topic,'Other owner');
  assert.equal(JSON.parse(sqlite.prepare('SELECT data FROM desktop_sync_backups WHERE owner=? AND revision=0').get(a.userId).data).records.study[0].duration_min,25);
  await devices(request('/api/devices',{action:'revoke',id:connection.device_id}),env,b);
  assert.equal((await desktopSync(request('/api/desktop-sync',undefined,auth),env)).status,200);
  await devices(request('/api/devices',{action:'revoke',id:connection.device_id}),env,a);
  assert.equal((await desktopSync(request('/api/desktop-sync',undefined,auth),env)).status,401);
 }finally{sqlite.close();}
});
