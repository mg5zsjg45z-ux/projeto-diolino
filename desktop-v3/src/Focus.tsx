import {useEffect,useState} from 'react';
import {change,finish,newSession,observe,maxGap,type Mode,type Session} from './focusModel';
import {localDay,type Task} from './data';
import type {Workspace,useWorkspace} from './workspace';

type Store=ReturnType<typeof useWorkspace>;
export type Preferences={focusMin:number;shortBreakMin:number;longBreakMin:number;longBreakEvery:number;
  breaks:'suggest'|'auto'|'manual';sound:boolean;notify:boolean};
const defaults:Preferences={focusMin:25,shortBreakMin:5,longBreakMin:15,longBreakEvery:4,breaks:'suggest',sound:false,notify:false};
const owner=crypto.randomUUID();
function legacy<T>(key:string,fallback:T):T {
  try{return JSON.parse(localStorage.getItem(key)??'null')??fallback}catch{return fallback}
}
function prefs(w:Workspace):Preferences {
  return {...defaults,...legacy<Partial<Preferences>>('diolino-focus-settings',{}),...w.focusOptions};
}
const timer=(n:number)=>String(Math.floor(n/60)).padStart(2,'0')+':'+String(Math.floor(n%60)).padStart(2,'0');
function transitionNotice(text:string,p:Preferences){
  if(p.notify && 'Notification' in window && Notification.permission==='granted'){
    try{new Notification('Diolino',{body:text})}catch{ /* The visible status remains available. */ }
  }
  if(p.sound){
    try{const audio=new AudioContext(),note=audio.createOscillator(),gain=audio.createGain();
      gain.gain.value=0.07;note.connect(gain);gain.connect(audio.destination);note.start();note.stop(audio.currentTime+0.18);
      note.onended=()=>{void audio.close()};}catch{ /* Sound is optional. */ }
  }
}

export function useFocus(store:Store,feedback:(text:string)=>void) {
  const {save,value}=store, session=value.activeFocus, rest=value.focusBreak;
  const options=prefs(value);
  useEffect(()=>{
    if(!store.loaded||session?.status!=='running')return;
    const sample=()=>void save(w=>{
      const s=w.activeFocus;
      if(!s||s.status!=='running'||s.id!==session.id)return w;
      const now=Date.now();
      if(s.owner!==owner && now-s.checkpoint<=maxGap && now>=s.checkpoint)return w;
      const next=observe(s,owner,now);
      return next===s?w:{...w,activeFocus:next};
    },true);
    const id=window.setInterval(sample,3000);
    return ()=>clearInterval(id);
  },[save,store.loaded,session?.id,session?.status]);
  useEffect(()=>{
    if(!rest?.endsAt)return;
    const endsAt=rest.endsAt;
    const id=window.setTimeout(()=>{void save(w=>w.focusBreak?.endsAt===endsAt?{...w,focusBreak:null}:w)
      .then(ok=>{if(ok){feedback('Pausa concluída.');transitionNotice('Pausa concluída.',options)}})},Math.min(2147483647,Math.max(0,endsAt-Date.now())));
    return ()=>clearTimeout(id);
  },[save,rest?.endsAt]);
  useEffect(()=>{
    if(session?.status==='review'){feedback('Foco encerrado. Confirme ou descarte a sessão.');transitionNotice('Foco encerrado.',options)}
    if(session?.status==='paused' && session.events.at(-1)?.name==='recovered')feedback('Sessão recuperada e pausada. O intervalo sem observação foi excluído.');
  },[session?.id,session?.status]);
  const start=async(mode:Mode,task:Task|null,minutes:number|null)=>{
    let created=false;
    const ok=await save(w=>{
      if(w.activeFocus)return w;
      created=true;return {...w,focusBreak:null,activeFocus:newSession(mode,task,minutes,owner)};
    });
    if(ok)feedback(created?'Foco iniciado.':'Já existe uma sessão. Retome, confirme ou descarte antes de iniciar outra.');
  };
  const control=(action:'pause'|'resume'|'end')=>save(w=>{
    if(!session||w.activeFocus?.id!==session.id)return w;
    const now=Date.now(),s=observe(w.activeFocus,owner,now);
    if(s.status==='review')return {...w,activeFocus:s};
    if(s.status==='running'&&s.owner!==owner)throw new Error('A sessão está ativa em outra janela.');
    let next=s;
    if(action==='resume'&&s.status==='paused')next={...change(s,'running','resumed',now),owner};
    if(action==='pause'&&s.status==='running')next=change(s,'paused','paused',now,'Pausa manual');
    if(action==='end')next=change(s,'review','ended',now);
    return {...w,activeFocus:next};
  });
  const complete=(discard:boolean,asStudy:boolean,chosenBreak?:number)=>save(w=>{
    if(!session||w.activeFocus?.id!==session.id)return w;
    const now=Date.now(),s=observe(w.activeFocus,owner,now);
    if(s.status==='running'&&s.owner!==owner)throw new Error('A sessão está ativa em outra janela.');
    const next=finish({...w,activeFocus:s},s.id,discard,asStudy,now);
    if(next.activeFocus||discard)return next;
    const cycles=(w.focusCycles??0)+1,long=cycles%options.longBreakEvery===0;
    const length=(chosenBreak??(long?options.longBreakMin:options.shortBreakMin))*60000;
    return {...next,focusCycles:cycles,focusBreak: length===0 || (options.breaks==='manual' && chosenBreak===undefined)?null:{
      length,remaining:length,long,endsAt:options.breaks==='auto'?now+length:null}};
  });
  const restart=()=>save(w=>{
    if(!session||w.activeFocus?.id!==session.id)return w;
    const now=Date.now(),s=observe(w.activeFocus,owner,now);
    if(s.status==='running'&&s.owner!==owner)throw new Error('A sessão está ativa em outra janela.');
    const next=finish({...w,activeFocus:s},s.id,true,false,now);
    const fresh=newSession(s.mode,null,s.planned_seconds===null?null:s.planned_seconds/60,owner,now);
    return {...next,activeFocus:{...fresh,task_id:s.task_id,task_title:s.task_title}};
  });
  return {options,start,control,complete,restart};
}

