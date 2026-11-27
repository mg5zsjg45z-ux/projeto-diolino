import {useEffect,useRef,useState} from 'react';
import * as echarts from './charts';
import {themes,type Theme} from './themes';

type Item={label:string;grams:number|null;missing:number;factor?:number};

export function DailyNutrients({items,theme}:{items:Item[];theme:Theme}){
 const [type,setType]=useState<'bar'|'pie'>('bar');
 const ref=useRef<HTMLDivElement>(null);
 const {fg,grid,study,exercise,sleep,attention}=themes[theme];
 const quantified=items.filter(item=>item.grams!==null);
 const pie=quantified.filter(item=>item.factor!==undefined&&item.grams!>0);
 const hasData=type==='bar'?quantified.length>0:pie.length>0;
 useEffect(()=>{
  if(!ref.current)return;
  const element=ref.current;
  const chart=echarts.init(element);
  chart.setOption({
   animation:false,textStyle:{color:fg},color:[study,exercise,sleep,attention],
   tooltip:{trigger:type==='pie'?'item':'axis',renderMode:'richText',valueFormatter:(value:unknown)=>value==null?'—':Number(value).toLocaleString('pt-BR',{maximumFractionDigits:2})+(type==='pie'?' kcal':' g')},
   ...(type==='pie'?{series:[{type:'pie',radius:['35%','66%'],label:{color:fg,formatter:'{b} · {d}%'},data:pie.map(item=>({name:item.label,value:item.grams!*item.factor!}))}]}:{
    grid:{left:105,right:18,top:12,bottom:32},
    xAxis:{type:'value',name:'g',nameLocation:'middle',nameGap:18,axisLabel:{color:fg},splitLine:{lineStyle:{color:grid}}},
    yAxis:{type:'category',inverse:true,data:items.map(item=>item.label),axisLabel:{color:fg}},
    series:[{type:'bar',data:items.map((item,index)=>({value:item.grams,itemStyle:{color:[study,exercise,sleep,attention][index%4]}}))}],
   }),
  });
  const observer=new ResizeObserver(()=>chart.resize());
  observer.observe(element);
  return()=>{observer.disconnect();chart.dispose()};
 },[type,items,fg,grid,study,exercise,sleep,attention,hasData]);

 return <section className="panel">
  <div className="agenda-heading"><h2>Composição do dia</h2>
   <div className="segments" aria-label="Gráfico da composição">
    <button aria-pressed={type==='bar'} onClick={()=>setType('bar')}>Barras</button>
    <button aria-pressed={type==='pie'} onClick={()=>setType('pie')}>Pizza</button>
   </div>
  </div>
  {hasData?<div className="plot" ref={ref} role="img" aria-label={type==='bar'?'Nutrientes do dia em gramas':'Participação estimada dos macronutrientes na energia'}/>:<p className="muted">Sem valores para exibir neste gráfico.</p>}
  {type==='pie'&&<p className="muted">Distribuição estimada entre proteínas, carboidratos e gorduras, usando 4, 4 e 9 kcal/g. A energia do diário vem da TACO.</p>}
  <details><summary>Composição em tabela</summary><table><thead><tr><th>Nutriente</th><th>Quantidade</th></tr></thead>
   <tbody>{items.map(({label,grams,missing})=><tr key={label}><td>{label}</td><td>{grams===null?'—':grams.toLocaleString('pt-BR',{maximumFractionDigits:2})+' g'}{missing>0&&' · dados incompletos'}</td></tr>)}</tbody>
  </table></details>
 </section>;
}
