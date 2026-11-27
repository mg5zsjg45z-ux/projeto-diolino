export type Point = [string, number];
export type TaskStep = {id:string;text:string;done:boolean};
export type Task = {id:number;title:string;plan:string;state:string;priority:string;due:string|null;date?:string|null;estimated_minutes?:number|null;steps?:TaskStep[];archived_at?:number;legacy_daily_id?:string;completed_at?:number|null;created_at?:number;updated_at?:number};
export type Agenda = {id:number;date:string;time:string|null;title:string;duration_min:number|null;state:string};
export type StudyRecord = {focus_session_id?:string;id:number;date:string;time:string|null;topic:string;duration_min:number;format:string;source:string|null;learning:string|null;notes:string|null;attachment_path:string|null;attachment_name:string|null};
export type Snapshot = {dates:string[];series:Record<'study'|'exercise'|'sleep'|'weight',Point[]>;focus:Record<string,Point[]>;forecast:{pending:number;days:{date:string;count:number}[]};recall:Point[];agenda:Agenda[];studyRecords:StudyRecord[];tasks:Task[];today:{study:number|null;exercise:number|null;sleep:number|null;pending:number}};
export const localDay=(d=new Date())=>[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
