import type { Task, TaskStep } from './data';
import type { Workspace } from './workspace';

export type LegacyTask = {id:string; date:string; text:string; done:boolean; minutes:number|null; steps:TaskStep[]};

export function nextTaskId(tasks: Task[], minimum = 0) {
  return tasks.reduce((max, task) => Math.max(max, task.id), minimum) + 1;
}

export function shouldReconcileLegacyTasks(workspace:Pick<Workspace,'dailyMigration'>,hasPendingCopy:boolean) {
  return workspace.dailyMigration !== 2 || hasPendingCopy;
}

export function setTaskState(task: Task, state: string, now = Date.now()): Task {
  return {...task, state, updated_at:now, completed_at:state === 'Concluído' ? task.completed_at ?? now : null};
}

export function dailyTasks(tasks: Task[], day: string) {
  return tasks.filter(task => !task.archived_at && (task.date === day || task.due === day ||
    (task.state !== 'Concluído' && (!task.due && (!task.date || task.date <= day) || !!task.due && task.due < day))))
    .sort((a,b) => Number(a.state === 'Concluído') - Number(b.state === 'Concluído') ||
      (a.due ?? '9999').localeCompare(b.due ?? '9999') ||
      ['Alta','Normal','Baixa'].indexOf(a.priority) - ['Alta','Normal','Baixa'].indexOf(b.priority) || a.id-b.id);
}

export function migrateTasks(workspace: Workspace, legacy: LegacyTask[], previouslyImported: boolean, existingFocusIds: number[], now: number): Workspace {
  const byId = new Map(legacy.map(row => [row.id,row]));
  const tasks = workspace.tasks.map(task => {
    const old = task.legacy_daily_id && byId.get(task.legacy_daily_id);
    if (old && old.text.trim().length > 120 && task.title === old.text.trim().slice(0,120)) {
      return {...task, title:old.text.trim()};
    }
    return task;
  });
  const imported = new Set(tasks.map(task => task.legacy_daily_id));
  let id = nextTaskId(tasks,existingFocusIds.reduce((a,b)=>Math.max(a,b),0));
  for (const row of legacy) {
    if (imported.has(row.id)) continue;
    tasks.push({id:id++, title:row.text, date:row.date, due:null, plan:'Pessoal', priority:'Normal',
      state:row.done ? 'Concluído' : 'A fazer', steps:row.steps, estimated_minutes:row.minutes,
      legacy_daily_id:row.id, completed_at:null, updated_at:now});
    imported.add(row.id);
  }
  return {...workspace, tasks, taskIdFloor:id-1, dailyMigration:2};
}

export function parseCapture(text:string, day:string) {
  let plan='Pessoal',priority='Normal',due:string|null=null,minutes:number|null=null;
  const words=text.trim().split(/\s+/).filter(word=>{
    if(/^#[\p{L}\p{N}_-]+$/u.test(word)){plan=word.slice(1);return false}
    if(/^p[123]$/i.test(word)){priority=['Alta','Normal','Baixa'][Number(word[1])-1];return false}
    if(/^(hoje|amanhã)$/i.test(word)){
      const d=new Date(day+'T12:00:00');
      if(word.toLowerCase()==='amanhã')d.setDate(d.getDate()+1);
      due=[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
      return false;
    }
    if(/^\d{1,3}m$/i.test(word)){const n=Number(word.slice(0,-1));if(n>0&&n<=120){minutes=n;return false}}
    return true;
  });
  return {title:words.join(' '),plan,priority,due,estimated_minutes:minutes};
}
