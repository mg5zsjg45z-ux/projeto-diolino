import {useEffect,useRef,useState} from 'react';
import {ListTodo,Play,Plus,Trash2,Save} from 'lucide-react';
import {localDay,type Task,type TaskStep} from './data';
import {loadLocalSection,useLocalSection} from './localSection';
type LegacyTask={id:string;date:string;text:string;done:boolean;minutes:number|null;steps:TaskStep[]};
const key='diolino-daily-tasks';
const empty:LegacyTask[]=[];
type Props={tasks:Task[];onSave:(edit:(tasks:Task[])=>Task[])=>Promise<boolean>;onFocus:(id:number,title:string,minutes:number|null)=>void;ready:boolean;error:string};
export function DailyTasks({tasks,onSave,onFocus,ready,error}:Props){
 const [legacyTasks,,legacyError,legacyReady]=useLocalSection(key,()=>loadLocalSection(key,empty));
 const [text,setText]=useState(''),[editingId,setEditingId]=useState<number|null>(null),[migrationError,setMigrationError]=useState('');
 const migrationBusy=useRef(false),saveRef=useRef(onSave),day=localDay();
 saveRef.current=onSave;
 useEffect(()=>{
  if(!ready||!legacyReady||migrationBusy.current||localStorage.getItem(key+'.migrated')==='true')return;
  migrationBusy.current=true;
  try{
   const backupKey=key+'.migration-backup';
   if(localStorage.getItem(backupKey)===null)localStorage.setItem(backupKey,JSON.stringify(legacyTasks));
   const valid=Array.isArray(legacyTasks)?legacyTasks.filter(task=>task&&typeof task.id==='string'&&typeof task.text==='string'&&task.text.trim()&&typeof task.date==='string'):[];
   const missing=valid.filter(task=>!tasks.some(existing=>existing.legacy_daily_id===task.id));
   const next=[...tasks];let id=Math.max(0,...next.map(task=>task.id))+1;
   for(const old of missing){const now=Date.now();next.push({id:id++,title:old.text.trim().slice(0,120),plan:'Pessoal',state:old.done?'Concluído':'A fazer',priority:'Normal',due:null,date:old.date,estimated_minutes:Number.isInteger(old.minutes)&&old.minutes!>=1?old.minutes:null,steps:Array.isArray(old.steps)?old.steps.filter(step=>step&&typeof step.id==='string'&&typeof step.text==='string').map(step=>({id:step.id,text:step.text,done:!!step.done})):[],legacy_daily_id:old.id,completed_at:null,created_at:now,updated_at:now})}
   const persist=missing.length===0?Promise.resolve(true):saveRef.current(()=>next);
   void persist.then(saved=>{if(saved)localStorage.setItem(key+'.migrated','true');else{migrationBusy.current=false;setMigrationError('A migração não foi confirmada. Os dados antigos continuam preservados.')}}).catch(()=>{migrationBusy.current=false});
  }catch{migrationBusy.current=false;setMigrationError('Não foi possível preparar a migração. Os registros antigos foram preservados.')}
 },[ready,legacyReady,tasks,legacyTasks]);
 const save=(edit:(items:Task[])=>Task[])=>{void onSave(edit)};
 const update=(id:number,edit:(task:Task)=>Task)=>save(items=>items.map(task=>task.id===id?edit({...task,updated_at:Date.now()}):task));
 const today=tasks.filter(task=>task.date===day||task.due===day||(!task.date&&!task.due&&task.state!=='Concluído'));
 return <>
  <section className="panel"><h2>Captura rápida</h2><form className="module-fields" onSubmit={event=>{event.preventDefault();const title=text.trim();if(!title||!ready)return;const now=Date.now(),id=Math.max(0,...tasks.map(task=>task.id))+1;const task:Task={id,title:title.slice(0,120),plan:'Pessoal',state:'A fazer',priority:'Normal',due:null,date:day,estimated_minutes:null,steps:[],completed_at:null,created_at:now,updated_at:now};save(items=>[...items,task]);setText('')}}><label>Nova tarefa<input required disabled={!ready} maxLength={120} value={text} onChange={event=>setText(event.target.value)}/></label><button type="submit" disabled={!ready||!text.trim()}><Plus size={16} aria-hidden="true"/> Adicionar</button></form></section>
  {(error||legacyError||migrationError)&&<p className="error" role="alert">{error||legacyError||migrationError}</p>}
  <section className="panel"><h2>Hoje</h2>{!ready||!legacyReady?<p className="muted">Abrindo tarefas…</p>:today.length===0?<p className="icon-line muted"><ListTodo aria-hidden="true" size={18}/> Nenhuma tarefa para hoje.</p>:<div className="study-list">{today.map(task=><article key={task.id} className="study-record daily-task"><div className="event-actions">
   <label><input aria-label={'Concluir tarefa: '+task.title} type="checkbox" checked={task.state==='Concluído'} onChange={event=>update(task.id,current=>({...current,state:event.target.checked?'Concluído':'A fazer',completed_at:event.target.checked?Date.now():null}))}/></label>
   {editingId===task.id?<form className="module-fields" onSubmit={event=>{event.preventDefault();const title=String(new FormData(event.currentTarget).get('title')).trim();if(title){update(task.id,current=>({...current,title:title.slice(0,120)}));setEditingId(null)}}}><label className="sr-only">Nome da tarefa<input name="title" required maxLength={120} defaultValue={task.title}/></label><button type="submit"><Save size={16} aria-hidden="true"/> Salvar</button><button type="button" onClick={()=>setEditingId(null)}>Cancelar</button></form>:<strong className={task.state==='Concluído'?'muted':''}>{task.title}</strong>}
   {editingId!==task.id&&<button type="button" disabled={!ready} aria-label={'Editar tarefa: '+task.title} onClick={()=>setEditingId(task.id)}>Editar</button>}
   <button type="button" className="danger" disabled={!ready} aria-label={'Apagar tarefa: '+task.title} onClick={()=>{if(window.confirm('Apagar a tarefa “'+task.title+'”? As sessões de foco permanecem no histórico.'))save(items=>items.filter(item=>item.id!==task.id))}}><Trash2 size={16} aria-hidden="true"/> Apagar</button>
   <label>Estimativa (min) <input aria-label={'Estimativa em minutos: '+task.title} type="number" min="1" max="120" step="1" value={task.estimated_minutes??''} onChange={event=>{const value=event.target.valueAsNumber;if(event.target.value==='')update(task.id,current=>({...current,estimated_minutes:null}));else if(Number.isInteger(value)&&value>=1&&value<=120)update(task.id,current=>({...current,estimated_minutes:value}))}}/></label>
   <button type="button" disabled={task.state==='Concluído'||!ready} onClick={()=>onFocus(task.id,task.title,task.estimated_minutes??null)}><Play size={16} aria-hidden="true"/> Iniciar Foco</button>
  </div><details><summary>Micro-passos{(task.steps?.length??0)>0&&' · '+task.steps!.filter(step=>step.done).length+'/'+task.steps!.length}</summary>
   {(task.steps??[]).map(step=><form className="module-fields" key={step.id} onSubmit={event=>{event.preventDefault();const title=String(new FormData(event.currentTarget).get('step')).trim();if(title)update(task.id,current=>({...current,steps:(current.steps??[]).map(item=>item.id===step.id?{...item,text:title}:item)}))}}><input aria-label={'Concluir micro-passo: '+step.text} type="checkbox" checked={step.done} onChange={event=>update(task.id,current=>({...current,steps:(current.steps??[]).map(item=>item.id===step.id?{...item,done:event.target.checked}:item)}))}/><label>Editar micro-passo<input name="step" required maxLength={160} defaultValue={step.text}/></label><button type="submit">Salvar</button><button type="button" className="danger" aria-label={'Apagar micro-passo: '+step.text} onClick={()=>update(task.id,current=>({...current,steps:(current.steps??[]).filter(child=>child.id!==step.id)}))}><Trash2 size={16} aria-hidden="true"/> Apagar</button></form>)}
   <form className="module-fields" onSubmit={event=>{event.preventDefault();const form=event.currentTarget;const title=String(new FormData(form).get('step')).trim();if(!title)return;const step:TaskStep={id:crypto.randomUUID(),text:title,done:false};update(task.id,current=>({...current,steps:[...(current.steps??[]),step]}));form.reset()}}><label>Novo micro-passo<input name="step" required maxLength={160}/></label><button type="submit">Adicionar micro-passo</button></form>
   {task.state!=='Concluído'&&(task.steps?.length??0)>0&&task.steps!.every(step=>step.done)&&<p className="muted">Micro-passos concluídos. Marque a tarefa quando terminar.</p>}
  </details></article>)}</div>}</section>
 </>;
}