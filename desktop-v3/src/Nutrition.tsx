import {useMemo,useState} from 'react';
import {Plus,Pencil,Trash2} from 'lucide-react';
import catalogue from '../../data/taco/catalogue.json';
import type {Point} from './data';
import {Plot} from './Plot';
import {DailyNutrients} from './DailyNutrients';
import {loadLocalSection,useLocalSection} from './localSection';
import {themes,type Theme} from './themes';

const nutrients=[
 {key:'kcal',label:'Energia',unit:'kcal'},
 {key:'protein_g',label:'Proteínas',unit:'g'},
 {key:'carbs_g',label:'Carboidratos',unit:'g'},
 {key:'fiber_g',label:'Fibras',unit:'g'},
 {key:'fat_g',label:'Gorduras totais',unit:'g'},
 {key:'saturated_g',label:'Gorduras saturadas',unit:'g'},
 {key:'sodium_mg',label:'Sódio',unit:'mg'},
] as const;
type Key=typeof nutrients[number]['key'];
type FoodEntry={id:string;date:string;code:number;name:string;grams:number;values:Partial<Record<Key,number>>};
type Goals=Partial<Record<Key,number>>;
const normalize=(value:string)=>value.toLowerCase().normalize('NFD').replace(/\p{M}/gu,'');
const format=(value:number)=>value.toLocaleString('pt-BR',{maximumFractionDigits:2});
const emptyEntries:FoodEntry[]=[];
const emptyGoals:Goals={};
const dateGoalsKey='diolino-food-date-goals';
const composition=[
 {key:'protein_g',label:'Proteínas',factor:4},
 {key:'carbs_g',label:'Carboidratos',factor:4},
 {key:'fat_g',label:'Gorduras',factor:9},
 {key:'fiber_g',label:'Fibras'},
] as const;

