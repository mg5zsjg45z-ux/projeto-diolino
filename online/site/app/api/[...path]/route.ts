import {env} from 'cloudflare:workers';
import {getChatGPTUser} from '../../chatgpt-auth';
import {definitions, fresh, active, overview, plans, mutate, energy, tacoSearch, iso, validate, modulePreferences} from '../../../lib/domain.mjs';
import {exportSync,snapshot,reconcile,applySync} from '../../../lib/manual-sync.mjs';
export const dynamic='force-dynamic';
function reply(data:unknown,status=200){return Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});}
async function handle(request:Request){
  const user=await getChatGPTUser();if(!user)return reply({error:'Entre com ChatGPT para acessar seus registros.'},401);
  const db=env.DB;if(!db)return reply({error:'Banco online indisponível. Tente novamente.'},503);
  const url=new URL(request.url),path=url.pathname.slice(5),day=url.searchParams.get('day')||new Intl.DateTimeFormat('en-CA',{timeZone:'America/Fortaleza'}).format(new Date());
  try{
    if(request.method==='POST'){
      if(request.headers.get('Origin')!==url.origin||!request.headers.get('Content-Type')?.startsWith('application/json'))return reply({error:'Origem inválida.'},403);
      if(Number(request.headers.get('Content-Length')||0)>1800000)return reply({error:'Arquivo muito grande.'},413);
    }
    if(path==='session')return reply({csrf:'platform-session',ai_ready:false});
    if(path==='schema')return reply(definitions.schema);
    if(path==='library')return reply({versions:definitions.versions,books:definitions.books});
    const saved=await db.prepare('SELECT revision,data FROM accounts WHERE owner=?').bind(user.userId).first<{revision:number,data:string}>();
    let state=saved?JSON.parse(saved.data):fresh();
    const device=state.manual_sync?.device||'site-'+Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(user.userId)))).map(x=>x.toString(16).padStart(2,'0')).join('');
    if(request.method==='GET'){
      if(path==='overview')return reply(overview(state,iso(day)));
      if(path==='plans')return reply({plans:plans(state,iso(day)),templates:definitions.templates});
      if(path==='records'){let k=url.searchParams.get('kind')||'';if(!Object.hasOwn(definitions.schema,k))throw Error('Tipo inválido.');return reply(active(state,k,url.searchParams.get('filter')==='day'&&!['profile','sets'].includes(k)?iso(day):null).sort((a:any,b:any)=>b.id-a.id));}
      if(path==='taco')return reply(tacoSearch((url.searchParams.get('q')||'').slice(0,200)));
      if(path==='export')return reply(state);
      if(path==='sync/export')return reply(exportSync(state,device));
      if(path==='preferences')return reply({modules:modulePreferences(state.preferences?.modules)});
      return reply({error:'Página não encontrada.'},404);
    }
    const text=await request.text();if(new TextEncoder().encode(text).length>1800000)return reply({error:'Arquivo muito grande.'},413);
    const data=JSON.parse(text);let result;
    if(path==='sync/preview'){
      const plan=reconcile(snapshot(state,device),data.file);
      return reply({counts:plan.counts,conflicts:plan.conflicts,revision:saved?.revision??-1});
    }
    if(path==='sync/apply'){
      if(data.revision!==(saved?.revision??-1))return reply({error:'Os dados do site mudaram. Gere uma nova prévia antes de importar.'},409);
      const merged=applySync(state,device,data.file,data.choices||{});state=merged.state;result={ok:true,counts:merged.counts};
    }else
    if(path==='energy')return reply(energy(data));
    else if(path==='import'){
      if(Object.values(state.records).some((rows:any)=>rows.length))throw Error('A importação inicial exige uma conta sem registros. Exporte os dados existentes antes de continuar.');
      if(!['diolino-online-1','diolino-desktop-1'].includes(data.format)||!data.records)throw Error('Arquivo Diolino inválido.');
      const incoming: {format:string,nextId:number,records:Record<string, any[]>,audit:any[]}=fresh();const ids=new Set<string>();let max=0;
      for(const kind of Object.keys(definitions.schema)){let rows=data.records[kind]||[];if(!Array.isArray(rows))throw Error('Registros inválidos.');incoming.records[kind]=rows.map((r:any)=>{if(!Number.isSafeInteger(r.id)||r.id<1)throw Error('Identificador inválido.');const key=kind+':'+r.id;if(ids.has(key))throw Error('Identificador duplicado.');ids.add(key);max=Math.max(max,r.id);let row=validate(kind,r);return {...row,id:r.id,created_at:r.created_at||new Date().toISOString(),updated_at:r.updated_at||new Date().toISOString(),deleted_at:r.deleted_at||null,...(r._nutrition?{_nutrition:r._nutrition}:{})};});}
      for(const kind of Object.keys(definitions.schema))for(const row of active(incoming,kind))for(const field of definitions.schema[kind as keyof typeof definitions.schema].fields){if(['plan','workout'].includes(field.type)&&row[field.key]!=null&&!active(incoming,field.type==='plan'?'plans':'workout').some((r:any)=>r.id===row[field.key]))throw Error('Arquivo com associação ausente.');}
      for(const mark of active(incoming,'habit_marks'))if(!active(incoming,'habits').some((habit:any)=>habit.id===mark.habit_id))throw Error('Arquivo com marcação de hábito sem hábito associado.');
      for(const kind of ['daily','routine']){let dates=active(incoming,kind).map((r:any)=>r.date);if(new Set(dates).size!==dates.length)throw Error('Checagens duplicadas no arquivo.');}
      if(active(incoming,'profile').length>1)throw Error('Mais de um perfil no arquivo.');
      incoming.preferences={modules:modulePreferences(data.preferences?.modules)};incoming.nextId=max+1;incoming.audit=data.format==='diolino-online-1'&&Array.isArray(data.audit)?data.audit:[];incoming.audit.push({action:'importar',at:new Date().toISOString()});state=incoming;result={ok:true};
    }else result=mutate(state,path,data);
    const serialized=JSON.stringify(state);if(new TextEncoder().encode(serialized).length>1800000)throw Error('Limite desta versão atingido. Exporte seus registros; os dados anteriores estão preservados.');
    let written=saved?await db.prepare('UPDATE accounts SET data=?,revision=revision+1 WHERE owner=? AND revision=?').bind(serialized,user.userId,saved.revision).run():await db.prepare('INSERT OR IGNORE INTO accounts(owner,revision,data) VALUES(?,0,?)').bind(user.userId,serialized).run();
    if(written.meta.changes!==1)return reply({error:'Os dados foram alterados em outro dispositivo. Recarregue a página antes de repetir.'},409);
    return reply(result);
  }catch(error){return reply({error:error instanceof Error?error.message:'Não foi possível concluir.'},400);}
}
export const GET=handle;
export const POST=handle;
