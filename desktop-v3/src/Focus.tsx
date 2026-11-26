import {useEffect,useRef,useState} from 'react';
import {Timer,RotateCcw,Play,Pause,SkipForward,Settings,Trash2,Save} from 'lucide-react';

type Settings={focusMin:number;shortBreakMin:number;longBreakMin:number;longBreakEvery:number};
type Phase='focus'|'shortBreak'|'longBreak';
type Clock={phase:Phase;remainingMs:number;running:boolean;endsAt:number|null;cycles:number;task?:{title:string;minutes:number}};
type Session={id:string;date:string;minutes:number;completedAt:number};
const defaults:Settings={focusMin:25,shortBreakMin:5,longBreakMin:15,longBreakEvery:4};
const dayKey=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
const read=<T,>(key:string,fallback:T):T=>{try{const value=localStorage.getItem(key);return value?JSON.parse(value) as T:fallback}catch{return fallback}};
const phaseName=(phase:Phase)=>phase==='focus'?'Concentração':phase==='shortBreak'?'Pausa curta':'Pausa longa';

export function startTaskFocus(title:string,estimate:number|null){
 const clock=read<Clock|null>('diolino-focus-timer',null);
 // Let Focus finish or resume its current block instead of replacing it.
 if(clock?.running)return false;
 const settings=read<Partial<Settings>>('diolino-focus-settings',{});
 const minutes=estimate??settings.focusMin??defaults.focusMin;
 const remainingMs=minutes*60000;
 const next:Clock={phase:'focus',remainingMs,running:true,endsAt:Date.now()+remainingMs,cycles:clock?.cycles??0,task:{title,minutes}};
 localStorage.setItem('diolino-focus-timer',JSON.stringify(next));
 return true;
}