function periodDates(day:string,period:'Semana'|'Mês'){
 const selected=new Date(day+'T12:00:00');
 const start=new Date(selected);
 const end=new Date(selected);
 if(period==='Semana'){
  start.setDate(start.getDate()-((start.getDay()+6)%7));
  end.setTime(start.getTime());
  end.setDate(start.getDate()+6);
 }else{
  start.setDate(1);
  end.setMonth(end.getMonth()+1,0);
 }
 const result:string[]=[];
 for(const date=new Date(start);date<=end;date.setDate(date.getDate()+1)){
  result.push([date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-'));
 }
 return result;
}

function sum(entries:FoodEntry[],key:Key){
 const known=entries.flatMap(entry=>entry.values[key]??[]);
 return {value:known.length?known.reduce((total,value)=>total+value,0):null,missing:entries.length-known.length};
}

export function Nutrition({day,theme}:{day:string;theme:Theme}){
 const [entries,setEntries,entriesError]=useLocalSection('diolino-food-entries',()=>loadLocalSection('diolino-food-entries',emptyEntries));
 const [goals,setGoals,goalsError]=useLocalSection('diolino-food-goals',()=>loadLocalSection('diolino-food-goals',emptyGoals));
 const [dateGoals,setDateGoals,dateGoalsError]=useLocalSection<Record<string,Goals>>(dateGoalsKey,()=>loadLocalSection(dateGoalsKey,{}));
 const [goalScope,setGoalScope]=useState<'default'|'day'>('default');
 const [period,setPeriod]=useState<'Semana'|'Mês'>('Semana');
 const [chartType,setChartType]=useState<'line'|'bar'>('line');
 const [query,setQuery]=useState('');
 const [code,setCode]=useState('');
 const [grams,setGrams]=useState('100');
 const [editing,setEditing]=useState<FoodEntry|null>(null);
 const [metric,setMetric]=useState<Key>('kcal');
 const [status,setStatus]=useState('');
 const today=entries.filter(entry=>entry.date===day);
 const dates=periodDates(day,period);
 const goalDraft=goalScope==='default'?goals:(dateGoals[day]??emptyGoals);
 const series=nutrients.find(nutrient=>nutrient.key===metric)!;
 const food=catalogue.foods.find(item=>String(item.code)===code);
 const indexed=useMemo(()=>catalogue.foods.map(item=>({item,text:normalize(item.name+' '+item.category)})),[]);
 const matches=useMemo(()=>{
  const tokens=normalize(query).trim().split(/\s+/);
  return indexed.filter(({text})=>tokens.every(token=>text.includes(token))).map(({item})=>item);
 },[indexed,query]);
 const options=food&&!matches.includes(food)?[food,...matches]:matches;
 const reset=()=>{setEditing(null);setQuery('');setCode('');setGrams('100')};

 return <>
  {(entriesError||goalsError||dateGoalsError)&&<p className="error" role="alert">{entriesError||goalsError||dateGoalsError}</p>}
  <section className="panel">
   <h2>Diário alimentar</h2>
   <p className="muted">TACO · NEPA/UNICAMP · 4ª edição (2011) · {catalogue.foods.length} alimentos offline</p>
   <form className="module-fields" onSubmit={event=>{
    event.preventDefault();
    const mass=Number(grams);
    if(!food||!Number.isFinite(mass)||mass<=0)return;
    const values:FoodEntry['values']={};
    for(const {key} of nutrients){
     const previous=editing?.code===food.code?editing:undefined;
     const value=previous?(previous.values[key]===undefined?undefined:previous.values[key]*100/previous.grams):food.nutrients[key];
     if(typeof value==='number'&&Number.isFinite(value)&&value>=0)values[key]=value*mass/100;
    }
    const entry:FoodEntry={id:editing?.id??crypto.randomUUID(),date:day,code:food.code,name:food.name,grams:mass,values};
    setEntries(current=>[...current.filter(item=>item.id!==entry.id),entry]);
    setStatus(editing?'Porção atualizada.':'Alimento registrado.');
    reset();
   }}>
    <label>Buscar na TACO<input type="search" value={query} onChange={event=>{setQuery(event.target.value);setCode('')}} placeholder="Ex.: arroz cozido"/></label>
    <label>Alimento<select aria-label="Alimento" required value={code} onChange={event=>setCode(event.target.value)}>
     <option value="">{matches.length?'Selecione um alimento':'Nenhum alimento encontrado'}</option>
     {options.map(item=><option key={item.code} value={item.code}>{item.name}</option>)}
    </select></label>
    <label>Porção (g)<input type="number" required min=".1" max="100000" step=".1" value={grams} onChange={event=>setGrams(event.target.value)}/></label>
    <button type="submit" disabled={!food}><Plus size={16} aria-hidden="true"/> {editing?'Salvar porção':'Adicionar alimento'}</button>
    {editing&&<button type="button" onClick={reset}>Cancelar</button>}
   </form>
   <p role="status" className="muted">{status}</p>
   {today.length?<div className="module-table"><table>
    <thead><tr><th>Alimento</th><th>Porção</th>{nutrients.map(({key,label,unit})=><th key={key}>{label} ({unit})</th>)}<th>Ações</th></tr></thead>
    <tbody>{today.map(entry=><tr key={entry.id}><td>{entry.name}</td><td>{format(entry.grams)} g</td>
     {nutrients.map(({key})=><td key={key}>{entry.values[key]===undefined?'—':format(entry.values[key])}</td>)}
     <td><div className="event-actions">
      <button type="button" aria-label={'Editar '+entry.name} onClick={()=>{setEditing(entry);setQuery('');setCode(String(entry.code));setGrams(String(entry.grams));setStatus('')}}><Pencil size={16} aria-hidden="true"/></button>
      <button type="button" aria-label={'Remover '+entry.name} onClick={()=>{setEntries(current=>current.filter(item=>item.id!==entry.id));if(editing?.id===entry.id)reset();setStatus('Alimento removido.')}}><Trash2 size={16} aria-hidden="true"/></button>
     </div></td>
    </tr>)}</tbody>
   </table></div>:<p className="muted">Nenhum alimento registrado nesta data.</p>}
   <small className="muted">— indica valor sem medida numérica válida na TACO.</small>
  </section>

  <section className="panel">
   <h2>Totais e metas diárias</h2>
   <label>Aplicar metas a <select aria-label="Aplicar metas a" value={goalScope} onChange={event=>setGoalScope(event.target.value as 'default'|'day')}>
    <option value="default">Todos os dias (padrão)</option><option value="day">Apenas à data selecionada</option>
   </select></label>
   <form key={goalScope+JSON.stringify(goalDraft)} className="module-fields" onSubmit={event=>{
    event.preventDefault();
    const values=new FormData(event.currentTarget);
    const next:Goals={};
    for(const {key} of nutrients){
     const value=Number(values.get(key));
     if(value>0&&Number.isFinite(value))next[key]=value;
    }
    if(goalScope==='default')setGoals(next);
    else setDateGoals(current=>{
     const updated={...current};
     if(Object.keys(next).length)updated[day]=next;
     else delete updated[day];
     return updated;
    });
    setStatus('Metas diárias salvas.');
   }}>
    {nutrients.map(({key,label,unit})=>{
     const {value,missing}=sum(today,key);
     const goal=dateGoals[day]?.[key]??goals[key];
     return <div className="nutrition-total" key={key}>
      <strong>{value===null?'—':format(value)+' '+unit}{missing>0&&' · dados incompletos'}</strong>
      {goal!==undefined&&value!==null&&<progress aria-label={'Progresso de '+label} max={goal} value={Math.min(goal,value)}/>}
      <label>Meta de {label.toLowerCase()} ({unit})<input name={key} type="number" min=".01" step=".01" placeholder={goalScope==='day'&&goals[key]!==undefined?String(goals[key]):undefined} defaultValue={goalDraft[key]}/></label>
     </div>;
    })}
    <button type="submit">Salvar metas</button>
   </form>
  </section>
  <DailyNutrients theme={theme} items={composition.map(item=>{
   const total=sum(today,item.key);
   return {...item,grams:total.value,missing:total.missing};
  })}/>
  <section>
   <h2>Evolução do consumo</h2>
   <div className="module-fields">
    <div className="segments" aria-label="Período do consumo">
     {(['Semana','Mês'] as const).map(value=><button key={value} aria-pressed={period===value} onClick={()=>setPeriod(value)}>{value}</button>)}
    </div>
    <div className="segments" aria-label="Gráfico da evolução">
     <button aria-pressed={chartType==='line'} onClick={()=>setChartType('line')}>Linhas</button>
     <button aria-pressed={chartType==='bar'} onClick={()=>setChartType('bar')}>Barras</button>
    </div>
   <label>Indicador do gráfico <select aria-label="Indicador do gráfico" value={metric} onChange={event=>setMetric(event.target.value as Key)}>
    {nutrients.map(({key,label})=><option key={key} value={key}>{label}</option>)}
   </select></label>
   </div>
   <p className="muted">{dates[0].split('-').reverse().join('/')} a {dates[dates.length-1].split('-').reverse().join('/')} · O padrão de meta atual é usado nos dias sem meta específica.</p>
   {dates.every(date=>!entries.some(entry=>entry.date===date))&&<p className="muted">Nenhum consumo registrado neste período.</p>}
   <Plot fixedType title={series.label+' por dia'} unit={series.unit} dates={dates} theme={theme} series={[{
    name:'Consumo',type:chartType,color:themes[theme].exercise,
    points:dates.flatMap((date):Point[]=>{
     const total=sum(entries.filter(entry=>entry.date===date),metric);
     return total.value===null?[]:[[date,total.value]];
    }),
   },{
    name:'Meta diária',type:'line',color:themes[theme].attention,
    points:dates.flatMap((date):Point[]=>{
     const target=dateGoals[date]?.[metric]??goals[metric];
     return target===undefined?[]:[[date,target]];
    }),
   }]}/>
  </section>
  <EnergyCalculator/>
 </>;
}

function EnergyCalculator(){
 const [estimate,setEstimate]=useState<{rest:number;total:number}|null>(null);
 return <section className="panel">
  <h2>Estimativa de gasto energético</h2>
  <form className="module-fields" onInput={()=>setEstimate(null)} onSubmit={event=>{
   event.preventDefault();
   const values=new FormData(event.currentTarget);
   const rest=10*Number(values.get('weight'))+6.25*Number(values.get('height'))-5*Number(values.get('age'))+Number(values.get('coefficient'));
   if(rest>0)setEstimate({rest,total:rest*Number(values.get('factor'))});
  }}>
   <label>Peso (kg)<input required type="number" name="weight" min="30" max="350" step=".1"/></label>
   <label>Altura (cm)<input required type="number" name="height" min="100" max="250" step=".1"/></label>
   <label>Idade (anos)<input required type="number" name="age" min="18" max="120"/></label>
   <label>Coeficiente da equação<select aria-label="Coeficiente da equação" name="coefficient" defaultValue="" required><option value="">Selecione</option><option value="5">Masculino (+5)</option><option value="-161">Feminino (−161)</option></select></label>
   <label>Fator de atividade<input required type="number" name="factor" min="1" max="2.5" step=".01" defaultValue="1.2"/></label>
   <button type="submit">Estimar gasto</button>
  </form>
  <p className="muted">Simulação para adultos. Mifflin–St Jeor estima o gasto em repouso. O gasto diário multiplica esse valor pelo fator de atividade informado.</p>
  <div role="status">{estimate&&<strong>{format(estimate.rest)} kcal/dia em repouso · {format(estimate.total)} kcal/dia com atividade</strong>}</div>
 </section>;
}
