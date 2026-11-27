import {useState} from 'react';
import {invoke,isTauri} from '@tauri-apps/api/core';
import {open,save} from '@tauri-apps/plugin-dialog';
import {flushLocalSections,reconcileWebSection} from './localSection';
import {localDay} from './data';
import {isBackupDate as isDate,isBackupTime as isTime} from './backupValidation.mjs';

const preferenceKeys=['diolino-theme','diolino-library','diolino-focus-settings','diolino-focus-timer','diolino-focus-sessions'];
const sectionKeys=[
 'diolino-workspace-v1','diolino-health-entries','diolino-health-goals','diolino-habits-v1',
 'diolino-habit-marks-v1','diolino-preview-reviews','diolino-bible-days','diolino-bible-notes',
 'diolino-food-entries','diolino-food-goals','diolino-food-date-goals','diolino-strength-plan','diolino-daily-tasks','diolino-caderno',
];
type Backup={createdAt:string;sections:Record<string,unknown>;preferences:Record<string,unknown>};
const isObject=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value);
const isString=(value:unknown):value is string=>typeof value==='string';
const isNumber=(value:unknown):value is number=>typeof value==='number'&&Number.isFinite(value);
const optionalString=(value:unknown)=>value===null||isString(value);
const optionalNumber=(value:unknown)=>value===null||isNumber(value);
type SectionObject=Record<string,unknown>;
const objectRows=(value:unknown):value is SectionObject[]=>Array.isArray(value)&&value.every(isObject);
const isAgenda=(row:Record<string,unknown>)=>typeof row.id==='number'&&isDate(row.date)&&isTime(row.time)&&isString(row.title)&&optionalNumber(row.duration_min)&&isString(row.state);
const isStudy=(row:Record<string,unknown>)=>typeof row.id==='number'&&isDate(row.date)&&isTime(row.time)&&isString(row.topic)&&isNumber(row.duration_min)&&isString(row.format)&&optionalString(row.source)&&optionalString(row.learning)&&optionalString(row.notes)&&optionalString(row.attachment_path)&&optionalString(row.attachment_name);
const validLocalSection=(key:string,value:unknown):boolean=>{
 if(key==='diolino-caderno')return isObject(value)&&isString(value.draft)&&objectRows(value.entries)&&value.entries.every(row=>isString(row.id)&&isString(row.text)&&!!row.text.trim());
 if(key==='diolino-workspace-v1')return isObject(value)&&objectRows(value.agenda)&&value.agenda.every(isAgenda)&&objectRows(value.tasks)&&value.tasks.every(row=>typeof row.id==='number'&&isString(row.title)&&isString(row.plan)&&isString(row.state)&&isString(row.priority)&&optionalString(row.due))&&objectRows(value.studies)&&value.studies.every(isStudy)&&objectRows(value.reviews)&&value.reviews.every(row=>isAgenda(row)&&(row.sourceStudy===undefined||isStudy(row.sourceStudy as Record<string,unknown>)));
 if(key==='diolino-health-entries')return objectRows(value)&&value.every(row=>typeof row.id==='number'&&isDate(row.date)&&optionalString(row.activity)&&optionalNumber(row.exerciseMin)&&optionalNumber(row.sleepHours)&&optionalNumber(row.weightKg)&&optionalString(row.notes)&&(row.source===undefined||row.source==='Meus registros'));
 if(key==='diolino-health-goals')return isObject(value)&&Object.keys(value).every(field=>field==='exerciseMin'||field==='sleepHours')&&optionalNumber(value.exerciseMin??null)&&optionalNumber(value.sleepHours??null);
 if(key==='diolino-habits-v1')return objectRows(value)&&value.every(row=>isString(row.id)&&isString(row.name)&&!!row.name.trim()&&isString(row.description)&&['daily','weekdays','weekends'].includes(String(row.frequency))&&isDate(row.createdAt));
 if(key==='diolino-habit-marks-v1')return isObject(value)&&Object.values(value).every(days=>isObject(days)&&Object.entries(days).every(([date,mark])=>isDate(date)&&['done','missed','skipped'].includes(String(mark))));
 if(key==='diolino-preview-reviews')return objectRows(value)&&value.every(row=>isAgenda(row)&&(row.sourceStudy===undefined||isStudy(row.sourceStudy as Record<string,unknown>)));
 if(key==='diolino-bible-days')return Array.isArray(value)&&value.every(isDate);
 if(key==='diolino-bible-notes')return objectRows(value)&&value.every(row=>['BPM','BLIVRE','BLT'].includes(String(row.edition))&&['book','bookName','chapter','verse','comment'].every(field=>isString(row[field]))&&typeof row.marked==='boolean');
 if(key==='diolino-food-entries')return objectRows(value)&&value.every(row=>isString(row.id)&&isDate(row.date)&&isNumber(row.code)&&isString(row.name)&&isNumber(row.grams)&&row.grams>0&&isObject(row.values)&&Object.values(row.values).every(isNumber));
 if(key==='diolino-food-goals')return isObject(value)&&Object.values(value).every(isNumber);
 if(key==='diolino-food-date-goals')return isObject(value)&&Object.entries(value).every(([date,goals])=>isDate(date)&&isObject(goals)&&Object.values(goals).every(isNumber));
 if(key==='diolino-strength-plan')return objectRows(value)&&value.every(row=>isString(row.id)&&isDate(row.date)&&isString(row.name)&&isNumber(row.sets)&&row.sets>0&&isString(row.reps)&&(row.load===null||isNumber(row.load)&&row.load>=0)&&isString(row.notes));
 if(key==='diolino-daily-tasks')return objectRows(value)&&value.every(row=>isString(row.id)&&isDate(row.date)&&isString(row.text)&&typeof row.done==='boolean'&&optionalNumber(row.minutes)&&objectRows(row.steps)&&row.steps.every(step=>isString(step.id)&&isString(step.text)&&typeof step.done==='boolean'));
 return false;
};

