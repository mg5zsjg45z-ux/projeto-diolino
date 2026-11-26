import {useCallback,useEffect,useRef,useState} from 'react';
import {invoke,isTauri} from '@tauri-apps/api/core';
import {localDay,type Agenda,type Snapshot,type StudyRecord,type Task,type Point} from './data';

import {persistWebSection} from './webSection.mjs';
import {migrateTasks, type LegacyTask} from './taskModel';
import type {Preferences} from './Focus';
import {change,newSession,type Session,type Break} from './focusModel';

export type SavedReview=Agenda & {sourceStudy?:StudyRecord};
export type Workspace={agenda:Agenda[];tasks:Task[];studies:StudyRecord[];reviews:SavedReview[];
  focusOptions?:Preferences;dailyMigration?:number;taskIdFloor?:number;activeFocus?:Session|null;focusSessions?:Session[];
  focusBreak?:Break|null;focusCycles?:number;legacyFocusImported?:boolean};
const key='diolino-workspace-v1';
const dailyKey='diolino-daily-tasks';
const empty:Workspace={agenda:[],tasks:[],studies:[],reviews:[]};

async function persist(expected:Workspace|null,next:Workspace) {
  if (isTauri()) await invoke('save_workspace',{expected,value:next});
  else await persistWebSection(key,expected===null?null:JSON.stringify(expected),JSON.stringify(next));
  if(isTauri()) {
    try {localStorage.setItem(key+'.revision',crypto.randomUUID())} catch { /* SQLite already committed. */ }
  }
}
function preference(name:string) {
  const raw=localStorage.getItem(name);
  return raw===null ? null : JSON.parse(raw);
}
async function initializeWorkspace():Promise<Workspace|null> {
  const stored:Workspace|null=isTauri()?await invoke('read_local_section',{key}):preference(key);
  if(stored && ![stored.tasks,stored.agenda,stored.studies,stored.reviews].every(Array.isArray))throw new Error('Registros inválidos.');
  if(stored?.dailyMigration===2 && stored.legacyFocusImported)return stored;
  const candidate=stored??(isTauri()?preference(key):null);
  if(candidate && ![candidate.tasks,candidate.agenda,candidate.studies,candidate.reviews].every(Array.isArray))throw new Error('Cópia local do workspace inválida.');
  let next:Workspace=candidate??empty;
  const old=preference('diolino-focus-timer');
  if(next.dailyMigration!==2) {
    const native=isTauri()?await invoke<LegacyTask[]|null>('read_local_section',{key:dailyKey}):null;
    const legacy:LegacyTask[]=preference(dailyKey+'.sqlite-pending') ?? native ?? preference(dailyKey) ?? [];
    if(!Array.isArray(legacy)||legacy.some(row=>!row||typeof row.id!=='string'||typeof row.text!=='string'||
      typeof row.date!=='string'||!Array.isArray(row.steps)))throw new Error('Tarefas antigas inválidas. A migração foi interrompida.');
    // Keep the original source and its pre-migration copy before changing the workspace.
    if(legacy.length) localStorage.setItem(dailyKey+'.migration-backup-v2',JSON.stringify(legacy));
    const history=preference('diolino-focus-sessions')??[];
    const ids=history.map((s:{task_id?:number})=>s.task_id).concat(old?.task?.taskId).filter(Number.isSafeInteger);
    next=migrateTasks(next,legacy,!!candidate&&localStorage.getItem(dailyKey+'.migrated')==='true',ids,Date.now());
  }
  if(!next.legacyFocusImported) {
    const settings=preference('diolino-focus-settings');
    const minutes=old?.task?.minutes ?? settings?.focusMin ?? 25;
    if(old?.phase==='focus' && (old.running || old.task || old.sessionId || old.remainingMs>0 && old.remainingMs<minutes*60000)) {
      const draft=newSession('Pomodoro',old.task?{id:old.task.taskId??null,title:old.task.title}:null,minutes,'');
      if(typeof old.sessionId==='string')draft.id=old.sessionId;
      if(Number.isSafeInteger(old.startedAt))draft.started_at=old.startedAt;
      if(!(preference('diolino-focus-sessions')??[]).some((row:{id:string})=>row.id===draft.id))
        next={...next,activeFocus:change(draft,'paused','recovered',Date.now(),'Temporizador anterior sem intervalos confirmados')};
    } else if(old?.phase==='shortBreak'||old?.phase==='longBreak') {
      const remaining=old.running?Math.max(0,old.endsAt-Date.now()):old.remainingMs;
      if(remaining>0) next={...next,focusBreak:{remaining,length:remaining,endsAt:null,long:old.phase==='longBreak'}};
    }
    next={...next,legacyFocusImported:true,focusCycles:old?.cycles??0};
  }
  await persist(stored,next);
  return next;
}

export function useWorkspace(refresh:number){
 const [value,setValue]=useState<Workspace|null>(null);
 const [loaded,setLoaded]=useState(false);
 const [saving,setSaving]=useState(false);
 const [error,setError]=useState('');
 const current=useRef<Workspace|null>(null);
 const queue=useRef<Promise<unknown>>(Promise.resolve());
 useEffect(()=>{
   let live=true;
   const read=()=>{
     queue.current=queue.current.then(async()=>{
       if(!live)return;
       try {
         const data=await initializeWorkspace().catch(reason=>{
           if(!String(reason).includes('outra janela'))throw reason;
           return initializeWorkspace();
         });
         if(live){current.current=data;setValue(data);setLoaded(true);setError('')}
       }catch(reason){if(live){setError('Não foi possível abrir os registros. '+String(reason));setLoaded(false)}}
     });
   };
   const updated=(event:StorageEvent)=>{if(event.key===key||event.key===key+'.revision')read()};
   read();
   window.addEventListener('storage',updated);
   return ()=>{live=false;window.removeEventListener('storage',updated)};
 },[refresh]);
 const save=useCallback((edit:(workspace:Workspace)=>Workspace,background=false):Promise<boolean>=>{
   if(!loaded)return Promise.resolve(false);
   const write=async()=>{
     if(!background)setSaving(true);
     try {
       const before=current.current;
       const next=edit(before??empty);
       if(next!==before){await persist(before,next);current.current=next;setValue(next)}
       if(!background)setError('');
       return true;
     } catch(reason){setError('Alteração não confirmada. '+String(reason));return false}
     finally{if(!background)setSaving(false)}
   };
   const result=queue.current.then(write);
   queue.current=result;
   return result;
 },[loaded]);
 return {value:value??empty,loaded,saving,error,save};
}

export function personalSnapshot(workspace:Workspace,day:string,days:number):Snapshot{
 const dates=Array.from({length:days},(_,i)=>{
  const date=new Date(day+'T12:00:00');
  date.setDate(date.getDate()+i-days+1);
  return localDay(date);
 });
 const sums=new Map<string,number>();
 for(const record of workspace.studies)sums.set(record.date,(sums.get(record.date)??0)+record.duration_min);
 const study:Point[]=dates.filter(date=>sums.has(date)).map(date=>[date,sums.get(date)!]);
 return {
  dates,series:{study,exercise:[],sleep:[],weight:[]},focus:{},forecast:{pending:0,days:[]},recall:[],
  agenda:workspace.agenda,tasks:workspace.tasks.filter(task=>!task.archived_at),studyRecords:[...workspace.studies].sort((a,b)=>b.date.localeCompare(a.date)||(b.time??'').localeCompare(a.time??'')),
  today:{study:sums.get(day)??null,exercise:null,sleep:null,pending:0},
 };
}
