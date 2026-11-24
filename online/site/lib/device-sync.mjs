import {fresh} from './domain.mjs';
import {exportSync, snapshot, reconcile, applySync} from './manual-sync.mjs';

export const SYNC_LIMIT=1800000;
const json=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
const digest=async value=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))).map(v=>v.toString(16).padStart(2,'0')).join('');
const random=()=>Array.from(crypto.getRandomValues(new Uint8Array(32))).map(v=>v.toString(16).padStart(2,'0')).join('');
async function tables(db){
 await db.prepare('CREATE TABLE IF NOT EXISTS desktop_devices(id TEXT PRIMARY KEY,owner TEXT NOT NULL,label TEXT NOT NULL,token_hash TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL,expires_at TEXT NOT NULL,revoked_at TEXT)').run();
 await db.prepare('CREATE TABLE IF NOT EXISTS desktop_sync_backups(owner TEXT NOT NULL,revision INTEGER NOT NULL,data TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(owner,revision))').run();
}
async function body(request){
 if(!request.headers.get('Content-Type')?.startsWith('application/json'))throw Error('Use JSON.');
 if(Number(request.headers.get('Content-Length')||0)>SYNC_LIMIT)throw Error('Limite de 1,8 MB excedido.');
 const text=await request.text();if(new TextEncoder().encode(text).length>SYNC_LIMIT)throw Error('Limite de 1,8 MB excedido.');
 return JSON.parse(text);
}
export async function devices(request,env,user){
 if(!user)return json({error:'Entre na sua conta para conectar o Windows.'},401);
 if(!env.DB)return json({error:'Banco indisponível.'},503);
 const url=new URL(request.url),db=env.DB;
 try{
  await tables(db);
  if(request.method==='GET'){
   const result=await db.prepare('SELECT id,label,created_at,expires_at,revoked_at FROM desktop_devices WHERE owner=? ORDER BY created_at DESC LIMIT 100').bind(user.userId).all();
   return json({devices:result.results});
  }
  if(request.method!=='POST')return json({error:'Método inválido.'},405);
  if(request.headers.get('Origin')!==url.origin)return json({error:'Origem inválida.'},403);
  const data=await body(request);
  if(data.action==='revoke'){
   if(typeof data.id!=='string'||data.id.length>100)throw Error('Conexão inválida.');
   await db.prepare('UPDATE desktop_devices SET revoked_at=? WHERE owner=? AND id=? AND revoked_at IS NULL').bind(new Date().toISOString(),user.userId,data.id).run();
   return json({ok:true});
  }
  if(data.action!=='create')throw Error('Ação inválida.');
  if(!env.DIOLINO_DISPATCH_TOKEN)return json({error:'A conexão de serviço ainda não foi configurada.'},503);
  const label=String(data.label||'Windows').trim();if(!label||label.length>100)throw Error('Nome do computador inválido.');
  const count=await db.prepare('SELECT COUNT(*) AS total FROM desktop_devices WHERE owner=? AND revoked_at IS NULL AND expires_at>?').bind(user.userId,new Date().toISOString()).first();
  if(count.total>=10)throw Error('Revogue uma conexão antiga antes de conectar outro computador. Limite: 10.');
  const token=random(),id=crypto.randomUUID(),created=new Date().toISOString(),expires=new Date(Date.now()+365*86400000).toISOString();
  await db.prepare('INSERT INTO desktop_devices(id,owner,label,token_hash,created_at,expires_at) VALUES(?,?,?,?,?,?)').bind(id,user.userId,label,await digest(token),created,expires).run();
  return json({format:'diolino-site-connection-1',url:url.origin,device_id:id,device_token:token,gateway_token:env.DIOLINO_DISPATCH_TOKEN,account:user.email,expires_at:expires});
 }catch(error){return json({error:error instanceof Error?error.message:'Não foi possível preparar a conexão.'},400);}
}
export async function desktopSync(request,env){
 if(!env.DB)return json({error:'Banco indisponível.'},503);
 try{
  const token=request.headers.get('Authorization')?.match(/^Bearer ([a-f0-9]{64})$/)?.[1];
  if(!token)return json({error:'Conexão não autorizada.'},401);
  const db=env.DB;await tables(db);
  const device=await db.prepare('SELECT id,owner,expires_at FROM desktop_devices WHERE token_hash=? AND revoked_at IS NULL AND expires_at>?').bind(await digest(token),new Date().toISOString()).first();
  if(!device)return json({error:'Conexão expirada ou revogada. Conecte este PC novamente pelo site.'},401);
  const saved=await db.prepare('SELECT revision,data FROM accounts WHERE owner=?').bind(device.owner).first();
  const state=saved?JSON.parse(saved.data):fresh(),identity='site-'+await digest(device.owner);
  const current=()=>({file:exportSync(state,identity),revision:saved?.revision??-1,device_id:device.id});
  if(request.method==='GET')return json(current());
  if(request.method!=='POST')return json({error:'Método inválido.'},405);
  const data=await body(request);
  if(!['preview','apply'].includes(data.action))throw Error('Ação inválida.');
  if(data.action==='preview'){
   const plan=reconcile(snapshot(state,identity),data.file);
   return json({...current(),counts:plan.counts,conflicts:plan.conflicts});
  }
  if(data.revision!==(saved?.revision??-1))return json({error:'Os dados online mudaram. Gere outra prévia.'},409);
  const merged=applySync(state,identity,data.file,data.choices||{}),encoded=JSON.stringify(merged.state);
  if(new TextEncoder().encode(encoded).length>SYNC_LIMIT)throw Error('Limite da conta de 1,8 MB atingido. Os dados anteriores foram preservados.');
  let written;
  if(saved){
   const results=await db.batch([
    db.prepare('INSERT OR IGNORE INTO desktop_sync_backups(owner,revision,data,created_at) SELECT owner,revision,data,? FROM accounts WHERE owner=? AND revision=?').bind(new Date().toISOString(),device.owner,saved.revision),
    db.prepare('UPDATE accounts SET data=?,revision=revision+1 WHERE owner=? AND revision=? AND EXISTS (SELECT 1 FROM desktop_devices WHERE id=? AND revoked_at IS NULL AND expires_at>?)').bind(encoded,device.owner,saved.revision,device.id,new Date().toISOString())
   ]);written=results[1];
  }else written=await db.prepare('INSERT OR IGNORE INTO accounts(owner,revision,data) SELECT ?,0,? WHERE EXISTS (SELECT 1 FROM desktop_devices WHERE id=? AND revoked_at IS NULL AND expires_at>?)').bind(device.owner,encoded,device.id,new Date().toISOString()).run();
  if(written.meta.changes!==1)return json({error:'Os dados ou a autorização mudaram. Tente novamente.'},409);
  // Retain the twenty most recent states before device imports for this owner.
  await db.prepare('DELETE FROM desktop_sync_backups WHERE owner=? AND revision NOT IN (SELECT revision FROM desktop_sync_backups WHERE owner=? ORDER BY revision DESC LIMIT 20)').bind(device.owner,device.owner).run();
  return json({ok:true,counts:merged.counts,file:exportSync(merged.state,identity),revision:(saved?.revision??-1)+1,device_id:device.id});
 }catch(error){return json({error:error instanceof Error?error.message:'Sincronização não concluída.'},400);}
}
