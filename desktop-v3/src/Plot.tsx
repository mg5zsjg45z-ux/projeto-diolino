import {useEffect,useRef,useState} from 'react';
import * as echarts from 'echarts';
import type {Point} from './data';
import {themes,type Theme} from './themes';
export function Plot({title,unit,series,dates,theme,max,fixedType=false}:{title:string;unit:string;series:{name:string;points:Point[];color:string;type:'bar'|'line'}[];dates:string[];theme:Theme;max?:number;fixedType?:boolean}){
 const [chartType,setChartType]=useState<''|'bar'|'line'>('');
 const ref=useRef<HTMLDivElement>(null);
 const empty=series.every(s=>s.points.length===0);
 useEffect(()=>{
   const el=ref.current;if(!el)return;
   const chart=echarts.init(el,undefined,{renderer:'canvas'});
   const {fg,grid}=themes[theme];
   chart.setOption({animation:false,aria:{enabled:!empty},backgroundColor:'transparent',textStyle:{color:fg},tooltip:{trigger:'axis',renderMode:'richText',valueFormatter:(v:unknown)=>v==null?'Sem registro':Number(v).toLocaleString('pt-BR',{maximumFractionDigits:1})+' '+unit},legend:{show:series.length>1,textStyle:{color:fg}},grid:{left:48,right:18,top:series.length>1?35:15,bottom:45},xAxis:{type:'category',data:dates.map(d=>d.slice(8)+'/'+d.slice(5,7)),axisLabel:{color:fg},axisLine:{lineStyle:{color:grid}}},yAxis:{type:'value',max,axisLabel:{color:fg},splitLine:{lineStyle:{color:grid}}},dataZoom:dates.length>14?[{type:'inside',start:0,end:100},{type:'slider',height:14,bottom:7}]:[],series:series.map(s=>({name:s.name,type:chartType||s.type,connectNulls:false,symbolSize:6,itemStyle:{color:s.color,borderRadius:(chartType||s.type)==='bar'?[4,4,0,0]:0},data:dates.map(d=>new Map(s.points).get(d)??null)}))});
   const observer=new ResizeObserver(()=>chart.resize());observer.observe(el);
   return ()=>{observer.disconnect();chart.dispose()};
 },[series,dates,theme,unit,max,chartType]);
 return <section className="panel"><div className="agenda-heading"><h3>{title}</h3>{!fixedType&&<label>Tipo de gráfico <select aria-label={'Tipo de gráfico: '+title} value={chartType||series[0]?.type||'bar'} onChange={event=>setChartType(event.target.value as 'line'|'bar')}><option value="line">Linhas</option><option value="bar">Barras</option></select></label>}</div><div className="plot" ref={ref} role={empty?undefined:'img'} aria-label={empty?undefined:title+' em '+unit} aria-hidden={empty||undefined}/>{empty&&<p className="muted" role="status">Sem registros neste período.</p>}<details><summary>Dados em tabela</summary><table><thead><tr><th>Data</th>{series.map(s=><th key={s.name}>{s.name} ({unit})</th>)}</tr></thead><tbody>{dates.map(d=><tr key={d}><td>{d}</td>{series.map(s=><td key={s.name}>{new Map(s.points).get(d)?.toLocaleString('pt-BR',{maximumFractionDigits:1})??'—'}</td>)}</tr>)}</tbody></table></details></section>
}
