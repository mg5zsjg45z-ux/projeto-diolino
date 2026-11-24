import {env} from 'cloudflare:workers';
import {getChatGPTUser} from '../../chatgpt-auth';
import {PART_SIZE,MAX_FILE_SIZE,STORAGE_LIMIT,CATEGORIES,validateFile,expectedPart,validSignature,byteRange,safeFile} from '../../../lib/media.mjs';
export const dynamic='force-dynamic';
const json=(data:unknown,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});
async function bodyJSON(request:Request){
 const bytes=await limitedBody(request,8192);return JSON.parse(new TextDecoder().decode(bytes));
}
async function limitedBody(request:Request,limit:number,exact=false){
 if(!request.body)throw Error('Arquivo não recebido.');
 const reader=request.body.getReader(),result=new Uint8Array(limit);let length=0;
 try{while(true){const {value,done}=await reader.read();if(done)break;if(length+value.length>limit)throw Error('Envio acima do tamanho permitido.');result.set(value,length);length+=value.length;}}
 catch(error){await reader.cancel().catch(()=>{});throw error;}
 if(exact&&length!==limit)throw Error('Parte incompleta. Tente novamente.');
 return result.subarray(0,length);
}
async function handle(request:Request){
 const user=await getChatGPTUser();if(!user)return json({error:'Entre com ChatGPT para acessar seus arquivos.'},401);
 const db=env.DB,bucket=env.BUCKET;if(!db||!bucket)return json({error:'Biblioteca indisponível. O armazenamento ainda não foi conectado.'},503);
 const url=new URL(request.url),action=url.searchParams.get('action')||'',id=url.searchParams.get('id')||'',owner=user.userId;
 try{
  if(request.method==='GET'){
   if(!id){const files=await db.prepare("SELECT * FROM media_files WHERE owner=? AND status NOT IN ('deleted','failed') ORDER BY created_at DESC LIMIT 1000").bind(owner).all();const used=await db.prepare("SELECT COALESCE(SUM(size),0) AS used FROM media_files WHERE owner=? AND status NOT IN ('deleted','failed')").bind(owner).first();return json({files:files.results.map(safeFile),used:used?.used||0,limit:STORAGE_LIMIT,max_file:MAX_FILE_SIZE,part_size:PART_SIZE,categories:CATEGORIES});}
   const row:any=await db.prepare("SELECT * FROM media_files WHERE id=? AND owner=? AND status='ready'").bind(id,owner).first();if(!row)return json({error:'Arquivo não encontrado.'},404);
   let range;try{range=byteRange(request.headers.get('Range'),row.size)}catch{return new Response(null,{status:416,headers:{'Content-Range':`bytes */${row.size}`,'Cache-Control':'private, no-store'}})}
   const object=await bucket.get(row.object_key,range?{range}:undefined);if(!object)return json({error:'Arquivo não encontrado no armazenamento.'},404);
   const inline=url.searchParams.get('download')!=='1'&&/^(video\/|audio\/|image\/|application\/pdf$)/.test(row.mime);
   const headers:Record<string,string>={'Content-Type':row.mime,'Content-Length':String(range?range.length:row.size),'Accept-Ranges':'bytes','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Cross-Origin-Resource-Policy':'same-origin','Content-Disposition':`${inline?'inline':'attachment'}; filename*=UTF-8''${encodeURIComponent(row.name)}`};
   if(row.mime==='application/pdf')headers['Content-Security-Policy']="default-src 'none'; sandbox";
   if(range)headers['Content-Range']=`bytes ${range.offset}-${range.offset+range.length-1}/${row.size}`;
   return new Response(object.body,{status:range?206:200,headers});
  }
  if(request.method!=='POST')return json({error:'Método inválido.'},405);
  if(request.headers.get('Origin')!==url.origin)return json({error:'Origem inválida.'},403);
  if(action==='init'){
   if(!request.headers.get('Content-Type')?.startsWith('application/json'))return json({error:'Formato inválido.'},415);
   const info=validateFile(await bodyJSON(request)),fileId=crypto.randomUUID(),key=`media/${owner}/${fileId}`,now=new Date().toISOString();
   const inserted=await db.prepare("INSERT INTO media_files(id,owner,object_key,name,mime,size,category,fingerprint,status,created_at,updated_at) SELECT ?,?,?,?,?,?,?,?,'pending',?,? WHERE (SELECT COALESCE(SUM(size),0) FROM media_files WHERE owner=? AND status NOT IN ('deleted','failed'))+?<=? AND (SELECT COUNT(*) FROM media_files WHERE owner=? AND status IN ('pending','completing'))<3 AND (SELECT COUNT(*) FROM media_files WHERE owner=? AND status NOT IN ('deleted','failed'))<1000").bind(fileId,owner,key,info.name,info.mime,info.size,info.category,info.fingerprint,now,now,owner,info.size,STORAGE_LIMIT,owner,owner).run();
   if(inserted.meta.changes!==1)return json({error:'Espaço ou limite de envios atingido. Cancele envios pendentes ou exclua arquivos.'},409);
   try{const upload=await bucket.createMultipartUpload(key,{httpMetadata:{contentType:info.mime}});await db.prepare('UPDATE media_files SET upload_id=? WHERE id=? AND owner=?').bind(upload.uploadId,fileId,owner).run();return json({id:fileId,part_size:PART_SIZE});}
   catch(error){await db.prepare("UPDATE media_files SET status='failed' WHERE id=? AND owner=?").bind(fileId,owner).run();throw error;}
  }
  const row:any=await db.prepare("SELECT * FROM media_files WHERE id=? AND owner=? AND status NOT IN ('deleted','failed')").bind(id,owner).first();if(!row)return json({error:'Arquivo não encontrado.'},404);
  if(action==='status'){const parts=await db.prepare('SELECT part_number,etag,size FROM media_parts WHERE file_id=? ORDER BY part_number').bind(id).all();return json({...safeFile(row),parts:parts.results,part_size:PART_SIZE});}
  if(action==='part'){
   if(row.status!=='pending'||!row.upload_id)return json({error:'Este envio não aceita novas partes.'},409);
   if(!request.headers.get('Content-Type')?.startsWith('application/octet-stream'))return json({error:'Formato de envio inválido.'},415);
   const number=Number(url.searchParams.get('part')),size=expectedPart(row.size,number);
   if(Number(request.headers.get('Content-Length'))!==size)return json({error:'Tamanho da parte inválido.'},400);
   const bytes=await limitedBody(request,size,true);if(number===1&&!validSignature(row.mime,bytes))return json({error:'O conteúdo não corresponde ao formato do arquivo.'},400);
   const part=await bucket.resumeMultipartUpload(row.object_key,row.upload_id).uploadPart(number,bytes);
   const inserted=await db.prepare("INSERT INTO media_parts(file_id,part_number,etag,size) SELECT id,?,?,? FROM media_files WHERE id=? AND owner=? AND status='pending' ON CONFLICT(file_id,part_number) DO UPDATE SET etag=excluded.etag,size=excluded.size").bind(number,part.etag,size,id,owner).run();
   if(inserted.meta.changes!==1)return json({error:'O envio foi cancelado ou concluído.'},409);return json({part:number});
  }
  if(action==='complete'){
   if(row.status==='ready')return json({ok:true});if(!['pending','completing'].includes(row.status)||!row.upload_id)return json({error:'Envio indisponível.'},409);
   const parts=await db.prepare('SELECT part_number,etag,size FROM media_parts WHERE file_id=? ORDER BY part_number').bind(id).all();
   if(parts.results.length!==Math.ceil(row.size/PART_SIZE)||parts.results.some((p:any,i:number)=>p.part_number!==i+1||p.size!==expectedPart(row.size,i+1)))return json({error:'Envio incompleto. Retome as partes pendentes.'},409);
   await db.prepare("UPDATE media_files SET status='completing',updated_at=? WHERE id=? AND owner=? AND status='pending'").bind(new Date().toISOString(),id,owner).run();
   try{const existing=await bucket.head(row.object_key);if(!existing)await bucket.resumeMultipartUpload(row.object_key,row.upload_id).complete(parts.results.map((p:any)=>({partNumber:p.part_number,etag:p.etag})));
    const object=await bucket.head(row.object_key);if(!object||object.size!==row.size)throw Error('Tamanho final divergente. Cancele o envio e tente novamente.');
    const ready=await db.prepare("UPDATE media_files SET status='ready',updated_at=? WHERE id=? AND owner=? AND status='completing'").bind(new Date().toISOString(),id,owner).run();if(!ready.meta.changes){await bucket.delete(row.object_key);return json({error:'Envio cancelado durante a conclusão.'},409);}return json({ok:true});
   }catch(error){await db.prepare("UPDATE media_files SET status='pending' WHERE id=? AND owner=? AND status='completing'").bind(id,owner).run();throw error;}
  }
  if(action==='delete'){
   await db.prepare("UPDATE media_files SET status='deleting' WHERE id=? AND owner=?").bind(id,owner).run();
   if(row.upload_id&&['pending','completing'].includes(row.status)){try{await bucket.resumeMultipartUpload(row.object_key,row.upload_id).abort()}catch{/* May already have completed; delete the object below. */}}
   await bucket.delete(row.object_key);
   await db.batch([db.prepare('DELETE FROM media_parts WHERE file_id=?').bind(id),db.prepare("UPDATE media_files SET status='deleted',upload_id=NULL,updated_at=? WHERE id=? AND owner=?").bind(new Date().toISOString(),id,owner)]);
   return json({ok:true});
  }
  return json({error:'Ação inválida.'},400);
 }catch(error){console.error('Falha na biblioteca de arquivos',error instanceof Error?error.message:'erro');return json({error:error instanceof Error?error.message:'Não foi possível concluir o arquivo.'},400);}
}
export const GET=handle;
export const POST=handle;