export function Focus({onFeedback}:{onFeedback:(message:string)=>void}){
 const [settings,setSettings]=useState<Settings>(()=>({...defaults,...read<Partial<Settings>>('diolino-focus-settings',{})}));
 const [draft,setDraft]=useState<Settings>(()=>({...defaults,...read<Partial<Settings>>('diolino-focus-settings',{})}));
 const [clock,setClock]=useState<Clock>(()=>read<Clock>('diolino-focus-timer',{phase:'focus',remainingMs:defaults.focusMin*60000,running:false,endsAt:null,cycles:0}));
 const [sessions,setSessions]=useState<Session[]>(()=>read<Session[]>('diolino-focus-sessions',[]));
 const completionRef=useRef<number|null>(null);
 useEffect(()=>localStorage.setItem('diolino-focus-settings',JSON.stringify(settings)),[settings]);
 useEffect(()=>localStorage.setItem('diolino-focus-timer',JSON.stringify(clock)),[clock]);
 useEffect(()=>localStorage.setItem('diolino-focus-sessions',JSON.stringify(sessions)),[sessions]);
 useEffect(()=>{
  if(!clock.running||clock.endsAt===null)return;
  const tick=()=>{
   const remainingMs=Math.max(0,clock.endsAt!-Date.now());
   if(remainingMs===0){
    if(completionRef.current===clock.endsAt)return;
    completionRef.current=clock.endsAt;
    if(clock.phase==='focus'){
     const now=Date.now(),cycles=clock.cycles+1,phase:Phase=cycles%settings.longBreakEvery===0?'longBreak':'shortBreak';
     setSessions(current=>[{id:String(now),date:dayKey(),minutes:clock.task?.minutes??settings.focusMin,completedAt:now},...current].slice(0,500));
     setClock({phase,remainingMs:(phase==='longBreak'?settings.longBreakMin:settings.shortBreakMin)*60000,running:false,endsAt:null,cycles});
    }else setClock({...clock,remainingMs:0,running:false,endsAt:null});
    return;
   }
   setClock(current=>current.running&&current.endsAt===clock.endsAt?{...current,remainingMs}:current);
  };
  tick();const interval=window.setInterval(tick,1000);return()=>window.clearInterval(interval);
 },[clock.running,clock.endsAt,clock.phase,clock.cycles,clock.task,settings]);
 const phaseMinutes=clock.phase==='focus'?(clock.task?.minutes??settings.focusMin):clock.phase==='shortBreak'?settings.shortBreakMin:settings.longBreakMin;
 const remaining=Math.max(0,clock.running&&clock.endsAt!==null?clock.endsAt-Date.now():clock.remainingMs);
 const percent=Math.max(0,Math.min(100,(phaseMinutes*60000-remaining)/(phaseMinutes*60000)*100));
 const time=`${String(Math.floor(remaining/60000)).padStart(2,'0')}:${String(Math.floor(remaining%60000/1000)).padStart(2,'0')}`;
 const today=sessions.filter(s=>s.date===dayKey()),minutes=today.reduce((sum,s)=>sum+s.minutes,0);
 const start=()=>setClock(current=>({...current,running:true,endsAt:Date.now()+current.remainingMs}));
 const pause=()=>setClock(current=>({...current,remainingMs:Math.max(0,(current.endsAt??Date.now())-Date.now()),running:false,endsAt:null}));
 const reset=()=>setClock(current=>({...current,phase:'focus',remainingMs:(current.task?.minutes??settings.focusMin)*60000,running:false,endsAt:null}));
 const saveSettings=(event:React.FormEvent)=>{event.preventDefault();const safe={focusMin:Math.max(1,Math.min(120,Math.round(draft.focusMin||1))),shortBreakMin:Math.max(1,Math.min(60,Math.round(draft.shortBreakMin||1))),longBreakMin:Math.max(1,Math.min(60,Math.round(draft.longBreakMin||1))),longBreakEvery:Math.max(2,Math.min(8,Math.round(draft.longBreakEvery||2)))};setSettings(safe);setDraft(safe);setClock(current=>({...current,phase:'focus',remainingMs:safe.focusMin*60000,running:false,endsAt:null,task:undefined}));onFeedback("Configurações de foco salvas.")};
 return <>
  <div className="focus-layout">
   <section className="panel focus-clock-panel">
    <p className="eyebrow">{phaseName(clock.phase).toUpperCase()} · CICLO {clock.cycles+1}</p>
    <div className="focus-ring" style={{background:`conic-gradient(var(--accent) ${percent}%,var(--soft) 0)`}}><div><strong>{time}</strong><span>{phaseName(clock.phase)}</span></div></div>
    {clock.task&&<p className="focus-hint">{clock.task.title}</p>}
    <p className="muted focus-hint">{clock.phase==='focus'?'Afaste as distrações e avance em uma tarefa por vez.':'Descanse os olhos e alongue-se um pouco.'}</p>
    <div className="focus-controls"><button className="primary-action" onClick={clock.running?pause:start}>{clock.running?<Pause aria-hidden="true" size={16}/>:<Play aria-hidden="true" size={16}/>} {clock.running?'Pausar':'Iniciar'}</button><button onClick={reset}><RotateCcw aria-hidden="true" size={16}/> Reiniciar</button>{clock.phase!=='focus'&&<button onClick={()=>setClock({...clock,phase:'focus',remainingMs:settings.focusMin*60000,running:false,endsAt:null})}><SkipForward aria-hidden="true" size={16}/> Pular pausa</button>}</div>
   </section>
   <section className="panel focus-stats"><h2>Seu ritmo de hoje</h2><div className="focus-stat-grid"><div><strong>{today.length}</strong><span>sessões concluídas</span></div><div><strong>{minutes}</strong><span>minutos focados</span></div><div><strong>{clock.cycles}</strong><span>ciclos completos</span></div></div><p className="muted">As sessões entram no histórico ao concluir um bloco de concentração.</p>
    <details className="focus-settings"><summary><Settings aria-hidden="true" size={16}/> Configurar temporizador</summary><form onSubmit={saveSettings}><label>Concentração (min)<input type="number" min="1" max="120" value={draft.focusMin} onChange={e=>setDraft({...draft,focusMin:Number(e.target.value)})}/></label><label>Pausa curta (min)<input type="number" min="1" max="60" value={draft.shortBreakMin} onChange={e=>setDraft({...draft,shortBreakMin:Number(e.target.value)})}/></label><label>Pausa longa (min)<input type="number" min="1" max="60" value={draft.longBreakMin} onChange={e=>setDraft({...draft,longBreakMin:Number(e.target.value)})}/></label><label>Pausa longa a cada ciclos<input type="number" min="2" max="8" value={draft.longBreakEvery} onChange={e=>setDraft({...draft,longBreakEvery:Number(e.target.value)})}/></label><button className="primary-action" type="submit"><Save size={16} aria-hidden="true"/> Salvar configurações</button></form></details>
   </section>
  </div>
  <div className="focus-history-heading"><h2>Sessões recentes</h2><button onClick={()=>{if(window.confirm('Apagar o histórico de sessões de foco deste dispositivo?'))setSessions([])}} disabled={sessions.length===0}><Trash2 aria-hidden="true" size={16}/> Limpar histórico</button></div>
  {sessions.length===0?<section className="panel"><p className="icon-line"><Timer size={18} aria-hidden="true"/> Nenhuma sessão concluída ainda. Inicie um ciclo para começar.</p></section>:<div className="focus-session-list">{sessions.slice(0,20).map(session=><article key={session.id}><span className="focus-session-icon"><Timer aria-hidden="true" size={18}/></span><div><b>Concentração concluída</b><small>{new Date(session.completedAt).toLocaleString('pt-BR',{dateStyle:'medium',timeStyle:'short'})}</small></div><strong>{session.minutes} min</strong></article>)}</div>}
 </>;
}
