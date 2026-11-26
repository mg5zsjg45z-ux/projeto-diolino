import type { Task, StudyRecord } from './data';
import type { Workspace } from './workspace';

export type Mode = 'Pomodoro' | 'Flowtime' | 'Livre';
type EventName = 'started' | 'paused' | 'resumed' | 'ended' | 'completed' | 'discarded' | 'recovered';
type Status = 'running' | 'paused' | 'review' | 'completed' | 'discarded';
export type Session = {
  id:string; mode:Mode; task_id:number|null; task_title:string|null; planned_seconds:number|null;
  started_at:number; ended_at:number|null; status:Status; interruption_reason:string|null;
  owner:string; checkpoint:number; active_seconds:number; active_ms:number; days:Record<string,number>;
  events:{name:EventName; at:number}[];
};
export type Break = {length:number; remaining:number; endsAt:number|null; long:boolean};
export const maxGap = 8000;
export function newSession(mode: Mode, task: Pick<Task,'id'|'title'>|null, minutes:number|null, owner:string, now=Date.now()):Session {
  return {id:crypto.randomUUID(), mode, task_id:task?.id ?? null, task_title:task?.title ?? null,
    planned_seconds:minutes === null ? null : minutes*60, started_at:now, ended_at:null, status:'running',
    interruption_reason:null, owner, checkpoint:now, active_seconds:0, active_ms:0, days:{}, events:[{name:'started',at:now}]};
}
export function change(session:Session, status:Status, event:EventName, now:number, reason:string|null=null):Session {
  return {...session, status, checkpoint:now, interruption_reason:reason ?? session.interruption_reason,
    ended_at:status === 'review' || status === 'discarded' ? session.ended_at ?? now : session.ended_at,
    events:[...session.events,{name:event,at:now}]};
}
export function observe(session:Session, owner:string, now:number):Session {
  if(session.status !== 'running') return session;
  const elapsed = now-session.checkpoint;
  if(elapsed > maxGap || elapsed < 0) return change(session,'paused','recovered',now,'Intervalo sem observação');
  if(owner !== session.owner || !elapsed) return session;
  const duration = session.planned_seconds === null ? elapsed : Math.min(elapsed,session.planned_seconds*1000-session.active_ms);
  const days = {...session.days};
  const end = session.checkpoint + duration;
  for(let at=session.checkpoint; at<end;) {
    const date = new Date(at);
    const day = [date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');
    const midnight = new Date(date.getFullYear(),date.getMonth(),date.getDate()+1).getTime();
    const next = Math.min(midnight,end);
    days[day] = (days[day] ?? 0) + next-at;
    at = next;
  }
  const active_ms = session.active_ms + duration;
  const next = {...session, days, active_ms, active_seconds:Math.floor(active_ms/1000), checkpoint:now};
  return session.planned_seconds !== null && next.active_seconds >= session.planned_seconds
    ? change(next,'review','ended',end) : next;
}

export function studyDurationMinutes(milliseconds:number):number {
  return Math.max(0.1,Math.round(milliseconds/6000)/10);
}

export function finish(workspace:Workspace, id:string, discard:boolean, asStudy:boolean, now:number):Workspace {
  const session=workspace.activeFocus;
  if(!session || session.id!==id || (!discard && session.status!=='review')) return workspace;
  const record=change(session,discard?'discarded':'completed',discard?'discarded':'completed',now);
  const studies=[...workspace.studies];
  const history=workspace.focusSessions ?? [];
  if(history.some(row=>row.id===id))return {...workspace,activeFocus:null};
  if(asStudy && !discard) {
    let studyId=studies.reduce((max,row)=>Math.max(max,row.id),0);
    for(const [date,ms] of Object.entries(record.days)) {
      if(!ms)continue;
      const entry:StudyRecord={id:++studyId,date,time:null,topic:record.task_title ?? 'Foco',duration_min:studyDurationMinutes(ms),
        format:record.mode,source:'Foco',learning:null,notes:null,attachment_path:null,attachment_name:null,focus_session_id:id};
      studies.push(entry);
    }
  }
  return {...workspace, studies, activeFocus:null, focusSessions:[record,...history]};
}
