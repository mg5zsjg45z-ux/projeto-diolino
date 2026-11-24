// Cloud-specific features; personal records are fetched only after authentication.
const more=el('section',undefined,'hidden');more.id='more';$('app').append(more);
const moreButton=el('button','Mais');moreButton.dataset.page='more';moreButton.onclick=()=>show('more').catch(failure);$('nav').append(moreButton);
const cloudShow=show;
show=async function(next){more.classList.toggle('hidden',next!=='more');if(next!=='more')return cloudShow(next);page='more';for(const id of ['overview','routine','records','calculator','planning'])$(id).classList.add('hidden');document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.page==='more'));$('area-label').textContent='BIBLIOTECA · IMPRESSÃO · DADOS';$('title').textContent='Ferramentas';await renderMore();};
function download(value,name,type='application/json'){let a=el('a');a.href=URL.createObjectURL(new Blob([value],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
let library;
async function renderMore(){
  more.replaceChildren();
  const bible=el('div',undefined,'card');bible.append(el('h2','Biblioteca bíblica'),el('p','Leitura em versões autorizadas nos leitores online. Seus estudos ficam nos Registros.','muted'));
  library ||= await api('/api/library');
  const version=el('select'),book=el('select'),chapter=el('input');chapter.type='number';chapter.min=1;chapter.value=1;
  for(const [code,[name]]of Object.entries(library.versions)){const o=el('option',code+' · '+name);o.value=code;version.append(o);}
  library.books.forEach(([name],i)=>{const o=el('option',name);o.value=i;book.append(o);});book.value=42;
  const update=()=>{chapter.max=library.books[book.value][2];chapter.value=1;};book.onchange=update;update();
  for(const [label,input]of [['Versão',version],['Livro',book],['Capítulo',chapter]]){const l=el('label',label);l.append(input);bible.append(l);}
  const reference=()=>{let b=library.books[book.value],n=Number(chapter.value);if(!Number.isInteger(n)||n<1||n>b[2])throw Error('Capítulo inválido.');return {text:b[0]+' '+n+' · '+version.value,url:version.value==='ACF'?'https://www.bibliaonline.com.br/acf/'+encodeURIComponent(b[3])+'/'+n:'https://www.bible.com/pt/bible/'+library.versions[version.value][1]+'/'+b[1]+'.'+n+'.'+version.value};};
  const read=el('button','Abrir leitura','primary');read.onclick=()=>{try{window.open(reference().url,'_blank','noopener,noreferrer')}catch(e){failure(e)}};
  const record=el('button','Registrar estudo');record.onclick=()=>{try{let r=reference();openEditor('bible',{date:day(),passage:r.text,notes:r.url});}catch(e){failure(e)}};
  let actions=el('div',undefined,'row');actions.append(read,record);bible.append(actions);more.append(bible);
  const print=el('div',undefined,'card');print.append(el('h2','Relatórios e planners'));
  let start=el('input'),end=el('input'),template=el('select');start.type=end.type='date';start.value=day().slice(0,8)+'01';end.value=day();
  for(const [key,label]of [['report','Relatório dos registros'],['daily','Planner diário'],['weekly','Planner semanal'],['monthly','Planner mensal'],['bundle','Caderno semanal + sete dias']]){let o=el('option',label);o.value=key;template.append(o);}
  for(const [label,input]of [['Modelo',template],['Início / data de referência',start],['Fim do relatório',end]]){let l=el('label',label);l.append(input);print.append(l);}
  let areas=el('details');areas.append(el('summary','Áreas incluídas no relatório'));const selections=[];
  for(const [kind,spec]of Object.entries(schema)){let l=el('label',undefined,'check'),c=el('input');c.type='checkbox';c.checked=true;selections.push([kind,c]);l.append(c,el('span',spec.label));areas.append(l);}print.append(areas);
  const showPrint=el('button','Preparar impressão / PDF','primary');showPrint.onclick=async()=>{showPrint.disabled=true;try{if(!start.value||!end.value||end.value<start.value)throw Error('Confira as datas.');if(template.value==='report'&&(Date.parse(end.value)-Date.parse(start.value))/86400000>365)throw Error('Selecione até 366 dias.');let state=await api('/api/export');preparePrint(state,template.value,start.value,end.value,selections.filter(([,c])=>c.checked).map(([k])=>k));}catch(e){failure(e)}finally{showPrint.disabled=false}};print.append(showPrint,el('p','A4 · escolha Imprimir ou Salvar PDF no navegador. Planners em branco, com checagem dos três pilares e cuidados diários.','muted'));more.append(print);
  const data=el('div',undefined,'card');data.append(el('h2','Seus dados'),el('p','Troque registros com o Windows por arquivo. Confira as diferenças antes de importar. A troca manual não é automática.','muted'));
  const exp=el('button','Exportar backup JSON');exp.onclick=async()=>{try{download(JSON.stringify(await api('/api/export'),null,2),'diolino-'+day()+'.json')}catch(e){failure(e)}};
  const file=el('input');file.type='file';file.accept='.json,application/json';file.setAttribute('aria-label','Arquivo de migração Diolino');
  const imp=el('button','Importar dados');imp.onclick=async()=>{if(!file.files[0])return notice('Selecione um arquivo Diolino.');if(!confirm('Importar os registros deste arquivo para sua conta online? A importação inicial só funciona quando a conta está vazia.'))return;imp.disabled=true;try{if(file.files[0].size>1800000)throw Error('Arquivo acima do limite desta versão.');await api('/api/import',JSON.parse(await file.files[0].text()));notice('Importação concluída.');file.value='';}catch(e){failure(e)}finally{imp.disabled=false}};
  data.append(exp,el('p','Importação inicial: aceita backup JSON do site ou arquivo preparado pelo exportador do aplicativo. Não aceita o banco SQLite diretamente.','muted'),file,imp);more.append(data);
  await manualSyncControls(data);
  const limits=el('div',undefined,'notice');limits.textContent='Disponível pela internet, sem depender do PC. A sincronização automática com iCloud e as notificações do Windows permanecem no aplicativo local. Para escrever por voz, use o ditado do teclado do iPhone. O site não cria alarmes no Relógio.';more.append(limits);
}
async function manualSyncControls(host){
 const section=el('section');section.append(el('h3','Troca manual com o Windows'),el('p','1. Exporte o arquivo no Windows em Dados e backup. 2. Confira e importe aqui. 3. Exporte deste site e importe no Windows para devolver as alterações e os vínculos.','muted'));
 const exp=el('button','Exportar troca para o Windows');exp.onclick=async()=>{try{download(JSON.stringify(await api('/api/sync/export'),null,2),'diolino-troca-site-'+day()+'.json')}catch(e){failure(e)}};
 const file=el('input');file.type='file';file.accept='.json,application/json';file.setAttribute('aria-label','Arquivo de troca manual');
 const preview=el('button','Conferir arquivo','primary'),results=el('div');results.setAttribute('aria-live','polite');
 preview.onclick=async()=>{preview.disabled=true;results.replaceChildren();try{
  if(!file.files[0])throw Error('Selecione o arquivo de troca manual.');if(file.files[0].size>1800000)throw Error('Arquivo acima de 1,8 MB.');
  const incoming=JSON.parse(await file.files[0].text()),plan=await api('/api/sync/preview',{file:incoming}),choices={};
  results.append(el('p',`${plan.counts.new} novos · ${plan.counts.same} iguais · ${plan.counts.conflicts} diferenças · ${plan.counts.blocked} bloqueados`));
  results.append(el('p','Diferenças mantêm a versão do site até você escolher usar o arquivo. Bloqueados são registros excluídos neste destino ou com associação indisponível.','muted'));
  for(const c of plan.conflicts){const box=el('details'),title=c.incoming.title||c.incoming.topic||c.incoming.passage||c.incoming.name||c.incoming.date||c.key;box.append(el('summary',(schema[c.kind]?.label||c.kind)+' · '+title));const local={...c.local};delete local.sync_ids;delete local.id;delete local.deleted_at;box.append(el('h4','No site'),el('pre',JSON.stringify(local,null,2)),el('h4','No arquivo'),el('pre',JSON.stringify(c.incoming,null,2)));const label=el('label','Versão a manter'),select=el('select');for(const [value,text]of [['keep','Manter no site'],['incoming','Usar versão do arquivo'],...(c.possible?[['separate','Criar como registro separado']]:[])]){const option=el('option',text);option.value=value;select.append(option)}select.onchange=()=>{choices[c.key]=select.value};label.append(select);box.append(label);results.append(box);}
  const apply=el('button','Criar backup e confirmar importação','primary');apply.onclick=async()=>{apply.disabled=true;try{
   const before=await api('/api/export');download(JSON.stringify(before,null,2),'diolino-antes-da-troca-'+Date.now()+'.json');
   const result=await api('/api/sync/apply',{file:incoming,revision:plan.revision,choices});
   results.replaceChildren(el('p',`Importação concluída: ${result.counts.new} novo(s), ${result.counts.updated} atualizado(s). Exporte a troca para devolver ao Windows.`));
   file.value='';
  }catch(e){failure(e);apply.disabled=false}};results.append(apply);
 }catch(e){failure(e)}finally{preview.disabled=false}};
 section.append(exp,file,preview,results,el('p','Inclui saúde e anotações pessoais em texto simples. Guarde o JSON em local privado. Anexos, exclusões, credenciais, preferências e o relógio ativo do Pomodoro não são transferidos. Nenhum item ausente no arquivo é apagado.','muted'));host.append(section);
}
function preparePrint(state,kind,start,end,kinds){
  $('print-root')?.remove();const root=el('section');root.id='print-root';const active=k=>(state.records[k]||[]).filter(r=>!r.deleted_at);
  function page(title,subtitle){let p=el('article',undefined,'print-page');p.append(el('small','DIOLINO / CONTROLE PESSOAL'),el('h1',title),el('p',subtitle));root.append(p);return p;}
  function checks(p){p.append(el('p','□ Medicina · 60 min     □ Exercício · 40 min     □ Estudo bíblico'),el('p','Boca: □ □ □     Banho: □ □     Medicação: □ □'),el('p','Água: ______ mL / meta pessoal ______ mL'));}
  function lines(p,title,n=6){p.append(el('h3',title));for(let i=0;i<n;i++)p.append(el('div',' ','print-line'));}
  function daily(d){let p=page('Planejamento diário',dateLabel(d));checks(p);lines(p,'Prioridades / horários',7);lines(p,'Registros / observações',5);}
  function weekly(){let p=page('Planejamento semanal',dateLabel(start));for(let i=0;i<7;i++){let d=new Date(start+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+i);p.append(el('h3',dateLabel(d.toISOString().slice(0,10))));checks(p);p.append(el('div',' ','print-line'));}}
  if(kind==='daily')daily(start);
  else if(kind==='weekly')weekly();
  else if(kind==='bundle'){weekly();for(let i=0;i<7;i++){let d=new Date(start+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+i);daily(d.toISOString().slice(0,10));}}
  else if(kind==='monthly'){let p=page('Planejamento mensal',start.slice(0,7)),d=new Date(start.slice(0,7)+'-01T12:00:00Z'),table=el('table');let head=el('tr');for(let label of ['Dia','Medicina','Exercício','Bíblia','Planejamento'])head.append(el('th',label));table.append(head);let month=d.getUTCMonth();while(d.getUTCMonth()===month){let tr=el('tr');for(let val of [String(d.getUTCDate()),'□','□','□',''])tr.append(el('td',val));table.append(tr);d.setUTCDate(d.getUTCDate()+1);}p.append(table);lines(p,'Objetivos do mês',3);}
  else{page('Relatório de registros',dateLabel(start)+' a '+dateLabel(end));for(let k of kinds){let records=active(k).filter(r=>{let day=r.date;if(k==='sets')day=active('workout').find(w=>w.id===r.workout_id)?.date;if(k==='plan_steps')day=r.due_date;if(k==='plans')return (!r.start_date||r.start_date<=end)&&(!r.end_date||r.end_date>=start);return !day||day>=start&&day<=end;});let p=el('article',undefined,'report-section');p.append(el('h2',schema[k].label));if(!records.length)p.append(el('p','–'));for(let r of records){let dl=el('dl');for(let f of schema[k].fields){dl.append(el('dt',f.label),el('dd',r[f.key]==null?'–':String(r[f.key])));}p.append(dl);}root.append(p);}}
  document.body.append(root);window.print();
}
