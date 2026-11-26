import {useState} from 'react';
import {Plus,Pencil,Trash2} from 'lucide-react';
import {loadLocalSection,useLocalSection} from './localSection';
import {ModalDialog} from './ModalDialog';

type Exercise={id:string;date:string;name:string;sets:number;reps:string;load:number|null;notes:string};
const storageKey='diolino-strength-plan';
const empty:Exercise[]=[];
const dateFormat=new Intl.DateTimeFormat('pt-BR',{weekday:'short',day:'2-digit',month:'2-digit'});
const iso=(date:Date)=>[date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');

export function StrengthPlan({day}:{day:string}){
 const [exercises,setExercises,error]=useLocalSection(storageKey,()=>loadLocalSection(storageKey,empty));
 const [view,setView]=useState<'Semana'|'Mês'>('Semana');
 const [editing,setEditing]=useState<Exercise|null>(null);
 const [formOpen,setFormOpen]=useState(false);
 const [status,setStatus]=useState('');
 const start=new Date(day+'T12:00:00');
 const end=new Date(start);
 if(view==='Semana'){
  start.setDate(start.getDate()-((start.getDay()+6)%7));
  end.setTime(start.getTime());
  end.setDate(start.getDate()+6);
 }else{
  start.setDate(1);
  end.setMonth(end.getMonth()+1,0);
 }
 const first=iso(start),last=iso(end);
 const rows=exercises.filter(row=>row.date>=first&&row.date<=last).sort((a,b)=>a.date.localeCompare(b.date));
 return <section className="panel">
  <div className="agenda-heading">
   <h2>Planejamento de musculação</h2>
   <div className="event-actions">
    <div className="segments" aria-label="Período do treino">
     {(['Semana','Mês'] as const).map(period=><button key={period} type="button" aria-pressed={view===period} onClick={()=>setView(period)}>{period}</button>)}
    </div>
    <button type="button" onClick={()=>{setEditing(null);setFormOpen(true)}}><Plus size={16} aria-hidden="true"/> Adicionar exercício</button>
   </div>
  </div>
  <p className="muted"><time dateTime={first}>{dateFormat.format(start)}</time> a <time dateTime={last}>{dateFormat.format(end)}</time></p>
  {error&&<p role="alert" className="error">{error}</p>}
  <p className="muted" role="status">{status}</p>
  {rows.length?<div className="module-table"><table>
   <thead><tr><th>Dia</th><th>Exercício</th><th>Séries</th><th>Repetições</th><th>Carga (kg)</th><th>Observações</th><th>Ações</th></tr></thead>
   <tbody>{rows.map(row=><tr key={row.id}>
    <td><time dateTime={row.date}>{dateFormat.format(new Date(row.date+'T12:00:00'))}</time></td>
    <td>{row.name}</td><td>{row.sets}</td><td>{row.reps}</td><td>{row.load?.toLocaleString('pt-BR')??'—'}</td><td>{row.notes||'—'}</td>
    <td><div className="event-actions">
     <button type="button" aria-label={'Editar '+row.name} onClick={()=>{setEditing(row);setFormOpen(true)}}><Pencil size={16} aria-hidden="true"/></button>
     <button type="button" aria-label={'Remover '+row.name} onClick={()=>{if(window.confirm('Remover este exercício do planejamento?')){setExercises(current=>current.filter(item=>item.id!==row.id));setStatus('Exercício removido.')}}}><Trash2 size={16} aria-hidden="true"/></button>
    </div></td>
   </tr>)}</tbody>
  </table></div>:<p className="muted">Nenhum exercício planejado neste período.</p>}
  {formOpen&&<ModalDialog titleId="strength-dialog-title" onClose={()=>setFormOpen(false)}><form className="agenda-form" onSubmit={event=>{
   event.preventDefault();
   const data=new FormData(event.currentTarget);
   const name=String(data.get('name')).trim(),reps=String(data.get('reps')).trim();
   if(!name||!reps)return;
   const date=String(data.get('date'));
   const load=String(data.get('load'));
   const row:Exercise={id:editing?.id??crypto.randomUUID(),date,name,reps,
    sets:Number(data.get('sets')),load:load===''?null:Number(load),notes:String(data.get('notes')).trim()};
   setExercises(current=>editing?current.map(item=>item.id===editing.id?row:item):[...current,row]);
   setFormOpen(false);
   setStatus(date<first||date>last?'Exercício salvo fora do período exibido.':'Exercício salvo.');
  }}>
   <h2 id="strength-dialog-title">{editing?'Editar exercício':'Adicionar exercício'}</h2>
   <label>Data do treino<input type="date" name="date" required defaultValue={editing?.date??day}/></label>
   <label>Exercício<input name="name" required maxLength={120} defaultValue={editing?.name}/></label>
   <div className="form-row">
    <label>Séries<input type="number" name="sets" required min="1" max="100" defaultValue={editing?.sets??3}/></label>
    <label>Repetições<input name="reps" required maxLength={40} defaultValue={editing?.reps} placeholder="Ex.: 8–12"/></label>
   </div>
   <label>Carga (kg)<input type="number" name="load" min="0" step=".01" defaultValue={editing?.load??undefined}/></label>
   <label>Observações do exercício<textarea name="notes" rows={2} maxLength={500} defaultValue={editing?.notes}/></label>
   <div className="form-actions"><button type="button" onClick={()=>setFormOpen(false)}>Cancelar</button><button type="submit">Salvar exercício</button></div>
  </form></ModalDialog>}
 </section>;
}
