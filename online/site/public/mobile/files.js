// Private file library. File bytes never enter the account JSON or localStorage.
let filesOpen=false,filesSnapshot=null,fileUpload={running:false,done:0,total:0,message:'',stop:false,id:null,controller:null},paintFileUpload=()=>{};
const filesApi=async(action,data,id)=>{const response=await fetch('/api/files'+(action?'?action='+encodeURIComponent(action)+(id?'&id='+encodeURIComponent(id):''):''),{credentials:'same-origin',...(action?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data||{})}:{})});let body;try{body=await response.json()}catch{throw Error('Resposta indisponível. Verifique a conexão e retome o envio.')}if(!response.ok)throw Error(body.error||'Não foi possível acessar seus arquivos.');return body;};
const fileSize=bytes=>bytes>=1024**3?(bytes/1024**3).toLocaleString('pt-BR',{maximumFractionDigits:2})+' GiB':bytes>=1024**2?(bytes/1024**2).toLocaleString('pt-BR',{maximumFractionDigits:1})+' MiB':Math.ceil(bytes/1024)+' KiB';
const filesSection=el('section',undefined,'hidden');filesSection.id='files';$('app').append(filesSection);
const filesNavigation=el('button');filesNavigation.dataset.page='files';filesNavigation.setAttribute('aria-label','Biblioteca de arquivos');filesNavigation.append(outlineGlyph('database'),el('span','Biblioteca'));filesNavigation.onclick=()=>show('files').catch(failure);$('nav').insertBefore(filesNavigation,document.querySelector('nav button[data-page="more"]'));
const filesBaseShow=show;
show=async function(next){filesSection.classList.toggle('hidden',next!=='files');if(next!=='files')return filesBaseShow(next);page='files';for(const id of ['overview','routine','records','calculator','planning','more'])$(id).classList.add('hidden');document.querySelectorAll('nav button').forEach(button=>button.classList.toggle('active',button.dataset.page==='files'));$('area-label').textContent='ARQUIVOS PESSOAIS';$('title').textContent='Biblioteca de arquivos';await drawFileLibrary(filesSection);};

