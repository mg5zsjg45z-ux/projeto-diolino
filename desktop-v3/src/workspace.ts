import {useCallback,useEffect,useRef,useState} from 'react';
import {invoke,isTauri} from '@tauri-apps/api/core';
import {localDay,type Agenda,type Snapshot,type StudyRecord,type Task,type Point} from './data';

export type SavedReview=Agenda & {sourceStudy?:StudyRecord};
export type Workspace={agenda:Agenda[];tasks:Task[];studies:StudyRecord[];reviews:SavedReview[]};
const key='diolino-workspace-v1';
const empty:Workspace={agenda:[],tasks:[],studies:[],reviews:[]};

export function useWorkspace(refresh:number){
 const [value,setValue]=useState<Workspace|null>(null);
 const [loaded,setLoaded]=useState(false);
 const [saving,setSaving]=useState(false);
 const [error,setError]=useState('');
 const busy=useRef(false);
 const current=useRef<Workspace|null>(null);
 useEffect(()=>{
  let active=true;
  if(busy.current)return;
  setLoaded(false);
  setError('');
  const read=async()=>{
   const data=isTauri()?await invoke<Workspace|null>('read_local_section',{key}):JSON.parse(localStorage.getItem(key)??'null') as Workspace|null;
   if(data!==null&&![data.agenda,data.tasks,data.studies,data.reviews].every(Array.isArray))throw new Error('Estrutura dos registros inválida.');
   if(active){current.current=data;setValue(data);setLoaded(true)}
  };
  read().catch(error=>{if(active)setError('Não foi possível abrir os registros da 3.0. '+String(error))});
  return()=>{active=false};
 },[refresh]);
 const save=useCallback(async(edit:(workspace:Workspace)=>Workspace)=>{
  if(!loaded||busy.current)return false;
  busy.current=true;
  setSaving(true);
  setError('');
  try{
   const expected=current.current;
   const next=edit(expected??empty);
   if(isTauri())await invoke('save_workspace',{expected,value:next});
   else{
    if(localStorage.getItem(key)!==(expected===null?null:JSON.stringify(expected)))throw new Error('Os registros mudaram em outra janela. Use Atualizar.');
    localStorage.setItem(key,JSON.stringify(next));
   }
   current.current=next;
   setValue(next);
   return true;
  }catch(error){
   setError('Alteração não confirmada. '+String(error));
   return false;
  }finally{busy.current=false;setSaving(false)}
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
  dates,series:{study,exercise:[],sleep:[],weight:[]},focus:{},habits:[],forecast:{pending:0,days:[]},recall:[],
  agenda:workspace.agenda,tasks:workspace.tasks,studyRecords:[...workspace.studies].sort((a,b)=>b.date.localeCompare(a.date)||(b.time??'').localeCompare(a.time??'')),
  today:{study:sums.get(day)??null,exercise:null,sleep:null,pending:0},
 };
}
