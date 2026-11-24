// Local visual preferences and navigation; no personal records are stored here.
const outlineFiles={overview:'house',routine:'list-checks',planning:'notebook-pen',records:'database',more:'palette'};
function outlineGlyph(name){const span=el('span',undefined,'outline-glyph');span.style.setProperty('--icon-url',`url('/art/icons/${name}.svg')`);span.setAttribute('aria-hidden','true');return span;}
document.querySelectorAll('nav button[data-page]').forEach(button=>{const file=outlineFiles[button.dataset.page];if(file){const label=button.textContent;button.replaceChildren(outlineGlyph(file),el('span',label));}});
const brand=$('app').querySelector('.brand'),lockup=brand.parentElement;
lockup.classList.add('brand-lockup');const monogram=el('span','D','brand-monogram');monogram.setAttribute('aria-hidden','true');brand.before(monogram);
let ornamentMode='crafted';try{ornamentMode=localStorage.getItem('diolino-ornaments')==='plain'?'plain':'crafted';}catch{}
document.documentElement.dataset.ornaments=ornamentMode;
function setOrnaments(value){document.documentElement.dataset.ornaments=value==='plain'?'plain':'crafted';try{localStorage.setItem('diolino-ornaments',document.documentElement.dataset.ornaments);}catch{}}
const previousMore=renderMore;
renderMore=async function(){await previousMore();const card=el('div',undefined,'card appearance-card');card.append(el('h2','Aparência'),el('p','O acabamento é ajustado neste navegador.','muted'));const label=el('label','Acabamento gráfico'),select=el('select');for(const [value,text]of [['crafted','Gravura · detalhes finos'],['plain','Discreto · sem ornamentos']]){const option=el('option',text);option.value=value;select.append(option);}select.value=document.documentElement.dataset.ornaments;select.onchange=()=>setOrnaments(select.value);label.append(select);card.append(label);more.prepend(card);};

// Keep required fields in view; all existing field ids and save logic are retained.
const completeEditor=openEditor;
openEditor=function(kind,values){
  completeEditor(kind,values);
  const spec=schema[kind],optional=el('details',undefined,'optional-fields');optional.append(el('summary','Detalhes opcionais'));
  let count=0,hasValues=false;
  for(const field of spec.fields){
    const input=$('f-'+field.key);if(!input)continue;const label=input.previousElementSibling;
    if(!field.required&&field.key!=='date'){
      optional.append(label,input);count++;if(values[field.key]!==null&&values[field.key]!==undefined&&values[field.key]!=='')hasValues=true;
    }
  }
  if(count){optional.open=hasValues;$('fields').append(optional);}
  const duration=$('f-duration_min');
  if(duration&&!editing.readonly&&['study','workout'].includes(kind)){
    const shortcuts=el('div',undefined,'duration-shortcuts');shortcuts.setAttribute('role','group');shortcuts.setAttribute('aria-label','Preencher duração em minutos');
    for(const minutes of [15,30,40,60]){const button=el('button',minutes+' min');button.type='button';button.onclick=()=>{duration.value=minutes;duration.dispatchEvent(new Event('input',{bubbles:true}));duration.focus();};shortcuts.append(button);}
    duration.after(shortcuts);
  }
};

const commands=el('dialog',undefined,'command-dialog');commands.id='command-menu';
const commandHeading=el('h2','Abrir ou registrar');commandHeading.id='command-heading';commands.setAttribute('aria-labelledby',commandHeading.id);
const commandInput=el('input');commandInput.type='search';commandInput.placeholder='Buscar tela ou ação…';commandInput.setAttribute('aria-label','Buscar tela ou ação');
const commandResults=el('div',undefined,'command-results'),commandClose=el('button','Fechar');commandClose.type='button';commandClose.onclick=()=>commands.close();
commands.append(commandHeading,commandInput,commandResults,commandClose);document.body.append(commands);let commandOpener;
function drawCommands(){const query=commandInput.value.toLocaleLowerCase('pt-BR');commandResults.replaceChildren();const items=[...Array.from(document.querySelectorAll('nav button[data-page]')).map(button=>({label:'Abrir '+button.textContent,run:()=>show(button.dataset.page).catch(failure)})),{label:'Registrar água',run:()=>openEditor('hydration',{drink:'Água',is_water:'Sim'})},{label:'Registrar peso',run:()=>openEditor('body',{})},{label:'Registrar estudo médico',run:()=>openEditor('study',{})},{label:'Registrar treino',run:()=>openEditor('workout',{})}];let count=0;for(const item of items.filter(item=>item.label.toLocaleLowerCase('pt-BR').includes(query))){const button=el('button',item.label);button.type='button';button.onclick=()=>{commands.close();item.run();};commandResults.append(button);count++;}if(!count)commandResults.append(el('p','Nenhuma ação encontrada.','muted'));}
function openCommands(){if(document.querySelector('dialog[open]'))return;commandOpener=document.activeElement;commandInput.value='';drawCommands();commands.showModal();commandInput.focus();}
commands.addEventListener('close',()=>{if(commandOpener?.isConnected)commandOpener.focus();});commandInput.oninput=drawCommands;
document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'&&!document.querySelector('dialog[open]')){event.preventDefault();openCommands();}});
const searchButton=el('button','Buscar','quiet command-launch');searchButton.setAttribute('aria-label','Buscar tela ou ação. Atalho Control K');searchButton.onclick=openCommands;$('app').querySelector('header').insertBefore(searchButton,$('theme-switch'));

// Reuse the daily checks; the compact presentation retains explicit confirmations.
const dailyOverview=overview;
overview=async function(){await dailyOverview();if(page!=='routine')return;const first=$('routine').querySelector('.card');first?.classList.add('daily-pillars');};