async function fingerprint(file){const data=new Blob([file.slice(0,65536),file.slice(Math.max(0,file.size-65536)),file.name+'|'+file.size+'|'+file.lastModified]);return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await data.arrayBuffer()))).map(n=>n.toString(16).padStart(2,'0')).join('');}
async function drawFileLibrary(host){
 disposeLibraryBrowser?.();host.replaceChildren();const card=el('div',undefined,'card');card.append(el('h2','Biblioteca de arquivos'),el('p','PDFs, vídeos, áudios, imagens e documentos. Acesso restrito à sua conta.','muted'));host.append(card);
 try{filesSnapshot=await filesApi('')}catch(error){card.append(el('p',error.message,'notice'));return}
 const info=filesSnapshot,usage=el('progress');usage.max=info.limit;usage.value=info.used;usage.setAttribute('aria-label','Espaço reservado e utilizado');card.append(el('p',fileSize(info.used)+' de '+fileSize(info.limit)+' reservados ou utilizados'),usage,el('p','Limite inicial do aplicativo: '+fileSize(info.max_file)+' por arquivo. Envios pendentes também reservam espaço.','muted'));
 const picker=el('input');picker.type='file';picker.accept='.pdf,.mp4,.m4v,.mov,.webm,.jpg,.jpeg,.png,.webp,.mp3,.m4a,.wav,.txt,.doc,.docx,.pptx,.xlsx';picker.setAttribute('aria-label','Selecionar PDF, vídeo ou outro arquivo');
 const category=el('select');category.setAttribute('aria-label','Categoria do arquivo');for(const label of info.categories)category.append(el('option',label));const send=el('button','Enviar arquivo','primary'),pause=el('button','Pausar envio'),status=el('p',undefined,'file-upload-status'),progress=el('progress');progress.setAttribute('aria-label','Progresso do envio');status.setAttribute('role','status');
 const uploader=el('details',undefined,'library-upload');uploader.append(el('summary','Enviar arquivos'),picker,category,send,pause,el('p','Mantenha esta aba aberta durante o envio. Se a conexão cair, escolha Retomar e selecione o mesmo arquivo. O envio usa partes pequenas. O backup JSON dos registros não inclui os arquivos; use Baixar para guardar cópias.','muted'));card.append(uploader,progress,status);
 let resumeFile=null;
 paintFileUpload=()=>{if(!host.isConnected)return;progress.max=fileUpload.total||1;progress.value=fileUpload.done;progress.hidden=!fileUpload.total;pause.hidden=!fileUpload.running;send.disabled=fileUpload.running;picker.disabled=fileUpload.running;category.disabled=fileUpload.running;status.textContent=fileUpload.message;};paintFileUpload();
 pause.onclick=()=>{fileUpload.stop=true;fileUpload.controller?.abort();};
 picker.onchange=()=>{if(!resumeFile)return;upload(picker.files[0],resumeFile).catch(failure)};
 send.onclick=()=>upload(picker.files[0],resumeFile).catch(failure);
 async function upload(file,resume){
  if(fileUpload.running)return;if(!file)return notice('Selecione um arquivo.');if(file.size<1||file.size>info.max_file)return notice('O arquivo deve ter até '+fileSize(info.max_file)+'.');
  fileUpload={running:true,done:0,total:file.size,message:'Preparando '+file.name+'…',stop:false,id:resume?.id||null,controller:null};paintFileUpload();
  try{
   const hash=await fingerprint(file);let pending;
   if(resume){if(file.name!==resume.name||file.size!==resume.size||hash!==resume.fingerprint)throw Error('Selecione o mesmo arquivo usado no envio original.');pending=await filesApi('status',{},resume.id);}
   else{const created=await filesApi('init',{name:file.name,size:file.size,category:category.value,fingerprint:hash});fileUpload.id=created.id;pending={id:created.id,part_size:created.part_size,parts:[]};}
   const parts=new Map(pending.parts.map(p=>[p.part_number,p.size]));fileUpload.done=Array.from(parts.values()).reduce((sum,n)=>sum+n,0);paintFileUpload();
   for(let number=1;number<=Math.ceil(file.size/pending.part_size);number++){
    if(fileUpload.stop)throw Error('Envio pausado. Use Retomar para continuar.');if(parts.has(number))continue;
    const start=(number-1)*pending.part_size,blob=file.slice(start,Math.min(file.size,start+pending.part_size));
    fileUpload.message='Enviando '+file.name+' · '+Math.floor(fileUpload.done/file.size*100)+'%';paintFileUpload();
    let sent=false;
    for(let attempt=0;attempt<3&&!sent;attempt++){
     if(fileUpload.stop)throw Error('Envio pausado. Use Retomar para continuar.');
     fileUpload.controller=new AbortController();
     try{const response=await fetch('/api/files?action=part&id='+encodeURIComponent(fileUpload.id)+'&part='+number,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/octet-stream'},body:blob,signal:fileUpload.controller.signal});const answer=await response.json();if(!response.ok){if(response.status<500)throw Object.assign(Error(answer.error||'Parte recusada.'),{permanent:true});throw Error(answer.error||'Conexão temporariamente indisponível.')}sent=true;}
     catch(error){if(fileUpload.stop)throw Error('Envio pausado. Use Retomar para continuar.');if(error.permanent||attempt===2)throw error;fileUpload.message='Tentando reconectar…';paintFileUpload();await new Promise(resolve=>setTimeout(resolve,(attempt+1)*1000));}
    }
    fileUpload.done+=blob.size;paintFileUpload();
   }
   fileUpload.message='Concluindo e verificando o arquivo…';paintFileUpload();await filesApi('complete',{},fileUpload.id);fileUpload.message='Arquivo enviado: '+file.name;picker.value='';resumeFile=null;
  }catch(error){fileUpload.message=error.message||'Envio interrompido. Você pode retomá-lo.';}
  finally{fileUpload.running=false;fileUpload.controller=null;paintFileUpload();if(page==='files')await show('files');}
 }
 const browser=el('div');card.append(browser);drawLibraryBrowser(browser,info,file=>{resumeFile=file;uploader.open=true;picker.value='';picker.click()});
}

function previewPrivateFile(file){
 const dialog=el('dialog',undefined,'file-preview'),heading=el('h2',file.name),close=el('button','Fechar'),url='/api/files?id='+encodeURIComponent(file.id);close.onclick=()=>dialog.close();const tools=el('div',undefined,'file-preview-toolbar'),expand=el('button','Tela cheia');tools.append(heading,expand,close);dialog.append(tools);expand.onclick=()=>{if(document.fullscreenElement)document.exitFullscreen?.().catch(()=>{});else dialog.requestFullscreen?.().catch(()=>notice('Tela cheia indisponível neste navegador.'))};
 let view;if(file.mime.startsWith('video/')){view=el('video');view.controls=true;view.playsInline=true;view.preload='metadata';}
 else if(file.mime.startsWith('audio/')){view=el('audio');view.controls=true;view.preload='metadata';}
 else if(file.mime.startsWith('image/')){view=el('img');view.alt=file.name;}
 else if(file.name.toLowerCase().endsWith('.docx')){view=el('div',undefined,'word-preview');}
 else if(file.mime==='text/plain'){view=el('pre',undefined,'text-preview');}
 else if(file.mime==='application/pdf'){view=el('div',undefined,'pdf-pages');view.setAttribute('aria-label','PDF: '+file.name);}
 if(view){if(/^(video|audio|image)\//.test(file.mime))view.src=url;dialog.append(view)}else dialog.append(el('p',file.mime==='application/msword'?'O formato antigo DOC precisa ser convertido para DOCX ou PDF no Word ou LibreOffice para leitura aqui. Baixe o original abaixo.':'Baixe este documento para abrir no aplicativo apropriado.'));
 const download=el('a','Abrir / baixar arquivo','file-download');download.href=url+'&download=1';dialog.append(download,el('p',file.mime.startsWith('video/')||file.mime.startsWith('audio/')?'A reprodução depende dos formatos compatíveis com seu navegador.':'A prévia serve para leitura; use Baixar para preservar o arquivo original.','muted'));dialog.addEventListener('close',()=>{if(view){if(view.pause)view.pause();view.removeAttribute('src')}dialog.remove()});document.body.append(dialog);dialog.showModal();close.focus();if(file.mime==='application/pdf')renderPrivatePDF(view,url,dialog);else if(file.name.toLowerCase().endsWith('.docx'))renderPrivateWord(view,url,dialog,file);else if(file.mime==='text/plain'){if(file.size>2*1024*1024)view.textContent='Texto acima de 2 MiB. Use Baixar.';else fetch(url,{credentials:'same-origin'}).then(r=>{if(!r.ok)throw Error();return r.text()}).then(text=>{if(dialog.open)view.textContent=text}).catch(()=>{view.textContent='Não foi possível ler o texto.'})}if(file.mime.startsWith('video/')){const speed=el('select');speed.setAttribute('aria-label','Velocidade de reprodução');for(const value of [.5,.75,1,1.25,1.5,1.75,2]){const option=el('option',value+'×');option.value=value;speed.append(option)}speed.value='1';speed.onchange=()=>{view.playbackRate=Number(speed.value)};dialog.insertBefore(speed,view);view.addEventListener('error',()=>{dialog.append(el('p','Este vídeo não é compatível ou não pôde ser carregado. Prefira MP4 com H.264/AAC ou baixe o original.','notice'))},{once:true})}
}
window.addEventListener('beforeunload',event=>{if(fileUpload.running){event.preventDefault();event.returnValue=''}});

async function renderPrivatePDF(host,url,dialog){
 const status=el('p','Carregando PDF…','muted'),tools=el('div',undefined,'row'),canvas=el('canvas');host.append(status,tools,canvas);let documentPDF,task,current=1,rendering=false,closed=false,zoom=1;
 dialog.addEventListener('close',()=>{closed=true;task?.destroy();});
 try{
  const pdfjs=await import('/pdfjs/pdf.mjs');if(closed)return;pdfjs.GlobalWorkerOptions.workerSrc='/pdfjs/pdf.worker.mjs';
  task=pdfjs.getDocument({url,withCredentials:true,isEvalSupported:false,enableXfa:false,cMapUrl:'/pdfjs/cmaps/',cMapPacked:true,standardFontDataUrl:'/pdfjs/standard_fonts/',wasmUrl:'/pdfjs/wasm/',disableAutoFetch:true,disableStream:true,rangeChunkSize:65536});
  documentPDF=await task.promise;if(closed)return;
  const previous=el('button','‹ Página'),next=el('button','Página ›');const pageInput=el('input'),zoomInput=el('select');pageInput.type='number';pageInput.min='1';pageInput.max=String(documentPDF.numPages);pageInput.value='1';pageInput.setAttribute('aria-label','Ir para página do PDF');zoomInput.setAttribute('aria-label','Zoom do PDF');for(const [value,label]of [[1,'Ajustar à largura'],[1.25,'125%'],[1.5,'150%'],[2,'200%']]){const option=el('option',label);option.value=value;zoomInput.append(option)}tools.append(previous,pageInput,next,zoomInput);const draw=async()=>{if(rendering||closed)return;rendering=true;previous.disabled=next.disabled=pageInput.disabled=zoomInput.disabled=true;try{const page=await documentPDF.getPage(current);if(closed)return;const natural=page.getViewport({scale:1}),width=Math.max(240,Math.min(host.clientWidth||900,1100)),viewport=page.getViewport({scale:width/natural.width*zoom});canvas.style.width=width*zoom+'px';canvas.width=viewport.width;canvas.height=viewport.height;await page.render({canvasContext:canvas.getContext('2d'),viewport,canvas}).promise;status.textContent='Página '+current+' de '+documentPDF.numPages;pageInput.value=String(current);}catch(error){if(!closed)status.textContent='Não foi possível exibir esta página. Use Baixar para abrir o PDF.'}finally{rendering=false;pageInput.disabled=zoomInput.disabled=false;previous.disabled=current===1;next.disabled=current===documentPDF.numPages}};
  pageInput.onchange=()=>{const value=Number(pageInput.value);if(!rendering&&Number.isInteger(value)&&value>=1&&value<=documentPDF.numPages){current=value;draw()}else pageInput.value=String(current)};zoomInput.onchange=()=>{zoom=Number(zoomInput.value);draw()};previous.onclick=()=>{if(current>1){current--;draw()}};next.onclick=()=>{if(current<documentPDF.numPages){current++;draw()}};await draw();
 }catch(error){if(!closed)status.textContent='Prévia indisponível. Use Baixar para abrir o PDF no leitor do dispositivo.'}
}
