export type Point = [string, number];
export type Task = {id:number;title:string;plan:string;state:string;priority:string;due:string|null};
export type Agenda = {id:number;date:string;time:string|null;title:string;duration_min:number|null;state:string};
export type Habit = {id:string;name:string;cells:[string,string][]};
export type Snapshot = {dates:string[];series:Record<'study'|'exercise'|'sleep'|'weight',Point[]>;focus:Record<string,Point[]>;habits:Habit[];forecast:{pending:number;days:{date:string;count:number}[]};recall:Point[];agenda:Agenda[];tasks:Task[];today:{study:number|null;exercise:number|null;sleep:number|null;pending:number}};
export const localDay=(d=new Date())=>[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
function shift(day:string,n:number){const d=new Date(day+'T12:00:00');d.setDate(d.getDate()+n);return localDay(d)}
export function demo(day:string,n:number):Snapshot{
 const dates=Array.from({length:n},(_,i)=>shift(day,i-n+1));
 const points=(f:(i:number)=>number):Point[]=>dates.map((d,i)=>[d,f(i)]);
 const series={study:points(i=>30+(i*17)%65),exercise:points(i=>15+(i*11)%40),sleep:points(i=>6.5+(i%5)*.4),weight:points(i=>80-i*.025)};
 const tasks=['Revisar ECG','Organizar semana','Estudar insuficiência cardíaca','Revisar cartões','Treino','Leitura'].map((title,i)=>({id:i+1,title,plan:i<4?'Medicina':'Pessoal',state:['A fazer','Em andamento','Concluído'][Math.floor(i/2)],priority:i%2?'Normal':'Alta',due:shift(day,i%3)}));
 return {dates,series,focus:{Pomodoro:points(i=>25*(i%3+1)),Flowtime:points(i=>15+i%4*8)},habits:['Leitura','Exercício','Estudos'].map((name,j)=>({id:String(j),name,cells:Array.from({length:30},(_,i)=>[shift(day,i-29),['done','done','unknown','missed','done'][(i+j)%5]])})),forecast:{pending:12,days:Array.from({length:7},(_,i)=>({date:shift(day,i),count:5+(i*7)%20}))},recall:dates.slice(-7).map((d,i)=>[d,70+i%3*10]),tasks,agenda:dates.slice(-7).map((d,i)=>({id:i,date:d,time:i%2?'14:00':'08:30',title:['Revisão médica','Treino','Leitura','Planejamento'][i%4],duration_min:45,state:'Pendente'})),today:{study:48,exercise:30,sleep:7.3,pending:12}};
}
