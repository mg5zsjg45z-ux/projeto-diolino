import {useState} from 'react';
import {ListTodo,Play,Plus} from 'lucide-react';
import {localDay} from './data';
import {loadLocalSection,useLocalSection} from './localSection';

type Step={id:string;text:string;done:boolean};
type DailyTask={id:string;date:string;text:string;done:boolean;minutes:number|null;steps:Step[]};
const key='diolino-daily-tasks';
const empty:DailyTask[]=[];

export function DailyTasks({onFocus}:{onFocus:(title:string,minutes:number|null)=>void}){
 const [tasks,setTasks,error,ready]=useLocalSection(key,()=>loadLocalSection(key,empty));
 const [text,setText]=useState('');
 const day=localDay();
 const today=tasks.filter(task=>task.date===day);
 const update=(id:string,edit:(task:DailyTask)=>DailyTask)=>setTasks(current=>current.map(task=>task.id===id?edit(task):task));

 return <>
  <section className="panel">
   <h2>Captura rápida</h2>
   <form className="module-fields" onSubmit={event=>{
    event.preventDefault();
    const title=text.trim();
    if(!title)return;
    const task:DailyTask={id:crypto.randomUUID(),date:localDay(),text:title,done:false,minutes:null,steps:[]};
    setTasks(current=>[...current,task]);
    setText('');
   }}>
    <label>Nova tarefa<input required disabled={!ready} maxLength={160} value={text} onChange={event=>setText(event.target.value)}/></label>
    <button type="submit" disabled={!ready||!text.trim()}><Plus size={16} aria-hidden="true"/> Adicionar</button>
   </form>
  </section>
  {error&&<p className="error" role="alert">{error}</p>}
  <section className="panel">
   <h2>Hoje</h2>
   {!ready?<p className="muted">{error?"Tarefas indisponíveis.":"Carregando tarefas…"}</p>:today.length===0?<p className="icon-line muted"><ListTodo aria-hidden="true" size={18}/> Nenhuma tarefa para hoje.</p>:<div className="study-list">
    {today.map(task=><article key={task.id} className="study-record daily-task">
     <div className="event-actions">
      <label><input type="checkbox" checked={task.done} onChange={event=>update(task.id,current=>({...current,done:event.target.checked}))}/> {task.text}</label>
      <label>Estimativa (min) <input aria-label={'Estimativa em minutos: '+task.text} type="number" min="1" max="120" step="1" value={task.minutes??''} onChange={event=>{
       const value=event.target.valueAsNumber;
       if(event.target.value==='')update(task.id,current=>({...current,minutes:null}));
       else if(Number.isInteger(value)&&value>=1&&value<=120)update(task.id,current=>({...current,minutes:value}));
      }}/></label>
      <button type="button" disabled={task.done} onClick={()=>onFocus(task.text,task.minutes)}><Play size={16} aria-hidden="true"/> Iniciar Foco</button>
     </div>
     <details>
      <summary>Micro-passos{task.steps.length>0&&' · '+task.steps.filter(step=>step.done).length+'/'+task.steps.length}</summary>
      {task.steps.map(step=><form className="module-fields" key={step.id+':'+step.text} onSubmit={event=>{
       event.preventDefault();
       const title=String(new FormData(event.currentTarget).get('step')).trim();
       if(title)update(task.id,current=>({...current,steps:current.steps.map(item=>item.id===step.id?{...item,text:title}:item)}));
      }}>
       <input aria-label={'Concluir micro-passo: '+step.text} type="checkbox" checked={step.done} onChange={event=>update(task.id,current=>({...current,steps:current.steps.map(item=>item.id===step.id?{...item,done:event.target.checked}:item)}))}/>
       <label>Editar micro-passo<input name="step" required maxLength={160} defaultValue={step.text}/></label>
       <button type="submit">Salvar</button>
      </form>)}
      <form className="module-fields" onSubmit={event=>{
       event.preventDefault();
       const form=event.currentTarget;
       const title=String(new FormData(form).get('step')).trim();
       if(!title)return;
       const step:Step={id:crypto.randomUUID(),text:title,done:false};
       update(task.id,current=>({...current,steps:[...current.steps,step]}));
       form.reset();
      }}>
       <label>Novo micro-passo<input name="step" required maxLength={160}/></label>
       <button type="submit">Adicionar micro-passo</button>
      </form>
      {!task.done&&task.steps.length>0&&task.steps.every(step=>step.done)&&<p className="muted">Micro-passos concluídos. Marque a tarefa quando terminar.</p>}
     </details>
    </article>)}
   </div>}
  </section>
 </>;
}
