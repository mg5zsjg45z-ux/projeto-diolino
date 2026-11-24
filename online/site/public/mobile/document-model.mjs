export const DOCX_PREVIEW_LIMIT=20*1024*1024;
// Inspect ZIP metadata before decompressing a DOCX in a disposable worker.
export function inspectDocx(buffer){
 const b=new Uint8Array(buffer),v=new DataView(buffer);if(b.length<22||b.length>DOCX_PREVIEW_LIMIT)throw Error('A prévia Word aceita DOCX de até 20 MiB. Baixe o original para documentos maiores.');
 let end=-1;for(let p=b.length-22;p>=Math.max(0,b.length-65557);p--)if(v.getUint32(p,true)===0x06054b50&&p+22+v.getUint16(p+20,true)===b.length){end=p;break;}
 if(end<0||v.getUint16(end+4,true)||v.getUint16(end+6,true))throw Error('Documento Word inválido ou formato ZIP não suportado.');
 const count=v.getUint16(end+10,true),length=v.getUint32(end+12,true),start=v.getUint32(end+16,true);if(count>2000||count===65535||start+length!==end)throw Error('Documento complexo demais para a prévia.');
 let cursor=start,total=0,word=false;const decoder=new TextDecoder();
 for(let i=0;i<count;i++){
  if(cursor+46>end||v.getUint32(cursor,true)!==0x02014b50)throw Error('Estrutura Word inválida.');
  const packed=v.getUint32(cursor+20,true),size=v.getUint32(cursor+24,true),n=v.getUint16(cursor+28,true),extra=v.getUint16(cursor+30,true),comment=v.getUint16(cursor+32,true);
  if(v.getUint16(cursor+8,true)&1||size===0xffffffff||packed===0xffffffff)throw Error('Documento criptografado ou ZIP64 não suportado.');
  total+=size;if(total>64*1024*1024||size>32*1024*1024||size>Math.max(1024*1024,packed*250))throw Error('Documento expandido grande demais para uma prévia segura.');
  if(cursor+46+n+extra+comment>end)throw Error('Estrutura Word incompleta.');
  if(decoder.decode(b.subarray(cursor+46,cursor+46+n))==='word/document.xml')word=true;
  cursor+=46+n+extra+comment;
 }
 if(!word||cursor!==end)throw Error('O arquivo não é um DOCX válido.');return {entries:count,expanded:total};
}