const filters=[{name:'Backup do Diolino 3.0',extensions:['json']}];

function currentPreferences(){
 const values:Record<string,unknown>={};
 for(const key of preferenceKeys){
  const raw=localStorage.getItem(key);
  if(raw!==null)values[key]=key==='diolino-theme'?raw:JSON.parse(raw);
 }
 return values;
}
function currentWebSections(){
 const sections:Record<string,unknown>={};
 const pending:Record<string,boolean>={};
 for(const key of sectionKeys){const value=reconcileWebSection(key,null);if(value!==null){if(!validLocalSection(key,value))throw new Error('Seção atual inválida. Restauração cancelada sem alterar os dados: '+key);sections[key]=value;pending[key]=localStorage.getItem(key+'.sqlite-pending')!==null}}
 sections.__pending=pending;
 return sections;
}

function loadPreferences(backup:Backup){
 for(const key of sectionKeys){
  localStorage.removeItem(key);
  localStorage.removeItem(key+'.sqlite-pending');
 }
 for(const key of preferenceKeys){
  const value=backup.preferences[key];
  if(value===undefined)localStorage.removeItem(key);
  else localStorage.setItem(key,key==='diolino-theme'?String(value):JSON.stringify(value));
 }
}

export function BackupPanel({setLocked}:{setLocked:(locked:boolean)=>void}){
 const [busy,setBusy]=useState(false);
 const [selected,setSelected]=useState<{path:string;backup:Backup}|null>(null);
 const [verified,setVerified]=useState(false);
 const [message,setMessage]=useState('');
 const [error,setError]=useState('');
 if(!isTauri())return <p className="notice">Abra o aplicativo Windows para usar backup e restauração.</p>;

 const run=async(operation:()=>Promise<void>)=>{
  setBusy(true);setLocked(true);setError('');setMessage('');
  try{await operation()}catch(reason){setError(String(reason))}
  finally{setBusy(false);setLocked(false)}
 };

 return <>
  <section className="panel">
   <h2>Exportar backup</h2>
   <p>Inclui os registros da 3.0, inclusive dados ainda no armazenamento da interface, tema, preferências, histórico de Foco e atalhos da Biblioteca. Os documentos originais ficam nas suas pastas.</p>
   <p className="muted">O backup é um arquivo JSON sem criptografia. Guarde-o em um local privado.</p>
   <button type="button" disabled={busy} onClick={()=>void run(async()=>{
    const path=await save({defaultPath:'Diolino-'+localDay()+'.diolino-backup.json',filters});
    if(!path)return;
    await flushLocalSections();
    const sections=currentWebSections();
    await invoke('export_backup',{path,preferences:currentPreferences(),sections});
    setMessage('Backup criado em '+path);
   })}>Salvar backup…</button>
  </section>
  <section className="panel">
   <h2>Restaurar backup</h2>
   <p>Feche outras janelas do Diolino. A restauração substitui os registros e preferências deste perfil e cria uma cópia de recuperação antes de aplicar o arquivo.</p>
   <button type="button" disabled={busy} onClick={()=>void run(async()=>{
    setSelected(null);setVerified(false);
    const path=await open({multiple:false,directory:false,filters});
    if(typeof path!=='string')return;
    const backup=await invoke<Backup>('inspect_backup',{path});
    setSelected({path,backup});
   })}>Selecionar backup…</button>
   {selected&&<div className="notice">
    <p>{selected.path}</p>
    <p>Criado em {new Date(selected.backup.createdAt).toLocaleString('pt-BR')} · {Object.keys(selected.backup.sections).length} seções de dados</p>
    <label><input type="checkbox" checked={verified} disabled={busy} onChange={event=>setVerified(event.target.checked)}/> Confirmo a substituição dos dados deste perfil</label>
    <div className="event-actions">
     <button type="button" disabled={!verified||busy} onClick={()=>void run(async()=>{
      await flushLocalSections();
      const sections:Record<string,unknown>={...selected.backup.sections};
      for(const key of sectionKeys){const current=reconcileWebSection(key,null);if(current!==null){if(!validLocalSection(key,current))throw new Error('Seção atual inválida. Restauração cancelada sem alterar os dados: '+key);if(sections[key]===undefined)sections[key]=current}}
      const recovery=await invoke<string>('restore_backup',{backup:{...selected.backup,sections},preferences:currentPreferences(),sections:currentWebSections()});
      setSelected(null);
      try{loadPreferences(selected.backup)}catch{
       setError('Os registros foram restaurados, mas o navegador local recusou alguma preferência. Cópia anterior: '+recovery);
       return;
      }
      sessionStorage.setItem('diolino-backup-result','Backup restaurado. Cópia anterior: '+recovery);
      window.location.reload();
     })}>Restaurar e reabrir</button>
     <button type="button" disabled={busy} onClick={()=>{setSelected(null);setVerified(false)}}>Cancelar</button>
    </div>
   </div>}
  </section>
  {error&&<p className="error" role="alert">{error}</p>}
  {message&&<p role="status">{message}</p>}
 </>;
}
