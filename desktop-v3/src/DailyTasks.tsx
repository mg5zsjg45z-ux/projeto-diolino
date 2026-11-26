import {useState} from 'react';
import {dailyTasks,nextTaskId,parseCapture,setTaskState} from './taskModel';
import type {Task} from './data';

type Props={tasks:Task[];floor:number;day:string;ready:boolean;onFocus:(task:Task)=>void;
  onSave:(edit:(tasks:Task[])=>Task[])=>Promise<boolean>};

export function DailyTasks({tasks,floor,day,ready,onFocus,onSave}:Props){
  const [text,setText]=useState(''),[syntax,setSyntax]=useState(false);
  const [editing,setEditing]=useState<number|null>(null);
  const [state,setState]=useState(''),[priority,setPriority]=useState(''),[plan,setPlan]=useState('');
  const draft=syntax?parseCapture(text,day):{title:text.trim(),priority:'Normal',plan:'Pessoal',due:null,estimated_minutes:null};
  const items=dailyTasks(tasks,day).filter(t=>(!state||t.state===state)&&(!priority||t.priority===priority)&&(!plan||t.plan===plan));
  const update=(id:number,edit:(task:Task)=>Task)=>onSave(all=>all.map(t=>t.id===id?{...edit(t),updated_at:Date.now()}:t));
  return <>
    <section className="panel"><h2>Captura rápida</h2>
      <form className="module-fields" onSubmit={async e=>{
        e.preventDefault();if(!ready||!draft.title)return;
        const now=Date.now();
        if(await onSave(all=>[...all,{...draft,id:nextTaskId(all,floor),date:day,state:'A fazer',steps:[],created_at:now,updated_at:now}]))setText('');
      }}>
        <label>Nova tarefa<input required maxLength={160} value={text} onChange={e=>setText(e.target.value)}/></label>
        <label><input type="checkbox" checked={syntax} onChange={e=>setSyntax(e.target.checked)}/> Interpretar #plano, p1–p3, hoje/amanhã e minutos (30m)</label>
        {syntax&&text&&<p>Prévia: {draft.title || 'Informe o título'} · {draft.plan} · {draft.priority} · {draft.due??'Sem prazo'} · {draft.estimated_minutes??'—'} min</p>}
        <button disabled={!ready||!draft.title}>Adicionar</button>
      </form>
    </section>
    <section className="panel"><h2>Tarefas do dia</h2>
      <div className="module-fields">
        <label>Estado<select value={state} onChange={e=>setState(e.target.value)}><option value="">Todos</option>{['A fazer','Em andamento','Concluído'].map(v=><option key={v}>{v}</option>)}</select></label>
        <label>Prioridade<select value={priority} onChange={e=>setPriority(e.target.value)}><option value="">Todas</option>{['Alta','Normal','Baixa'].map(v=><option key={v}>{v}</option>)}</select></label>
        <label>Plano<select value={plan} onChange={e=>setPlan(e.target.value)}><option value="">Todos</option>{[...new Set(tasks.filter(t=>!t.archived_at).map(t=>t.plan))].sort().map(v=><option key={v}>{v}</option>)}</select></label>
      </div>
      {!items.length&&<p>Nenhuma tarefa nesta seleção.</p>}
      {items.map(task=><article key={task.id} className="study-record daily-task">
        <div className="event-actions">
          <label><input type="checkbox" aria-label={'Concluir '+task.title} checked={task.state==='Concluído'} disabled={!ready}
            onChange={e=>{const state=e.target.checked?'Concluído':'A fazer';void update(task.id,t=>setTaskState(t,state))}}/></label>
          {editing===task.id?<form onSubmit={async e=>{
            e.preventDefault();const title=String(new FormData(e.currentTarget).get('title')).trim();
            if(title&&await update(task.id,t=>({...t,title})))setEditing(null);
          }}><label>Nome da tarefa<input name="title" required autoFocus maxLength={160} defaultValue={task.title}/></label>
            <button disabled={!ready}>Salvar</button><button type="button" onClick={()=>setEditing(null)}>Cancelar</button></form>:
            <><strong>{task.title}</strong><button aria-label={'Editar '+task.title} onClick={()=>setEditing(task.id)}>Editar</button></>}
          <small>{task.plan} · {task.priority} · {task.due ? (task.due<day?'Vencida em ':'Prazo ')+task.due : 'Sem prazo'}</small>
          <label>Estimativa (min)<input type="number" min={1} max={120} key={task.estimated_minutes??'none'} defaultValue={task.estimated_minutes??''}
            onBlur={e=>{if(!e.target.validity.valid){e.target.reportValidity();return}const n=e.target.value?e.target.valueAsNumber:null;
              if(n!==(task.estimated_minutes??null))void update(task.id,t=>({...t,estimated_minutes:n}))}}/></label>
          <button disabled={!ready||task.state==='Concluído'} onClick={()=>onFocus(task)}>Iniciar foco</button>
          <button disabled={!ready} aria-label={'Apagar '+task.title} onClick={()=>{if(window.confirm('Apagar “'+task.title+'”? O histórico de foco será preservado.'))void update(task.id,t=>({...t,archived_at:Date.now()}))}}>Apagar</button>
        </div>
        <details><summary>Micro-passos ({task.steps?.filter(s=>s.done).length??0}/{task.steps?.length??0})</summary>
          {task.steps?.map(step=><form key={step.id} className="module-fields" onSubmit={e=>{
            e.preventDefault();const text=String(new FormData(e.currentTarget).get('step')).trim();
            if(text)void update(task.id,t=>({...t,steps:t.steps?.map(s=>s.id===step.id?{...s,text}:s)}));
          }}>
            <input type="checkbox" aria-label={'Concluir '+step.text} checked={step.done} onChange={e=>{
              const done=e.target.checked;void update(task.id,t=>({...t,steps:t.steps?.map(s=>s.id===step.id?{...s,done}:s)}))}}/>
            <label>Editar micro-passo<input key={step.text} name="step" required maxLength={160} defaultValue={step.text}/></label>
            <button disabled={!ready}>Salvar</button><button type="button" aria-label={'Apagar '+step.text} onClick={()=>void update(task.id,t=>({...t,steps:t.steps?.filter(s=>s.id!==step.id)}))}>Apagar</button>
          </form>)}
          <form className="module-fields" onSubmit={async e=>{
            e.preventDefault();const form=e.currentTarget,text=String(new FormData(form).get('step')).trim();
            if(text&&await update(task.id,t=>({...t,steps:[...(t.steps??[]),{id:crypto.randomUUID(),text,done:false}]})))form.reset();
          }}><label>Novo micro-passo<input name="step" required maxLength={160}/></label><button disabled={!ready}>Adicionar micro-passo</button></form>
        </details>
      </article>)}
    </section>
  </>;
}
