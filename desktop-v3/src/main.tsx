import {personalSnapshot,useWorkspace,type SavedReview} from './workspace';
import {BackupPanel} from './BackupPanel';
import {useLocalSection} from './localSection';
import {shiftCalendarDate} from './calendar.mjs';
import React,{Suspense,lazy,useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {invoke,isTauri} from '@tauri-apps/api/core';
import {open as openFileDialog} from '@tauri-apps/plugin-dialog';
import {LayoutDashboard,CalendarDays,Kanban,Brain,HeartPulse,Timer,Target,Palette,Moon,RefreshCw,Activity,BookOpen,ShieldCheck,LibraryBig,FileText,Plus,Pencil,Trash2,Check,Save,X,ChevronLeft,ChevronRight,CalendarPlus,FolderOpen,Undo2,CircleAlert,Circle,CircleDot,CircleCheck,GripVertical,Flag,Inbox,CalendarClock,Maximize2,Minimize2,Utensils,HardDrive,ListTodo} from 'lucide-react';
import {localDay,type Point,type Agenda,type Task,type StudyRecord} from './data';
import {Plot} from './Plot';
import {Focus,startTaskFocus} from './Focus';
import {DailyTasks} from './DailyTasks';
import {Habits} from './Habits';
import {BibleReader} from './BibleReader';
const Nutrition=lazy(()=>import('./Nutrition').then(module=>({default:module.Nutrition})));
import {StrengthPlan} from './StrengthPlan';
import {ModalDialog} from './ModalDialog';
import './styles.css';
const navigation=[['Hoje',LayoutDashboard],['Agenda',CalendarDays],['Planos',Kanban],['Atividade Física',Activity],['Alimentação',Utensils],['Estudos',Brain],['Bíblia',BookOpen],['Biblioteca',LibraryBig],['Saúde',HeartPulse],['Foco',Timer],['Hábitos',Target],['Tarefas',ListTodo],['Backup',HardDrive]] as const;
type LibraryItem={id:string;path:string;name:string};
const loadLibrary=():LibraryItem[]=>{try{const value=JSON.parse(localStorage.getItem('diolino-library')??'[]');return Array.isArray(value)?value.filter((item):item is LibraryItem=>!!item&&typeof item.id==='string'&&typeof item.path==='string'&&typeof item.name==='string'):[]}catch{return[]}};
type HealthEntry={id:number;date:string;activity:string|null;exerciseMin:number|null;sleepHours:number|null;weightKg:number|null;notes:string|null};
type HealthGoals={exerciseMin:number|null;sleepHours:number|null};
const loadHealthEntries=(key='diolino-health-entries'):HealthEntry[]=>{try{const value=JSON.parse(localStorage.getItem(key)??'[]');return Array.isArray(value)?value.filter((item):item is HealthEntry=>!!item&&typeof item.id==='number'&&typeof item.date==='string'&&item.source!=='Demonstração').map(item=>{const {source,...clean}=item as HealthEntry&{source?:string};return clean}):[]}catch{return[]}};
const loadHealthGoals=(key='diolino-health-goals'):HealthGoals=>{try{const value=JSON.parse(localStorage.getItem(key)??'{}');return {exerciseMin:typeof value.exerciseMin==='number'?value.exerciseMin:null,sleepHours:typeof value.sleepHours==='number'?value.sleepHours:null}}catch{return {exerciseMin:null,sleepHours:null}}};
type CalendarView='Mês'|'Semana'|'Dia'|'Ano';
const iso=(d:Date)=>[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
const addDays=(value:string,n:number)=>{const d=new Date(value+'T12:00:00');d.setDate(d.getDate()+n);return iso(d)};
const monthDates=(year:number,month:number)=>{const first=new Date(year,month,1,12),start=new Date(year,month,1,12);start.setDate(1-((first.getDay()+6)%7));return Array.from({length:42},(_,i)=>{const d=new Date(start);d.setDate(start.getDate()+i);return iso(d)})};
import {themes,loadTheme,saveTheme,type Theme} from './themes';
import './themes.css';

function App(){
 const [kanbanExpanded,setKanbanExpanded]=useState(false);
 const [backupLocked,setBackupLocked]=useState(false);
 const [backupResult]=useState(()=>sessionStorage.getItem('diolino-backup-result')??'');
 const [page,setPage]=useState(backupResult?'Backup':'Hoje'),[theme,setTheme]=useState<Theme>(loadTheme),[cliOutput,setCliOutput]=useState(''),[cliPath,setCliPath]=useState(''),[library,setLibrary]=useState<LibraryItem[]>(loadLibrary);
 useEffect(()=>{sessionStorage.removeItem('diolino-backup-result')},[]);
 const [feedback,setFeedback]=useState('');
 const [selectedTask,setSelectedTask]=useState<number|null>(null);
 const [draggingTask,setDraggingTask]=useState<number|null>(null);
 const [landedTask,setLandedTask]=useState<number|null>(null);
 const [dropColumn,setDropColumn]=useState<string|null>(null);
 useEffect(()=>{
  if(!feedback)return;
  const timer=window.setTimeout(()=>setFeedback(''),3400);
  return()=>window.clearTimeout(timer);
 },[feedback]);
 const healthEntriesKey='diolino-health-entries';const healthGoalsKey='diolino-health-goals';const [healthEntries,setHealthEntries,healthEntriesError]=useLocalSection(healthEntriesKey,()=>loadHealthEntries(healthEntriesKey)),[healthDraftId,setHealthDraftId]=useState<number|null>(null),[healthOpen,setHealthOpen]=useState(false),[healthGoals,setHealthGoals,healthGoalsError]=useLocalSection(healthGoalsKey,()=>loadHealthGoals(healthGoalsKey)),[healthGoalsOpen,setHealthGoalsOpen]=useState(false),[healthGoalsForm,setHealthGoalsForm]=useState({exerciseMin:'',sleepHours:''}),[healthForm,setHealthForm]=useState({date:localDay(),activity:'',exerciseMin:'',sleepHours:'',weightKg:'',notes:''}),[day,setDay]=useState(localDay()),[days,setDays]=useState(7),[error,setError]=useState(''),[refresh,setRefresh]=useState(0),[agendaDraft,setAgendaDraft]=useState<Agenda|null>(null),[agendaOpen,setAgendaOpen]=useState(false),[agendaView,setAgendaView]=useState<CalendarView>('Mês'),[agendaForm,setAgendaForm]=useState({date:localDay(),time:'09:00',title:'',duration_min:'45',state:'Pendente'}),[taskDraft,setTaskDraft]=useState<Task|null>(null),[taskOpen,setTaskOpen]=useState(false),[taskForm,setTaskForm]=useState({title:'',plan:'Pessoal',state:'A fazer',priority:'Normal',due:day}),[studyDraft,setStudyDraft]=useState<StudyRecord|null>(null),[studyOpen,setStudyOpen]=useState(false),[studyForm,setStudyForm]=useState({date:localDay(),time:'08:30',topic:'',duration_min:'45',format:'Leitura',source:'',learning:'',notes:''}),[reviewDraft,setReviewDraft]=useState<StudyRecord|null>(null),[reviewOpen,setReviewOpen]=useState(false),[reviewForm,setReviewForm]=useState({date:addDays(localDay(),1),time:'09:00',duration_min:'30'});
 const workspace=useWorkspace(refresh);
 const data=personalSnapshot(workspace.value,day,days);
 const editable=workspace.loaded&&!workspace.saving;
 useEffect(()=>{
  for(const key of ['diolino-demo-health-entries','diolino-demo-health-goals'])localStorage.removeItem(key);
  try {
   const key='diolino-health-entries';
   const raw=localStorage.getItem(key);
   if(raw!==null){
    const cleaned=JSON.stringify(loadHealthEntries());
    if(cleaned!==raw){
     localStorage.setItem(key,cleaned);
     if(localStorage.getItem(key+'.sqlite-pending')!==null)localStorage.setItem(key+'.sqlite-pending',cleaned);
    }
   }
  } catch { /* Dados inválidos continuam disponíveis para recuperação manual. */ }
 },[]);
 useEffect(()=>{setError('')},[page,day,days,refresh]);
 const palette=themes[theme];
 useEffect(()=>saveTheme(theme),[theme]);
 useEffect(()=>localStorage.setItem('diolino-library',JSON.stringify(library)),[library]);
 const format=(v:number|null|undefined,suffix='')=>v==null?'—':v.toLocaleString('pt-BR',{maximumFractionDigits:1})+suffix;
 const plot=(title:string,unit:string,points:Point[],color:string,type:'line'|'bar'='bar',dates=data?.dates??[],max?:number)=><Plot title={title} unit={unit} series={[{name:title,points,color,type}]} dates={dates} theme={theme} max={max}/>;
 const status:Record<string,string>={done:'Cumprido',missed:'Não realizado',unknown:'Sem registro',inactive:'Não ativo'};
 const show=(name:string)=>page===name;
 const exercisePage=show('Atividade Física');
 const personalModule=show('Bíblia')||show('Alimentação')||show('Backup')||show('Tarefas')||show('Foco');
 const exerciseDraft=healthEntries.find(entry=>entry.id===healthDraftId);
 const sharedExercise=exercisePage&&!!exerciseDraft&&(exerciseDraft.sleepHours!==null||exerciseDraft.weightKg!==null);
 const visibleHealthEntries=exercisePage?healthEntries.filter(entry=>entry.exerciseMin!==null):healthEntries;
 const [savedReviews,setSavedReviews,reviewsError]=useLocalSection<SavedReview[]>('diolino-preview-reviews',()=>{
  try {
   const stored=JSON.parse(localStorage.getItem('diolino-preview-reviews')??'[]');
   return Array.isArray(stored)?stored:[];
  } catch {return []}
 });
 const reviews=[...savedReviews,...workspace.value.reviews];
 const [reviewSource,setReviewSource]=useState<StudyRecord|null>(null);
 const [bibleDays,setBibleDays,bibleError]=useLocalSection<string[]>('diolino-bible-days',()=>{
  try {
   const dates:unknown=JSON.parse(localStorage.getItem('diolino-bible-days')??'[]');
   return Array.isArray(dates)?dates.filter(date=>typeof date==='string'):[];
  } catch {return []}
 });
 const bibleDone=bibleDays.includes(day);
 const bibleHistory=Array.from({length:7},(_,index)=>addDays(day,index-6));
 const bibleTotal=bibleHistory.filter(date=>bibleDays.includes(date)).length;
 const toggleBibleDay=()=>setBibleDays(current=>current.includes(day)
  ?current.filter(date=>date!==day):[...current,day]);
 const [scheduledReview,setScheduledReview]=useState<Agenda|null>(null);
 const openReviewSource=(id:number)=>{
  const source=reviews.find(review=>review.id===id)?.sourceStudy;
  if(!source)return;
  setReviewSource(source);
  setDay(source.date);
  setPage('Estudos');
 };
 const agendaEntries=[...workspace.value.agenda,...reviews];
 const upcoming=agendaEntries.filter(event=>event.date>=day&&event.state==='Pendente')
  .sort((a,b)=>a.date.localeCompare(b.date)||(a.time??'99:99').localeCompare(b.time??'99:99'));
 const openAgendaDay=(date:string)=>{setAgendaView('Dia');setDay(date);setPage('Agenda')};
 const openAgenda=(event?:Agenda)=>{const item=event??{id:0,date:day,time:'09:00',title:'',duration_min:45,state:'Pendente'};setAgendaDraft(event??null);setAgendaForm({date:item.date,time:item.time??'',title:item.title,duration_min:item.duration_min==null?'':String(item.duration_min),state:item.state});setAgendaOpen(true)};
 const agendaDays=()=>{if(agendaView==='Dia')return [day];if(agendaView==='Semana'){const d=new Date(day+'T12:00:00');return Array.from({length:7},(_,i)=>addDays(day,-((d.getDay()+6)%7)+i))}return monthDates(Number(day.slice(0,4)),Number(day.slice(5,7))-1)};
 const shiftCalendar=(n:number)=>setDay(shiftCalendarDate(day,n,agendaView));
 const eventHour=(time:string|null)=>time&&/^([01][0-9]|2[0-3]):[0-5][0-9]/.test(time)?time.slice(0,2):null;
 const eventCards=(date:string,hour?:string|null)=>agendaEntries.filter(a=>a.date===date&&(hour===undefined||eventHour(a.time)===hour)).sort((a,b)=>(a.time??'99:99').localeCompare(b.time??'99:99')).map(a=><article className="event" key={a.id}><small>{a.time??'Sem horário'} {a.duration_min&&'· '+a.duration_min+' min'}</small><b>{a.title}</b><small>{a.state}</small>{editable&&<div className="event-actions">{reviews.some(review=>review.id===a.id&&review.sourceStudy)&&<button onClick={()=>openReviewSource(a.id)}><BookOpen size={16} aria-hidden="true"/> Ver estudo de origem</button>}<button onClick={()=>openAgenda(a)}><Pencil size={16} aria-hidden="true"/> Editar</button><button onClick={()=>void removeAgenda(a)}><Trash2 size={16} aria-hidden="true"/> Remover</button></div>}</article>);
 const removeAgenda=async(item:Agenda)=>{
  if(!editable)return;
   if(savedReviews.some(event=>event.id===item.id)){
   setSavedReviews(current=>current.filter(event=>event.id!==item.id));
  }else if(await workspace.save(current=>({...current,agenda:current.agenda.filter(event=>event.id!==item.id),reviews:current.reviews.filter(event=>event.id!==item.id)}))){
   setFeedback('Evento removido.');
  }
 };
 const saveAgenda=async(e:React.FormEvent)=>{
  e.preventDefault();
  if(!editable||!agendaForm.title.trim())return;
  const item:Agenda={id:agendaDraft?.id??Math.max(0,...agendaEntries.map(a=>a.id))+1,date:agendaForm.date,time:agendaForm.time||null,title:agendaForm.title.trim(),duration_min:agendaForm.duration_min?Number(agendaForm.duration_min):null,state:agendaForm.state};
  const editReviews=(current:SavedReview[])=>current.map(event=>event.id===item.id?{...event,...item}:event);
  const editEvents=(current:Agenda[])=>[...current.filter(event=>event.id!==item.id),item];
   if(savedReviews.some(event=>event.id===item.id)){
   setSavedReviews(editReviews);
   setAgendaOpen(false);
   return;
  }else if(!await workspace.save(current=>item.id<0?{...current,reviews:editReviews(current.reviews)}:{...current,agenda:editEvents(current.agenda)}))return;
  setAgendaOpen(false);
  setFeedback('Agenda atualizada.');
 };
 const openTask=(task?:Task)=>{setTaskDraft(task??null);setTaskForm(task?{title:task.title,plan:task.plan,state:task.state,priority:task.priority,due:task.due??''}:{title:'',plan:'Pessoal',state:'A fazer',priority:'Normal',due:day});setTaskOpen(true)};
 const clearTaskDrag=()=>{setDraggingTask(null);setDropColumn(null)};
 const updateTasks=async(update:(tasks:Task[])=>Task[])=>{
  if(!editable)return false;
  return workspace.save(current=>({...current,tasks:update(current.tasks)}));
 };
 const moveTask=async(id:number,state:string)=>{
  if(!data?.tasks.some(task=>task.id===id&&task.state!==state))return;
  if(!await updateTasks(tasks=>tasks.map(task=>task.id===id?{...task,state}:task)))return;
  setSelectedTask(id);
  setLandedTask(id);
  setFeedback('Tarefa movida para '+state+'.');
 };
 const saveTask=async(e:React.FormEvent)=>{
  e.preventDefault();
  if(!editable||!data||!taskForm.title.trim())return;
  const task:Task={...(taskDraft??{}),id:taskDraft?.id??Math.max(0,...data.tasks.map(t=>t.id))+1,title:taskForm.title.trim(),plan:taskForm.plan.trim()||'Pessoal',state:taskForm.state,priority:taskForm.priority,due:taskForm.due||null};
  if(!await updateTasks(tasks=>[...tasks.filter(t=>t.id!==task.id),task]))return;
  setTaskOpen(false);
   setFeedback('Tarefa salva neste dispositivo.');
 };
  const saveHealth=(e:React.FormEvent)=>{e.preventDefault();const exerciseMin=healthForm.exerciseMin?Number(healthForm.exerciseMin):null,sleepHours=healthForm.sleepHours?Number(healthForm.sleepHours):null,weightKg=healthForm.weightKg?Number(healthForm.weightKg):null;if(exercisePage?exerciseMin===null:exerciseMin===null&&sleepHours===null&&weightKg===null){setError(exercisePage?'Informe a duração da atividade.':'Preencha pelo menos um dado de saúde.');return}const entry:HealthEntry={id:healthDraftId??Date.now(),date:healthForm.date,activity:healthForm.activity.trim()||null,exerciseMin,sleepHours,weightKg,notes:healthForm.notes.trim()||null};setHealthEntries(current=>healthDraftId===null?[...current,entry]:current.map(item=>item.id===healthDraftId?entry:item));setHealthDraftId(null);setHealthForm({date:day,activity:'',exerciseMin:'',sleepHours:'',weightKg:'',notes:''});setHealthOpen(false);setFeedback('Registro de saúde salvo neste dispositivo.')};
 const editHealth=(entry:HealthEntry)=>{setHealthDraftId(entry.id);setHealthForm({date:entry.date,activity:entry.activity??'',exerciseMin:entry.exerciseMin===null?'':String(entry.exerciseMin),sleepHours:entry.sleepHours===null?'':String(entry.sleepHours),weightKg:entry.weightKg===null?'':String(entry.weightKg),notes:entry.notes??''});setError('');setHealthOpen(true)};
 const saveHealthGoals=(e:React.FormEvent)=>{e.preventDefault();setHealthGoals({exerciseMin:healthGoalsForm.exerciseMin?Number(healthGoalsForm.exerciseMin):null,sleepHours:healthGoalsForm.sleepHours?Number(healthGoalsForm.sleepHours):null});setHealthGoalsOpen(false);setFeedback('Metas salvas neste dispositivo.')};
 const healthPoints=(field:'exerciseMin'|'sleepHours'|'weightKg'):Point[]=>{const grouped=new Map<string,HealthEntry[]>();for(const entry of healthEntries){if(entry[field]===null)continue;grouped.set(entry.date,[...(grouped.get(entry.date)??[]),entry])}return [...grouped.entries()].map(([date,entries])=>[date,field==='exerciseMin'?entries.reduce((sum,entry)=>sum+(entry.exerciseMin??0),0):field==='sleepHours'?entries.reduce((sum,entry)=>sum+(entry.sleepHours??0),0)/entries.length:(entries.sort((a,b)=>a.id-b.id)[entries.length-1]?.weightKg??0)] as Point)};
 const todayHealthEntries=healthEntries.filter(entry=>entry.date===day),todayExerciseEntries=todayHealthEntries.filter(entry=>entry.exerciseMin!==null),todaySleepEntries=todayHealthEntries.filter(entry=>entry.sleepHours!==null);
 const weekStart=addDays(day,-6),weekHealthEntries=healthEntries.filter(entry=>entry.date>=weekStart&&entry.date<=day),weekExercise=weekHealthEntries.reduce((sum,entry)=>sum+(entry.exerciseMin??0),0),weekSleepEntries=weekHealthEntries.filter(entry=>entry.sleepHours!==null),weekSleep=weekSleepEntries.length?weekSleepEntries.reduce((sum,entry)=>sum+(entry.sleepHours??0),0)/weekSleepEntries.length:null,lastWeight=[...healthEntries].filter(entry=>entry.weightKg!==null).sort((a,b)=>b.date.localeCompare(a.date)||b.id-a.id)[0]??null;
 const openHealth=()=>{setHealthDraftId(null);setHealthForm({date:day,activity:'',exerciseMin:'',sleepHours:'',weightKg:'',notes:''});setError('');setHealthOpen(true)};
 const openStudy=(record?:StudyRecord)=>{setStudyDraft(record??null);setStudyForm(record?{date:record.date,time:record.time??'',topic:record.topic,duration_min:String(record.duration_min),format:record.format,source:record.source??'',learning:record.learning??'',notes:record.notes??''}:{date:day,time:'08:30',topic:'',duration_min:'45',format:'Leitura',source:'',learning:'',notes:''});setStudyOpen(true)};
 const runLibraryTool=async(tool:'wordcraft'|'pdfcraft'|'gridcraft',path:string)=>{try{const output=await invoke<string>('run_library_cli',{tool,path});setCliPath(path);setCliOutput(output||'O CLI concluiu sem texto de saída.')}catch(e){setError(String(e))}};
 const openLibraryDocument=async(path:string)=>{try{await invoke<void>('open_library_document',{path})}catch(e){setError(String(e))}};
 const addLibraryFiles=async()=>{if(!isTauri()){setError('Abra a prévia Diolino para selecionar arquivos.');return}const selected=await openFileDialog({multiple:true,directory:false,title:'Adicionar documentos à Biblioteca',filters:[{name:'Documentos e planilhas',extensions:['pdf','txt','doc','docx','odt','rtf','md','xlsx','xls','csv','tsv','ods']}]});if(!selected)return;const paths=Array.isArray(selected)?selected:[selected];setLibrary(current=>[...current,...paths.filter(path=>!current.some(item=>item.path===path)).map((path,index)=>({id:`${Date.now()}-${index}`,path,name:path.split(/[\\/]/).pop()??path}))])};
  const saveStudy=async(e:React.FormEvent)=>{e.preventDefault();if(!editable||!data||!studyForm.topic.trim())return;const record:StudyRecord={id:studyDraft?.id??Math.max(0,...data.studyRecords.map(r=>r.id))+1,date:studyForm.date,time:studyForm.time||null,topic:studyForm.topic.trim(),duration_min:Number(studyForm.duration_min),format:studyForm.format,source:studyForm.source.trim()||null,learning:studyForm.learning.trim()||null,notes:studyForm.notes.trim()||null,attachment_path:studyDraft?.attachment_path??null,attachment_name:studyDraft?.attachment_name??null};const records=[...data.studyRecords.filter(r=>r.id!==record.id),record].sort((a,b)=>b.date.localeCompare(a.date)||(b.time??'').localeCompare(a.time??''));if(!await workspace.save(current=>({...current,studies:records})))return;setStudyOpen(false);setFeedback('Estudo salvo neste dispositivo.')};
  const removeStudy=async(record:StudyRecord)=>{if(!editable||!data)return;const records=data.studyRecords.filter(r=>r.id!==record.id);await workspace.save(current=>({...current,studies:records}))};
 const openReview=(record:StudyRecord)=>{setReviewDraft(record);setReviewForm({date:addDays(day,1),time:'09:00',duration_min:'30'});setReviewOpen(true)};
 const saveReview=async(e:React.FormEvent)=>{
  e.preventDefault();
  if(!editable||!reviewDraft)return;
  const event:SavedReview={
   sourceStudy:reviewDraft,
   id:Math.min(0,...reviews.map(review=>review.id))-1,
   date:reviewForm.date,time:reviewForm.time||null,
   title:`Revisão · ${reviewDraft.topic}`.slice(0,120),
   duration_min:Number(reviewForm.duration_min)||30,state:'Pendente',
  };
   if(!await workspace.save(current=>({...current,reviews:[...current.reviews,event]})))return;
  setScheduledReview(event);
  setReviewOpen(false);
  setReviewDraft(null);
 };
 return <div className={'app theme-'+theme}><aside><div className="brand"><span><Activity aria-hidden="true" size={20}/></span><div>Diolino<small>3.0 · Alfa</small></div></div><div className="nav-label">ESPAÇO PESSOAL</div><nav>{navigation.map(([name,Icon])=><button key={name} disabled={backupLocked||workspace.saving} className={page===name?'active':''} aria-current={page===name?'page':undefined} onClick={()=>setPage(name)}><Icon aria-hidden="true" size={20}/>{name}</button>)}</nav><div className="aside-bottom"><ShieldCheck aria-hidden="true" size={18}/><span>Offline · dados locais</span></div></aside><main><header><div><p className="eyebrow">Módulos</p><h1>{page==='Hoje'?'Minha central diária':page}</h1><p className="muted">Rotina e planejamento</p></div><label className="theme-select"><Palette aria-hidden="true" size={18}/> Tema <select aria-label="Tema visual" value={theme} onChange={e=>setTheme(e.target.value as Theme)}>{Object.entries(themes).map(([key,t])=><option key={key} value={key}>{t.label}</option>)}</select></label></header>{!show('Backup')&&!show('Tarefas')&&<div className="toolbar"><label>Data <input type="date" value={day} onChange={e=>{if(e.target.value)setDay(e.target.value)}}/></label>{!show('Bíblia')&&<><div className="segments" aria-label="Período">{[7,30,90].map(n=><button key={n} aria-pressed={days===n} onClick={()=>setDays(n)}>{n} dias</button>)}</div><button className="icon" aria-label="Atualizar" disabled={workspace.saving} onClick={()=>setRefresh(x=>x+1)}><RefreshCw aria-hidden="true" size={18}/></button></>}</div>}{!personalModule&&<div className="notice">Os seus registros ficam salvos neste dispositivo.</div>}{error&&<div role="alert" className="error action-error"><strong><CircleAlert size={16} aria-hidden="true"/> Não foi possível concluir</strong><span>{error}</span><button aria-label="Dispensar mensagem de erro" onClick={()=>setError('')}><X size={18} aria-hidden="true"/></button></div>}
 {(healthEntriesError||healthGoalsError||reviewsError||bibleError)&&<p role="alert" className="error">{healthEntriesError||healthGoalsError||reviewsError||bibleError}</p>}
 <div className="feedback-region"  role="status" aria-live="polite">{feedback&&<div className="action-toast"><span className="success-flash" aria-hidden="true"><Check className="draw-check" size={16} aria-hidden="true"/></span> {feedback}</div>}</div>{show('Bíblia')&&<>
  <section className="panel daily-pillar bible-pillar" aria-labelledby="bible-title">
   <div className="bible-pillar-heading">
    <div>
     <h3 id="bible-title"><BookOpen size={18} aria-hidden="true"/> Estudo bíblico</h3>
     <small>{new Date(day+'T12:00:00').toLocaleDateString('pt-BR')} · Registro local</small>
    </div>
    <div className="event-actions">
     <button className={bibleDone?undefined:'primary-action'} onClick={toggleBibleDay}>
      {bibleDone?<Undo2 size={16} aria-hidden="true"/>:<Check size={16} aria-hidden="true"/>}
      {bibleDone?'Desfazer registro':'Marcar como concluído'}
     </button>
    </div>
   </div>
   <p className="bible-status" data-done={bibleDone||undefined} role="status">
    {bibleDone?<Check size={16} aria-hidden="true"/>:<Circle size={16} aria-hidden="true"/>}
    {bibleDone?'Concluído nesta data':'Sem registro nesta data'}
   </p>
   <div className="bible-history">
    <small><strong>{bibleTotal} de 7 dias</strong> com registro</small>
    <ol aria-label="Histórico dos sete dias até a data selecionada">
     {bibleHistory.map(date=>{
      const completed=bibleDays.includes(date);
      return <li key={date} data-done={completed||undefined} aria-current={date===day?'date':undefined}>
       <time dateTime={date} aria-label={new Date(date+'T12:00:00').toLocaleDateString('pt-BR')}>
        {date.slice(8)}
       </time>
       <span className="bible-day-mark" aria-label={completed?'Concluído':'Sem registro'} role="img">
        {completed?<Check size={12} aria-hidden="true"/>:<span aria-hidden="true">–</span>}
       </span>
      </li>;
     })}
    </ol>
   </div>
  </section>
  <BibleReader/>
 </>}{show('Alimentação')&&<Suspense fallback={<p role="status">Carregando TACO…</p>}><Nutrition key={day} day={day} theme={theme}/></Suspense>}
 {exercisePage&&<StrengthPlan day={day}/>}
 {show('Foco')&&<><h2>Temporizador</h2><Focus onFeedback={setFeedback}/></>}
 {show('Tarefas')&&<DailyTasks tasks={workspace.value.tasks} ready={workspace.loaded&&!workspace.saving} error={workspace.error} onSave={edit=>workspace.save(current=>({...current,tasks:edit(current.tasks)}))} onFocus={(taskId,title,minutes)=>{
  try {
   if(!startTaskFocus(taskId,title,minutes))setFeedback('Já existe um temporizador em andamento.');
   setPage('Foco');
  } catch {setError('Não foi possível iniciar o Foco neste dispositivo.')}
 }}/>}
 {show('Backup')&&<>{backupResult&&<p role="status" className="notice">{backupResult}</p>}<BackupPanel setLocked={setBackupLocked}/></>}
 {!personalModule&&!data&&!error&&<p role="status">Consultando registros locais…</p>}{!personalModule&&data&&<>
 {workspace.error&&<p className="error" role="alert">{workspace.error}</p>}
 {!workspace.loaded&&!workspace.error&&<p role="status">Abrindo registros da 3.0…</p>}
 {page==='Hoje'&&<div className="metrics">{[{label:'Estudo médico',value:data.today.study,goal:60,unit:' min',color:palette.study,icon:BookOpen},{label:'Exercício',value:todayExerciseEntries.length?todayExerciseEntries.reduce((sum,entry)=>sum+(entry.exerciseMin??0),0):data.today.exercise,goal:40,unit:' min',color:palette.exercise,icon:Activity},{label:'Sono',value:todaySleepEntries.length?todaySleepEntries.reduce((sum,entry)=>sum+(entry.sleepHours??0),0)/todaySleepEntries.length:data.today.sleep,goal:null,unit:' h',color:palette.sleep,icon:Moon},{label:'Revisões pendentes',value:reviews.filter(review=>review.state==='Pendente'&&review.date<=day).length,goal:null,unit:'',color:palette.attention,icon:Brain}].map(m=><section className="metric" key={m.label}><div className="metric-label"><m.icon aria-hidden="true" size={18}/>{m.label}</div><strong>{format(m.value,m.unit)}</strong>{m.goal!=null&&m.value!=null?<><progress max={m.goal} value={Math.min(m.goal,m.value)} style={{accentColor:m.color}}/><small>Meta: {m.goal} min</small></>:<small>{m.value==null?'Sem registro':'Registro disponível'}</small>}</section>)}</div>}
 {page==='Hoje'&&<>
  <h2>Próximas ações</h2>
  <div className="charts">
   {[
    {label:'Próximo compromisso',event:upcoming.find(item=>item.id>=0)},
    {label:'Próxima revisão agendada',event:upcoming.find(item=>item.id<0)},
   ].map(({label,event})=><section className="panel" key={label}>
    <h3>{label}</h3>
    {event?<p>{event.title}</p>:<p className="icon-line muted">
     <CalendarClock size={20} aria-hidden="true"/> Nada agendado a partir desta data.
    </p>}
    {event&&<p className="muted">{new Date(event.date+'T12:00:00').toLocaleDateString('pt-BR')} · {event.time??'Sem horário'}</p>}
    <div className="event-actions"><button onClick={()=>openAgendaDay(event?.date??day)}><CalendarDays size={16} aria-hidden="true"/> Ver na Agenda</button></div>
   </section>)}
  </div>
  <h2>Continuar o dia</h2>
  <div className="event-actions">{['Estudos','Foco','Hábitos','Planos'].map(module=><button key={module} onClick={()=>setPage(module)}>Abrir {module}</button>)}</div>
 </>}
 {show('Estudos')&&reviewSource&&<section className="panel" aria-label="Estudo de origem">
  <div className="agenda-heading"><h2>Estudo de origem</h2><button onClick={()=>setReviewSource(null)}>Fechar registro</button></div>
  <h3>{reviewSource.topic}</h3>
  <p>{new Date(reviewSource.date+'T12:00:00').toLocaleDateString('pt-BR')} · {reviewSource.duration_min} min · {reviewSource.format}</p>
  {reviewSource.source&&<p>Material: {reviewSource.source}</p>}
  {reviewSource.learning&&<p>Aprendizados: {reviewSource.learning}</p>}
  {reviewSource.notes&&<p>Observações: {reviewSource.notes}</p>}
  <small>Registro do estudo no momento do agendamento.</small>
 </section>}
 {show('Estudos')&&scheduledReview&&<section className="notice">
  <p role="status">Revisão {'salva neste dispositivo'} para {new Date(scheduledReview.date+'T12:00:00').toLocaleDateString('pt-BR')}.</p>
  <div className="event-actions"><button onClick={()=>{openAgendaDay(scheduledReview.date);setScheduledReview(null)}}><CalendarDays size={16} aria-hidden="true"/> Ver na Agenda</button><button onClick={()=>setScheduledReview(null)}>Dispensar</button></div>
 </section>}
 {show('Estudos')&&<><div className="agenda-heading"><h2>Estudos e revisões</h2>{editable&&<button onClick={()=>openStudy()}><Plus size={16} aria-hidden="true"/> Novo estudo</button>}</div><div className="charts">{plot('Estudo médico','min',data.series.study,palette.study)}{plot('Cartões FSRS agendados','cartões',data.forecast.days.map(x=>[x.date,x.count]),palette.study,'bar',data.forecast.days.map(x=>x.date))}{plot('Recordação observada','%',data.recall,palette.study,'bar',data.recall.map(x=>x[0]),100)}</div><h2>Sessões</h2>{data.studyRecords.length===0?<section className="panel"><p className="icon-line"><BookOpen size={18} aria-hidden="true"/> Nenhum registro de estudo neste período.</p></section>:<div className="study-list">{data.studyRecords.slice(0,30).map(r=><article className="study-record" key={r.id}><div><b>{r.topic}</b><small>{r.date}{r.time&&' · '+r.time} · {r.duration_min} min · {r.format}</small>{r.source&&<small>Material: {r.source}</small>}{r.learning&&<small>Aprendizados: {r.learning}</small>}{r.notes&&<small>{r.notes}</small>}</div><div className="event-actions">{editable&&<><button onClick={()=>openReview(r)}><CalendarPlus size={16} aria-hidden="true"/> Agendar revisão</button><button onClick={()=>openStudy(r)}><Pencil size={16} aria-hidden="true"/> Editar</button><button onClick={()=>removeStudy(r)}><Trash2 size={16} aria-hidden="true"/> Remover</button></>}</div></article>)}</div>}<h2>Revisões</h2>{agendaEntries.filter(a=>a.title.startsWith('Revisão · ')).length===0?<section className="panel"><p>Nenhuma releitura agendada.</p></section>:<div className="study-list">{agendaEntries.filter(a=>a.title.startsWith('Revisão · ')).sort((a,b)=>a.date.localeCompare(b.date)||(a.time??'99:99').localeCompare(b.time??'99:99')).map(a=><article className="study-record" key={a.id}><div><b>{a.title}</b><small>{a.date}{a.time&&' · '+a.time} · {a.duration_min??30} min</small></div><div className="event-actions"><button onClick={()=>{setDay(a.date);setAgendaView('Dia');setPage('Agenda')}}><CalendarDays size={16} aria-hidden="true"/> Ver na Agenda</button></div></article>)}</div>}{reviewOpen&&reviewDraft&&<ModalDialog titleId="review-dialog-title" onClose={()=>setReviewOpen(false)}><form className="agenda-form" onSubmit={saveReview}>{workspace.error&&<p role="alert" className="error">{workspace.error}</p>}<h2 id="review-dialog-title">Agendar revisão</h2><p className="muted">Releitura de: <b>{reviewDraft.topic}</b></p><div className="form-row"><label>Data<input required type="date" value={reviewForm.date} onChange={e=>setReviewForm({...reviewForm,date:e.target.value})}/></label><label>Horário<input type="time" value={reviewForm.time} onChange={e=>setReviewForm({...reviewForm,time:e.target.value})}/></label></div><label>Duração (minutos)<input required type="number" min="1" max="1440" value={reviewForm.duration_min} onChange={e=>setReviewForm({...reviewForm,duration_min:e.target.value})}/></label><div className="form-actions"><button type="button" onClick={()=>setReviewOpen(false)}>Cancelar</button><button type="submit" disabled={!editable}><Save size={16} aria-hidden="true"/> Salvar na Agenda</button></div></form></ModalDialog>}{studyOpen&&<ModalDialog titleId="study-dialog-title" onClose={()=>setStudyOpen(false)}><form className="agenda-form" onSubmit={saveStudy}>{workspace.error&&<p role="alert" className="error">{workspace.error}</p>}<h2 id="study-dialog-title">{studyDraft?'Editar sessão':'Novo estudo'}</h2><label>Tema<input required maxLength={200} value={studyForm.topic} onChange={e=>setStudyForm({...studyForm,topic:e.target.value})}/></label><div className="form-row"><label>Data<input required type="date" value={studyForm.date} onChange={e=>setStudyForm({...studyForm,date:e.target.value})}/></label><label>Horário<input type="time" value={studyForm.time} onChange={e=>setStudyForm({...studyForm,time:e.target.value})}/></label></div><div className="form-row"><label>Duração (min)<input required type="number" min="0.1" max="1440" step="0.1" value={studyForm.duration_min} onChange={e=>setStudyForm({...studyForm,duration_min:e.target.value})}/></label><label>Formato<select value={studyForm.format} onChange={e=>setStudyForm({...studyForm,format:e.target.value})}><option>Leitura</option><option>Vídeo</option><option>Leitura e vídeo</option></select></label></div><label>Material / fonte<input maxLength={300} value={studyForm.source} onChange={e=>setStudyForm({...studyForm,source:e.target.value})}/></label><label>Aprendizados / revisão<textarea rows={3} maxLength={2000} value={studyForm.learning} onChange={e=>setStudyForm({...studyForm,learning:e.target.value})}/></label><label>Observações<textarea rows={2} maxLength={1000} value={studyForm.notes} onChange={e=>setStudyForm({...studyForm,notes:e.target.value})}/></label><div className="form-actions"><button type="button" onClick={()=>setStudyOpen(false)}>Cancelar</button><button type="submit" disabled={!editable}><Save size={16} aria-hidden="true"/> Salvar</button></div></form></ModalDialog>}</>}
 {show('Biblioteca')&&<><div className="agenda-heading"><h2>Biblioteca</h2><button onClick={addLibraryFiles}><Plus size={16} aria-hidden="true"/> Adicionar documentos</button></div><p className="muted">Abra os arquivos originais no aplicativo padrão do Windows ou use os CLIs para extrair texto e dados. Os arquivos permanecem nas pastas onde você os salvou.</p>{library.length===0?<section className="panel"><p className="icon-line"><FolderOpen size={18} aria-hidden="true"/> Nenhum documento na Biblioteca. Adicione PDFs, arquivos Word, textos ou planilhas.</p></section>:<div className="study-list">{library.map(item=>{const name=item.name.toLowerCase(),word=/\.(docx?|txt|odt|rtf|md)$/.test(name),pdf=/\.pdf$/.test(name),grid=/\.(xlsx?|csv|tsv|ods)$/.test(name);return <article className="study-record" key={item.id}><div><b><FileText aria-hidden="true" size={16} style={{verticalAlign:'middle',marginRight:7}}/>{item.name}</b><small>{item.path}</small></div><div className="event-actions"><button onClick={()=>openLibraryDocument(item.path)}><FolderOpen size={16} aria-hidden="true"/> Abrir documento</button>{word&&<button onClick={()=>runLibraryTool('wordcraft',item.path)}>WordCraft CLI</button>}{pdf&&<button onClick={()=>runLibraryTool('pdfcraft',item.path)}>PdfCraft CLI</button>}{grid&&<button onClick={()=>runLibraryTool('gridcraft',item.path)}>GridCraft CLI</button>}<button onClick={()=>setLibrary(current=>current.filter(file=>file.id!==item.id))}><Trash2 size={16} aria-hidden="true"/> Remover da Biblioteca</button></div></article>})}</div>}</>}
 {(show('Saúde')||exercisePage)&&<>
  <div className="agenda-heading"><div><h2>{exercisePage?'Treinos e exercícios':'Saúde e atividade'}</h2></div><div className="event-actions"><button onClick={()=>{setHealthGoalsForm({exerciseMin:healthGoals.exerciseMin===null?'':String(healthGoals.exerciseMin),sleepHours:healthGoals.sleepHours===null?'':String(healthGoals.sleepHours)});setHealthGoalsOpen(true)}}>Metas</button><button onClick={openHealth}><Plus size={16} aria-hidden="true"/> {exercisePage?'Registrar atividade':'Registrar dados'}</button></div></div>
  <p className="muted">Meus registros ficam salvos neste dispositivo.</p>
  <div className="health-summary">
   <section className="metric"><div className="metric-label"><Activity aria-hidden="true" size={18}/>Exercício em {new Date(day+'T12:00:00').toLocaleDateString('pt-BR')}</div><strong>{todayExerciseEntries.length?format(todayExerciseEntries.reduce((sum,entry)=>sum+(entry.exerciseMin??0),0),' min'):'—'}</strong>{healthGoals.exerciseMin!==null&&<><progress max={healthGoals.exerciseMin} value={Math.min(healthGoals.exerciseMin,todayExerciseEntries.reduce((sum,entry)=>sum+(entry.exerciseMin??0),0))} style={{accentColor:palette.exercise}}/><small>Meta definida por você: {healthGoals.exerciseMin} min</small></>}</section>
   {!exercisePage&&<section className="metric"><div className="metric-label"><Moon aria-hidden="true" size={18}/>Sono em {new Date(day+'T12:00:00').toLocaleDateString('pt-BR')}</div><strong>{todaySleepEntries.length?format(todaySleepEntries.reduce((sum,entry)=>sum+(entry.sleepHours??0),0)/todaySleepEntries.length,' h'):'—'}</strong>{healthGoals.sleepHours!==null&&<><progress max={healthGoals.sleepHours} value={Math.min(healthGoals.sleepHours,todaySleepEntries.reduce((sum,entry)=>sum+(entry.sleepHours??0),0)/Math.max(1,todaySleepEntries.length))} style={{accentColor:palette.sleep}}/><small>Meta definida por você: {healthGoals.sleepHours} h</small></>}</section>}
   <section className="metric"><div className="metric-label"><Activity aria-hidden="true" size={18}/>Exercício nos últimos 7 dias</div><strong>{weekExercise?format(weekExercise,' min'):'—'}</strong><small>{weekHealthEntries.filter(entry=>entry.exerciseMin!==null).length} registro(s) no período</small></section>
   {!exercisePage&&<section className="metric"><div className="metric-label"><Activity aria-hidden="true" size={18}/>Peso mais recente</div><strong>{lastWeight?format(lastWeight.weightKg,' kg'):'—'}</strong><small>{lastWeight?new Date(lastWeight.date+'T12:00:00').toLocaleDateString('pt-BR'):'Nenhuma medição registrada'}</small></section>}
  </div>
  <div className="charts">{plot('Exercício','min',healthPoints('exerciseMin'),palette.exercise,'bar',data.dates)}{!exercisePage&&<>{plot('Sono','h',healthPoints('sleepHours'),palette.sleep,'line',data.dates)}{plot('Peso','kg',healthPoints('weightKg'),palette.weight,'line',data.dates)}</>}</div>
  <div className="agenda-heading"><h2>Registros da 3.0</h2><span className="muted">{visibleHealthEntries.length} registro(s)</span></div>
  {visibleHealthEntries.length===0?<section className="panel"><p className="icon-line"><HeartPulse size={18} aria-hidden="true"/> Nenhum registro ainda.</p></section>:<div className="study-list">{[...visibleHealthEntries].sort((a,b)=>b.date.localeCompare(a.date)||b.id-a.id).map(entry=><article className="study-record" key={entry.id}><div><b>{new Date(entry.date+'T12:00:00').toLocaleDateString('pt-BR')}</b>{entry.activity&&<small>Atividade: {entry.activity}</small>}{entry.exerciseMin!==null&&<small>Exercício: {format(entry.exerciseMin,' min')}</small>}{!exercisePage&&entry.sleepHours!==null&&<small>Sono: {format(entry.sleepHours,' h')}</small>}{!exercisePage&&entry.weightKg!==null&&<small>Peso: {format(entry.weightKg,' kg')}</small>}{entry.notes&&<small>{entry.notes}</small>}</div><div className="event-actions"><button onClick={()=>editHealth(entry)}><Pencil size={16} aria-hidden="true"/> Editar</button><button onClick={()=>{if(window.confirm(exercisePage?'Remover esta atividade?':'Remover este registro de saúde?'))setHealthEntries(current=>current.flatMap(item=>item.id!==entry.id?[item]:exercisePage&&(item.sleepHours!==null||item.weightKg!==null)?[{...item,activity:null,exerciseMin:null}]:[]))}}><Trash2 size={16} aria-hidden="true"/> Remover</button></div></article>)}</div>}
  {healthOpen&&<ModalDialog titleId="health-dialog-title" onClose={()=>setHealthOpen(false)}><form className="agenda-form" onSubmit={saveHealth}><h2 id="health-dialog-title">{exercisePage?(healthDraftId===null?'Registrar atividade':'Editar atividade'):(healthDraftId===null?'Registrar dados de saúde':'Editar registro de saúde')}</h2><label>Data<input required disabled={sharedExercise} type="date" value={healthForm.date} onChange={e=>setHealthForm({...healthForm,date:e.target.value})}/></label><label>Atividade<input maxLength={100} placeholder="Ex.: musculação, caminhada" value={healthForm.activity} onChange={e=>setHealthForm({...healthForm,activity:e.target.value})}/></label><div className="form-row"><label>Exercício (min)<input required={exercisePage} type="number" min="1" max="1440" step="1" value={healthForm.exerciseMin} onChange={e=>setHealthForm({...healthForm,exerciseMin:e.target.value})}/></label>{!exercisePage&&<label>Sono (horas)<input type="number" min="0.1" max="24" step="0.1" value={healthForm.sleepHours} onChange={e=>setHealthForm({...healthForm,sleepHours:e.target.value})}/></label>}</div>{!exercisePage&&<label>Peso (kg)<input type="number" min="1" max="500" step="0.1" value={healthForm.weightKg} onChange={e=>setHealthForm({...healthForm,weightKg:e.target.value})}/></label>}<label>Observações<textarea rows={2} maxLength={500} value={healthForm.notes} onChange={e=>setHealthForm({...healthForm,notes:e.target.value})}/></label><div className="form-actions"><button type="button" onClick={()=>{setHealthDraftId(null);setHealthOpen(false)}}>Cancelar</button><button type="submit"><Save size={16} aria-hidden="true"/> {healthDraftId===null?'Salvar registro':'Salvar alterações'}</button></div></form></ModalDialog>}
  {healthGoalsOpen&&<ModalDialog titleId="health-goals-dialog-title" onClose={()=>setHealthGoalsOpen(false)}><form className="agenda-form" onSubmit={saveHealthGoals}><h2 id="health-goals-dialog-title">Metas pessoais</h2><p className="muted">Defina objetivos próprios. Eles servem apenas para acompanhar seus registros.</p><label>Exercício por dia (min)<input type="number" min="1" max="1440" step="1" value={healthGoalsForm.exerciseMin} onChange={e=>setHealthGoalsForm({...healthGoalsForm,exerciseMin:e.target.value})}/></label>{!exercisePage&&<label>Sono por noite (horas)<input type="number" min="0.1" max="24" step="0.1" value={healthGoalsForm.sleepHours} onChange={e=>setHealthGoalsForm({...healthGoalsForm,sleepHours:e.target.value})}/></label>}<div className="form-actions"><button type="button" onClick={()=>setHealthGoalsOpen(false)}>Cancelar</button><button type="submit"><Save size={16} aria-hidden="true"/> Salvar metas</button></div></form></ModalDialog>}
 </>}

 {show('Hábitos')&&<><h2>Rotina e histórico</h2> <Habits selectedDate={day} onFeedback={setFeedback}/></>}
 {show('Planos')&&<><div className="agenda-heading"><h2>Quadro de tarefas</h2><div className="event-actions kanban-toolbar">
 <button type="button" aria-controls="planning-board" aria-expanded={kanbanExpanded}
  onClick={()=>setKanbanExpanded(expanded=>!expanded)}>
  {kanbanExpanded?<Minimize2 size={16} aria-hidden="true"/>:<Maximize2 size={16} aria-hidden="true"/>}
  {kanbanExpanded?'Compactar quadro':'Expandir quadro'}
 </button>
 {editable&&<button onClick={()=>openTask()}><Plus size={16} aria-hidden="true"/> Nova tarefa</button>}</div></div><div id="planning-board" className="kanban" data-density={kanbanExpanded?'expanded':'compact'}>{['A fazer','Em andamento','Concluído'].map((state,i)=>{
 const tasks=data.tasks.filter(task=>task.state===state);
 return <section className="column" key={state}
 data-drop-target={dropColumn===state||undefined}
 onDragOver={event=>{if(draggingTask===null||!editable)return;event.preventDefault();event.dataTransfer.dropEffect='move';setDropColumn(state)}}
 onDragLeave={event=>{if(!event.currentTarget.contains(event.relatedTarget as Node|null))setDropColumn(current=>current===state?null:current)}}
 onDrop={event=>{if(draggingTask===null||!editable)return;event.preventDefault();moveTask(draggingTask,state);clearTaskDrag()}}><h3>{[<Circle size={16} aria-hidden="true"/>,<CircleDot size={16} aria-hidden="true"/>,<CircleCheck size={16} aria-hidden="true"/>][i]}{state} <small>{tasks.length}</small></h3>
 {tasks.length===0&&<div className="kanban-empty">
  <Inbox size={24} aria-hidden="true"/>
  <strong>Nenhuma tarefa</strong>
  {editable&&<small>Arraste uma tarefa para cá</small>}
 </div>}
 {tasks.map(t=><article className="task" key={t.id}
 data-done={t.state==='Concluído'||undefined} data-selected={selectedTask===t.id||undefined} data-dragging={draggingTask===t.id||undefined} data-landed={landedTask===t.id||undefined}
 draggable={editable}
 onDragStart={event=>{
  if(!editable)return;
  event.dataTransfer.effectAllowed='move';
  event.dataTransfer.setData('text/plain',String(t.id));
  setLandedTask(null);
  setDraggingTask(t.id);
  setSelectedTask(t.id);
 }}
 onDragEnd={clearTaskDrag}><small>{editable&&<GripVertical size={16} aria-hidden="true"/>} {t.plan}</small><b>{t.title}</b><div><span className="tag"><Flag size={16} aria-hidden="true"/> {t.priority}</span>{t.due&&<small>{t.due}</small>}</div>{editable&&<div className="event-actions kanban-actions"><button onClick={()=>{setSelectedTask(t.id);openTask(t)}}><Pencil size={16} aria-hidden="true"/> Editar</button><button onClick={()=>void updateTasks(tasks=>tasks.filter(item=>item.id!==t.id))}><Trash2 size={16} aria-hidden="true"/> Remover</button></div>}</article>)}</section>})}</div>{taskOpen&&<ModalDialog titleId="task-dialog-title" onClose={()=>setTaskOpen(false)}><form className="agenda-form" onSubmit={saveTask}>{workspace.error&&<p role="alert" className="error">{workspace.error}</p>}<h2 id="task-dialog-title">{taskDraft?'Editar tarefa':'Nova tarefa'}</h2><label>Tarefa<input required maxLength={120} value={taskForm.title} onChange={e=>setTaskForm({...taskForm,title:e.target.value})}/></label><div className="form-row"><label>Plano / área<input maxLength={80} value={taskForm.plan} onChange={e=>setTaskForm({...taskForm,plan:e.target.value})}/></label><label>Estado<select value={taskForm.state} onChange={e=>setTaskForm({...taskForm,state:e.target.value})}><option>A fazer</option><option>Em andamento</option><option>Concluído</option></select></label></div><div className="form-row"><label>Prioridade<select value={taskForm.priority} onChange={e=>setTaskForm({...taskForm,priority:e.target.value})}><option>Baixa</option><option>Normal</option><option>Alta</option></select></label><label>Prazo<input type="date" value={taskForm.due} onChange={e=>setTaskForm({...taskForm,due:e.target.value})}/></label></div><div className="form-actions"><button type="button" onClick={()=>setTaskOpen(false)}>Cancelar</button><button type="submit" disabled={!editable}><Save size={16} aria-hidden="true"/> Salvar</button></div></form></ModalDialog>}</>}
 {show('Agenda')&&<><div className="agenda-heading"><h2>{new Date(day+'T12:00:00').toLocaleDateString('pt-BR',{month:'long',year:'numeric'})}</h2>{editable&&<button onClick={()=>openAgenda()}><Plus size={16} aria-hidden="true"/> Novo evento</button>}</div><div className="calendar-toolbar"><div className="segments">{(['Mês','Semana','Dia','Ano'] as CalendarView[]).map(v=><button key={v} aria-pressed={agendaView===v} onClick={()=>setAgendaView(v)}>{v}</button>)}</div><div className="calendar-nav"><button onClick={()=>shiftCalendar(-1)} aria-label="Período anterior"><ChevronLeft size={18} aria-hidden="true"/></button><button onClick={()=>setDay(localDay())}>Hoje</button><button onClick={()=>shiftCalendar(1)} aria-label="Próximo período"><ChevronRight size={18} aria-hidden="true"/></button></div></div>{agendaView==='Ano'?<div className="year-grid">{Array.from({length:12},(_,m)=><section className="mini-month" key={m}><button className="mini-month-title" onClick={()=>{setDay(`${day.slice(0,4)}-${String(m+1).padStart(2,'0')}-01`);setAgendaView('Mês')}}>{new Date(Number(day.slice(0,4)),m,1).toLocaleDateString('pt-BR',{month:'long'})}</button><div className="mini-weekdays">{['S','T','Q','Q','S','S','D'].map((w,i)=><span key={i}>{w}</span>)}</div><div className="mini-days">{monthDates(Number(day.slice(0,4)),m).map(d=><button key={d} className={d.slice(0,7)===`${day.slice(0,4)}-${String(m+1).padStart(2,'0')}`?'':'outside'} onClick={()=>{setDay(d);setAgendaView('Dia')}}>{Number(d.slice(8))}</button>)}</div></section>)}</div>:agendaView==='Dia'?<div className="agenda-timeline" aria-label="Horários do dia">{agendaEntries.some(event=>event.date===day&&!eventHour(event.time))&&<section className="agenda-hour"><strong>Sem horário</strong><div>{eventCards(day,null)}</div></section>}{Array.from({length:24},(_,hour)=>String(hour).padStart(2,'0')).map(hour=><section className="agenda-hour" key={hour}><time dateTime={hour+':00'}>{hour}:00</time><div>{eventCards(day,hour)}</div></section>)}</div>:<div className="calendar-grid"><div className="weekdays">{['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'].map(w=><b key={w}>{w}</b>)}</div>{agendaDays().map(d=><section key={d} className={'calendar-day '+(d.slice(0,7)!==day.slice(0,7)?'outside':'')+(d===day?' selected':'')} onClick={()=>setDay(d)}><button className="day-number" onClick={e=>{e.stopPropagation();setDay(d);setAgendaView('Dia')}}>{Number(d.slice(8))}</button>{eventCards(d)}</section>)}</div>}{agendaOpen&&<ModalDialog titleId="agenda-dialog-title" onClose={()=>setAgendaOpen(false)}><form className="agenda-form" onSubmit={saveAgenda}>{workspace.error&&<p role="alert" className="error">{workspace.error}</p>}<h2 id="agenda-dialog-title">{agendaDraft?'Editar evento':'Novo evento'}</h2><label>Evento<input required maxLength={120} value={agendaForm.title} onChange={e=>setAgendaForm({...agendaForm,title:e.target.value})}/></label><div className="form-row"><label>Data<input required type="date" value={agendaForm.date} onChange={e=>setAgendaForm({...agendaForm,date:e.target.value})}/></label><label>Horário<input type="time" value={agendaForm.time} onChange={e=>setAgendaForm({...agendaForm,time:e.target.value})}/></label></div><div className="form-row"><label>Duração (minutos)<input type="number" min="1" max="1440" value={agendaForm.duration_min} onChange={e=>setAgendaForm({...agendaForm,duration_min:e.target.value})}/></label><label>Estado<select value={agendaForm.state} onChange={e=>setAgendaForm({...agendaForm,state:e.target.value})}><option>Pendente</option><option>Concluído</option><option>Cancelado</option></select></label></div><div className="form-actions"><button type="button" onClick={()=>setAgendaOpen(false)}>Cancelar</button><button type="submit" disabled={!editable}><Save size={16} aria-hidden="true"/> Salvar</button></div></form></ModalDialog>}</>}
 </>}{cliOutput&&<ModalDialog titleId="cli-output-dialog-title" onClose={()=>setCliOutput('')}><section className="cli-output"><div className="agenda-heading"><h2 id="cli-output-dialog-title">Resultado da ferramenta</h2><div className="event-actions"><button onClick={()=>openLibraryDocument(cliPath)}><FolderOpen size={16} aria-hidden="true"/> Abrir documento</button><button onClick={()=>setCliOutput('')}>Fechar</button></div></div><pre>{cliOutput}</pre></section></ModalDialog>}<footer>{page==='Agenda'?'Agenda 3.0 · calendário mensal, semanal, diário e anual.':page==='Planos'?'Planos 3.0 · quadro de tarefas.':page==='Estudos'?'Estudos 3.0 · sessões e releituras.':page==='Biblioteca'?'Biblioteca · arquivos originais ficam nas pastas escolhidas; atalhos são salvos neste dispositivo.':'Diolino 3.0 alfa · registros locais deste dispositivo.'}</footer></main></div>
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
