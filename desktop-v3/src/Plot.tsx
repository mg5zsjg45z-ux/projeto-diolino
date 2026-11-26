import {useEffect,useRef} from 'react';
import * as echarts from 'echarts';
import type {Point} from './data';
import {themes,type Theme} from './themes';
export function Plot({title,unit,series,dates,theme,max}:{title:string;unit:string;series:{name:string;points:Point[];color:string;type:'bar'|'line'}[];dates:string[];theme:Theme;max?:number}){
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{
   const el=ref.current;if(!el)return;
   const chart=echarts.init(el,undefined,{renderer:'canvas'});
   const {fg,grid}=themes[theme];
   chart.setOption({animation:false,aria:{enabled:true},backgroundColor:'transparent',textStyle:{color:fg},tooltip:{trigger:'axis',renderMode:'richText',valueFormatter:(v:unknown)=>v==null?'Sem registro':Number(v).toLocaleString('pt-BR',{maximumFractionDigits:1})+' '+unit},legend:{show:series.length>1,textStyle:{color:fg}},grid:{left:48,right:18,top:series.length>1?35:15,bottom:45},xAxis:{type:'category',data:dates.map(d=>d.slice(8)+'/'+d.slice(5,7)),axisLabel:{color:fg},axisLine:{lineStyle:{color:grid}}},yAxis:{type:'value',max,axisLabel:{color:fg},splitLine:{lineStyle:{color:grid}}},dataZoom:dates.length>14?[{type:'inside',start:0,end:100},{type:'slider',height:14,bottom:7}]:[],series:series.map(s=>({name:s.name,type:s.type,connectNulls:false,symbolSize:6,itemStyle:{color:s.color,borderRadius:s.type==='bar'?[4,4,0,0]:0},data:dates.map(d=>new Map(s.points).get(d)??null)}))});
   const observer=new ResizeObserver(()=>chart.resize());observer.observe(el);
   return ()=>{observer.disconnect();chart.dispose()};
 },[series,dates,theme,unit,max]);
 const empty=series.every(s=>s.points.length===0);
 return <section className="panel"><h3>{title}</h3><div className="plot" ref={ref} role="img" aria-label={title+' em '+unit}/>{empty&&<p className="muted">Sem registros neste período.</p>}<details><summary>Dados em tabela</summary><table><thead><tr><th>Data</th>{series.map(s=><th key={s.name}>{s.name} ({unit})</th>)}</tr></thead><tbody>{dates.map(d=><tr key={d}><td>{d}</td>{series.map(s=><td key={s.name}>{new Map(s.points).get(d)?.toLocaleString('pt-BR',{maximumFractionDigits:1})??'—'}</td>)}</tr>)}</tbody></table></details></section>
}