export function Focus({store,controller}:{store:Store;controller:ReturnType<typeof useFocus>}) {
  const {value:w,save}=store,{options,start,control,complete}=controller;
  const [mode,setMode]=useState<Mode>('Pomodoro'),[taskId,setTaskId]=useState(''),[asStudy,setStudy]=useState(false);
  const [flowBreak,setFlowBreak]=useState('5');
  const [now,setNow]=useState(Date.now());
  const s=w.activeFocus,rest=w.focusBreak, running=s?.status==='running'||!!rest?.endsAt;
  useEffect(()=>{if(!running)return;const clock=window.setInterval(()=>setNow(Date.now()),250);return()=>clearInterval(clock)},[running]);
  useEffect(()=>{setStudy(false);setFlowBreak(String(options.shortBreakMin))},[s?.id]);
  const active=s?.status==='running'&&s.owner===owner&&now>=s.checkpoint && now-s.checkpoint<=maxGap ?
    observe(s,owner,now).active_seconds : s?.active_seconds??0;
  const tasks=w.tasks.filter(t=>!t.archived_at&&t.state!=='Concluído'),task=tasks.find(t=>String(t.id)===taskId)??null;
  const plan=mode==='Pomodoro'?(task?.estimated_minutes??options.focusMin):null;
  const seconds=s?(s.planned_seconds===null?active:Math.max(0,s.planned_seconds-active)):rest?
    Math.ceil(Math.max(0,rest.endsAt===null?rest.remaining:rest.endsAt-now)/1000):(plan??0)*60;
  const history=w.focusSessions??[],day=localDay();
  const old=legacy<{id:string;date:string;minutes:number;completedAt:number;task_title?:string;active_seconds?:number}[]>('diolino-focus-sessions',[]);
  const today=history.filter(r=>r.status==='completed'&&r.days[day]>0),oldToday=old.filter(r=>r.date===day);
  const minutes=today.reduce((sum,r)=>sum+r.days[day]/60000,0)+oldToday.reduce((sum,r)=>sum+(r.active_seconds??r.minutes*60)/60,0);
  const locked=!store.loaded||store.saving;
  const clearHistory=async()=>{
    if(!window.confirm('Limpar o histórico de Foco? Os lançamentos de estudo permanecem.'))return;
    if(await save(v=>({...v,focusSessions:[]})))localStorage.removeItem('diolino-focus-sessions');
  };
  return <>
    {store.error&&<p role="alert">{store.error}</p>}
    <div className="focus-layout"><section className="panel focus-clock-panel">
      <h2>{s?.mode??(rest?(rest.long?'Pausa longa':'Pausa curta'):'Foco')}</h2>
      <div className="focus-ring"><div><strong role="timer" aria-live="off">{timer(seconds)}</strong>
        <span aria-live="polite">{s?.status==='paused'?'Pausado':s?.status==='review'?'A confirmar':s?'Em foco':rest?'Pausa':'Pronto'}</span></div></div>
      {s?.task_title&&<p>{s.task_title}</p>}
      {!s&&!rest&&<div className="module-fields"><label>Modo<select value={mode} onChange={e=>setMode(e.target.value as Mode)}>
        <option>Pomodoro</option><option>Flowtime</option><option value="Livre">Foco livre</option></select></label>
        <label>Tarefa<select value={taskId} onChange={e=>setTaskId(e.target.value)}><option value="">Sem vínculo</option>
          {tasks.map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select></label>
        <button disabled={locked} onClick={()=>void start(mode,task,plan)}>Iniciar foco</button>
        <button disabled={locked} onClick={()=>void save(v=>({...v,focusBreak:{long:false,length:options.shortBreakMin*60000,remaining:options.shortBreakMin*60000,endsAt:Date.now()+options.shortBreakMin*60000}}))}>Iniciar pausa</button></div>}
      {rest&&!s&&<div className="focus-controls"><button disabled={locked} onClick={()=>void save(v=>{
        const b=v.focusBreak;if(!b)return v;const now=Date.now();
        return {...v,focusBreak:b.endsAt?{...b,remaining:Math.max(0,b.endsAt-now),endsAt:null}:{...b,endsAt:now+b.remaining}};
      })}>{rest.endsAt?'Pausar':'Iniciar pausa'}</button><button onClick={()=>void save(v=>({...v,focusBreak:null}))}>Pular pausa</button></div>}
      {s&&<div className="focus-controls">
        {s.status!=='review'&&<><button disabled={locked} onClick={()=>void control(s.status==='paused'?'resume':'pause')}>{s.status==='paused'?'Retomar':'Pausar'}</button>
          <button disabled={locked} onClick={()=>void control('end')}>Encerrar foco</button>
          <button disabled={locked} onClick={()=>{if(window.confirm('Descartar o bloco atual e reiniciar a contagem?'))void controller.restart()}}>Reiniciar</button></>}
        {s.status==='review'&&<><p>Tempo ativo: {timer(s.active_seconds)}</p><label><input type="checkbox" checked={asStudy} onChange={e=>setStudy(e.target.checked)}/> Registrar como estudo médico</label>
           {s.mode==='Flowtime'&&<label>Pausa após Flowtime (min, 0 para pular)<input type="number" min={0} max={120} value={flowBreak} onChange={e=>setFlowBreak(e.target.value)}/></label>}
          <button disabled={locked||s.mode==='Flowtime'&&(!flowBreak||!Number.isInteger(Number(flowBreak))||Number(flowBreak)<0||Number(flowBreak)>120)}
            onClick={()=>void complete(false,asStudy,s.mode==='Flowtime'?Number(flowBreak):undefined)}>Confirmar</button></>}
        <button disabled={locked} onClick={()=>{if(window.confirm('Descartar esta sessão de foco?'))void complete(true,false)}}>Descartar</button>
      </div>}
    </section><section className="panel"><h2>Seu ritmo de hoje</h2><p>{today.length+oldToday.length} sessões · {Number(minutes.toFixed(1))} min de foco</p>
      <details><summary>Configurar temporizador e avisos</summary><form className="module-fields" onSubmit={async e=>{
        e.preventDefault();const f=new FormData(e.currentTarget);
        let notify=f.has('notify');if(notify && 'Notification' in window){try{notify=await Notification.requestPermission()==='granted'}catch{notify=false}}
        const next:Preferences={focusMin:Number(f.get('focusMin')),shortBreakMin:Number(f.get('shortBreakMin')),longBreakMin:Number(f.get('longBreakMin')),
          longBreakEvery:Number(f.get('longBreakEvery')),breaks:f.get('breaks') as Preferences['breaks'],sound:f.has('sound'),notify};
        await save(v=>({...v,focusOptions:next}));
      }}>
        {([['focusMin','Foco (min)',1,120],['shortBreakMin','Pausa curta (min)',1,60],['longBreakMin','Pausa longa (min)',1,60],['longBreakEvery','Ciclos até pausa longa',2,8]] as const)
          .map(([key,label,min,max])=><label key={key}>{label}<input name={key} type="number" required min={min} max={max} defaultValue={options[key]}/></label>)}
        <label>Após confirmar<select name="breaks" defaultValue={options.breaks}><option value="suggest">Sugerir pausa</option><option value="auto">Iniciar pausa</option><option value="manual">Escolher depois</option></select></label>
        <label><input name="sound" type="checkbox" defaultChecked={options.sound}/> Som de transição</label>
        {'Notification' in window&&<label><input name="notify" type="checkbox" defaultChecked={options.notify}/> Notificação do sistema</label>}
        <button disabled={locked}>Salvar preferências</button>
      </form></details></section></div>
    <section className="panel"><h2>Sessões recentes</h2>{history.slice(0,20).map((r:Session)=><p key={r.id}>
      {r.task_title??r.mode} · {timer(r.active_seconds)} · {r.status==='completed'?'Confirmada':'Descartada'} · {new Date(r.ended_at??r.started_at).toLocaleString('pt-BR')}</p>)}
      {old.slice(0,Math.max(0,20-history.length)).map(r=><p key={r.id}>{r.task_title??'Foco anterior'} · {r.minutes} min · {r.date}</p>)}
      {!history.length&&!old.length?<p>Nenhuma sessão registrada.</p>:<button onClick={()=>void clearHistory()}>Limpar histórico</button>}
    </section>
  </>;
}
