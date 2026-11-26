import {useState} from 'react';
import {invoke,isTauri} from '@tauri-apps/api/core';
import {open,save} from '@tauri-apps/plugin-dialog';
import {flushLocalSections} from './localSection';
import {localDay} from './data';

const preferenceKeys=['diolino-theme','diolino-library','diolino-focus-settings','diolino-focus-timer','diolino-focus-sessions'];
const sectionKeys=[
 'diolino-workspace-v1','diolino-health-entries','diolino-health-goals','diolino-habits-v1',
 'diolino-habit-marks-v1','diolino-preview-reviews','diolino-bible-days','diolino-bible-notes',
 'diolino-food-entries','diolino-food-goals','diolino-food-date-goals','diolino-strength-plan','diolino-daily-tasks',
];
type Backup={createdAt:string;sections:Record<string,unknown>;preferences:Record<string,unknown>};
const filters=[{name:'Backup do Diolino 3.0',extensions:['json']}];

function currentPreferences(){
 const values:Record<string,unknown>={};
 for(const key of preferenceKeys){
  const raw=localStorage.getItem(key);
  if(raw!==null)values[key]=key==='diolino-theme'?raw:JSON.parse(raw);
 }
 return values;
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
   <p>Inclui os registros gravados na 3.0, tema, preferências e histórico de Foco e atalhos da Biblioteca. Os documentos originais ficam nas suas pastas.</p>
   <p className="muted">O backup é um arquivo JSON sem criptografia. Guarde-o em um local privado.</p>
   <button type="button" disabled={busy} onClick={()=>void run(async()=>{
    const path=await save({defaultPath:'Diolino-'+localDay()+'.diolino-backup.json',filters});
    if(!path)return;
    await flushLocalSections();
    await invoke('export_backup',{path,preferences:currentPreferences()});
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
      const recovery=await invoke<string>('restore_backup',{backup:selected.backup,preferences:currentPreferences()});
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
