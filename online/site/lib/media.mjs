export const PART_SIZE=8*1024*1024;
export const MAX_FILE_SIZE=500*1024*1024;
export const STORAGE_LIMIT=10*1024*1024*1024;
export const CATEGORIES=['Medicina','Bíblia','Pessoal','Outros'];
const TYPES={doc:'application/msword',pdf:'application/pdf',mp4:'video/mp4',m4v:'video/mp4',mov:'video/quicktime',webm:'video/webm',jpg:'image/jpeg',jpeg:'image/jpeg',png:'image/png',webp:'image/webp',mp3:'audio/mpeg',m4a:'audio/mp4',wav:'audio/wav',txt:'text/plain',docx:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',pptx:'application/vnd.openxmlformats-officedocument.presentationml.presentation',xlsx:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'};
export function validateFile(input){
 if(!input||typeof input.name!=='string'||!input.name.trim()||input.name.length>200||/[\x00-\x1f\x7f/\\]/.test(input.name))throw Error('Nome de arquivo inválido.');
 const name=input.name.trim(),ext=name.split('.').at(-1).toLowerCase(),mime=TYPES[ext];if(!mime)throw Error('Formato não aceito. Use PDF, vídeo, áudio, imagem ou documento Office.');
 if(!Number.isSafeInteger(input.size)||input.size<1||input.size>MAX_FILE_SIZE)throw Error('Selecione um arquivo entre 1 byte e 500 MiB.');
 if(!CATEGORIES.includes(input.category))throw Error('Categoria inválida.');
 if(typeof input.fingerprint!=='string'||!/^[a-f0-9]{64}$/.test(input.fingerprint))throw Error('Identificação do arquivo inválida.');
 return {name,mime,size:input.size,category:input.category,fingerprint:input.fingerprint};
}
export function expectedPart(size,number){
 if(!Number.isSafeInteger(number)||number<1||number>Math.ceil(size/PART_SIZE))throw Error('Parte de arquivo inválida.');
 return Math.min(PART_SIZE,size-(number-1)*PART_SIZE);
}
export function validSignature(mime,bytes){
 const text=(start,n)=>String.fromCharCode(...bytes.slice(start,start+n));
 if(mime==='application/msword')return [208,207,17,224,161,177,26,225].every((v,i)=>bytes[i]===v);
 if(mime==='application/pdf')return text(0,1024).includes('%PDF-');
 if(mime==='image/png')return [137,80,78,71,13,10,26,10].every((v,i)=>bytes[i]===v);
 if(mime==='image/jpeg')return bytes[0]===255&&bytes[1]===216&&bytes[2]===255;
 if(mime==='image/webp')return text(0,4)==='RIFF'&&text(8,4)==='WEBP';
 if(['video/mp4','video/quicktime','audio/mp4'].includes(mime))return text(4,4)==='ftyp';
 if(mime==='video/webm')return [26,69,223,163].every((v,i)=>bytes[i]===v);
 if(mime==='audio/wav')return text(0,4)==='RIFF'&&text(8,4)==='WAVE';
 if(mime==='audio/mpeg')return text(0,3)==='ID3'||bytes[0]===255&&(bytes[1]&224)===224;
 if(mime.includes('openxmlformats'))return text(0,2)==='PK';
 return mime==='text/plain'&&!bytes.slice(0,1024).includes(0);
}
export function byteRange(header,size){
 if(!header)return null;
 const match=/^bytes=(\d*)-(\d*)$/.exec(header);
 if(!match||!match[1]&&!match[2])throw Error('Intervalo de leitura inválido.');
 let start,end;if(!match[1]){const suffix=Number(match[2]);if(!Number.isSafeInteger(suffix)||suffix<1)throw Error('Intervalo inválido.');start=Math.max(0,size-suffix);end=size-1;}
 else{start=Number(match[1]);end=match[2]?Math.min(Number(match[2]),size-1):size-1;}
 if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>=size||start<0||end<start)throw Error('Intervalo fora do arquivo.');
 return {offset:start,length:end-start+1};
}
export function safeFile(row){return Object.fromEntries(['id','name','mime','size','category','fingerprint','status','created_at','updated_at'].map(k=>[k,row[k]]));}
