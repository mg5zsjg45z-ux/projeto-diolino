import definitions from './definitions.json' with {type:'json'};
import taco from './taco.json' with {type:'json'};
export {definitions};
export const fresh = () => ({format:'diolino-online-1', nextId:1, records:{}, audit:[]});
export const active = (state,kind,day) => (state.records[kind]||[]).filter(r=>!r.deleted_at&&(!day||r.date===day));
export function iso(value) {
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value)||!Number.isFinite(Date.parse(value))||new Date(value).toISOString().slice(0,10)!==value) throw Error('Data inválida.');
  return value;
}
const numeric=v=>Number(String(v).trim().replace(',','.'));
export function energy(data){
  let [w,h,a,f,d]=['weight','height','age','activity','deficit_pct'].map(k=>numeric(data[k]));
  if(![w,h,a,f,d].every(Number.isFinite)||w<30||w>350||h<100||h>250||!Number.isInteger(a)||a<18||a>120||f<1||f>2.5||d<0||d>50)throw Error('Confira os parâmetros e limites da simulação.');
  if(!['Masculino (+5)','Feminino (−161)'].includes(data.coefficient))throw Error('Coeficiente inválido.');
  let resting=10*w+6.25*h-5*a+(data.coefficient.startsWith('Masculino')?5:-161),total=resting*f,intake=total*(1-d/100);
  if(resting<=0||intake<1000)throw Error('A simulação resultaria em menos de 1.000 kcal/dia ou repouso inválido. Revise os parâmetros com um profissional.');
  return {resting_kcal:resting,total_kcal:total,deficit_kcal:total-intake,intake_kcal:intake,deficit_pct:d};
}
export function validate(kind, input){
  const spec=definitions.schema[kind];if(!spec||!input||typeof input!=='object'||Array.isArray(input))throw Error('Registro inválido.');
  const result={};
  for(const field of spec.fields){
    let v=input[field.key];
    if(v===undefined||v===null||v===''){if(field.required)throw Error('Preencha: '+field.label);result[field.key]=null;continue;}
    if(['number','integer','workout','plan'].includes(field.type)){
      v=numeric(v);if(!Number.isFinite(v)||(field.type!=='number'&&!Number.isInteger(v))||(field.minimum!==null&&v<field.minimum)||(field.maximum!==null&&v>field.maximum))throw Error('Valor inválido: '+field.label);
    }else{if(typeof v!=='string'||v.length>20000)throw Error('Texto inválido: '+field.label);v=v.trim();if(field.required&&!v)throw Error('Preencha: '+field.label);
      if(field.type==='date')iso(v);
      if(field.type==='time'&&!/^([01]\d|2[0-3]):[0-5]\d$/.test(v))throw Error('Horário inválido.');
      if(field.type==='datetime'){if(!/^\d{4}-\d{2}-\d{2} ([01]\d|2[0-3]):[0-5]\d$/.test(v))throw Error('Data e hora inválidas.');iso(v.slice(0,10));}
      if(field.type==='choice'&&!field.choices.includes(v))throw Error('Opção inválida: '+field.label);
    }result[field.key]=v;
  }
  if(kind==='sleep'){let elapsed=(Date.parse(result.end.replace(' ','T')+'Z')-Date.parse(result.start.replace(' ','T')+'Z'))/60000;if(elapsed<=0||elapsed>2880||result.awake_min>=elapsed||result.date!==result.end.slice(0,10))throw Error('Confira início, fim, tempo acordado e data em que acordou.');}
  if(kind==='medication'&&((result.status==='Tomado'&&(!result.taken_dose||!result.time))||(result.status!=='Tomado'&&result.taken_dose)))throw Error('Dose e horário devem corresponder à situação registrada.');
  if(kind==='body'&&!['weight_kg','waist_cm','hip_cm','chest_cm','arm_cm','thigh_cm','fat_pct'].some(k=>result[k]!==null))throw Error('Informe pelo menos uma medida corporal.');
  if(kind==='plans'&&result.start_date&&result.end_date&&result.end_date<result.start_date)throw Error('O prazo deve ser posterior ao início.');
  if(kind==='daily_tasks'&&result.micro_steps){let steps;try{steps=JSON.parse(result.micro_steps)}catch{throw Error('Micro-passos inválidos.');}if(!Array.isArray(steps)||steps.length>50||steps.some(s=>!s||typeof s.title!=='string'||s.title.trim().length>300||typeof s.done!=='boolean'))throw Error('Use até 50 micro-passos válidos.');result.micro_steps=JSON.stringify(steps.map(s=>({title:s.title.trim(),done:s.done})));}
  if(kind==='habit_marks'&&result.habit_id&&!Number.isInteger(result.habit_id))throw Error('Hábito inválido.');
  if(kind==='energy')energy({weight:result.weight_kg,height:result.height_cm,age:result.age_years,coefficient:result.coefficient,activity:result.activity_factor,deficit_pct:result.deficit_pct});
  return result;
}
export function save(state,kind,values,id=null,tacoCode=null){
  let row=validate(kind,values),existing=id==null?null:active(state,kind).find(r=>r.id===id);
  if(id!=null&&!existing)throw Error('Registro não encontrado.');
  if(kind==='habit_marks'){
    if(!active(state,'habits').some(h=>h.id===row.habit_id))throw Error('Hábito não encontrado.');
    const duplicate=active(state,'habit_marks').find(r=>r.id!==id&&r.habit_id===row.habit_id&&r.date===row.date);
    if(duplicate)throw Error('Este hábito já tem uma marcação nesta data. Edite a marcação existente.');
  }
  for(const f of definitions.schema[kind].fields)if(['workout','plan'].includes(f.type)&&row[f.key]!=null&&!active(state,f.type==='plan'?'plans':'workout').some(r=>r.id===row[f.key]))throw Error('Registro associado não encontrado.');
  if(['daily','routine','profile'].includes(kind)&&active(state,kind).some(r=>r.id!==id&&(kind==='profile'||r.date===row.date)))throw Error('Já existe um registro para este dia ou perfil. Edite o existente.');
  if(kind==='food'&&tacoCode){const food=taco.foods.find(f=>String(f.code)===String(tacoCode));if(!food)throw Error('Alimento TACO inválido.');if(row.unit!=='g'||!(row.quantity>0))throw Error('Informe a quantidade em gramas.');for(const k of ['kcal','protein_g','carbs_g','fat_g','fiber_g','sodium_mg'])if(k in row)row[k]=food.nutrients[k]==null?null:food.nutrients[k]*row.quantity/100;row.source='TACO (NEPA/UNICAMP)';row._nutrition={code:food.code,name:food.name,metadata:taco.metadata,nutrients:food.nutrients};}
  else if(kind==='food'&&existing?._nutrition&&row.source==='TACO (NEPA/UNICAMP)'){const code=existing._nutrition.code??existing._nutrition.food?.code;if(!code)throw Error('Selecione novamente o alimento na TACO.');return save(state,kind,row,id,code);}
  const now=new Date().toISOString();row={...row,id:id??state.nextId++,created_at:existing?.created_at||now,updated_at:now,deleted_at:null};
  const list=state.records[kind] ||= [];if(existing)list[list.indexOf(existing)]=row;else list.push(row);
  state.audit.push({kind,id:row.id,action:existing?'editar':'criar',at:now,before:existing||null});return row.id;
}
export function plans(state,day){return active(state,'plans').map(p=>{let steps=active(state,'plan_steps').filter(s=>s.plan_id===p.id).sort((a,b)=>(a.position||0)-(b.position||0)||a.id-b.id),done=steps.filter(s=>s.state==='Concluído').length;return {...p,steps,total:steps.length,done,progress:steps.length?Math.round(100*done/steps.length):0,overdue:steps.filter(s=>s.state!=='Concluído'&&s.due_date&&s.due_date<day).length};});}
export function createPlan(state,values,steps){if(!Array.isArray(steps)||steps.length>100)throw Error('Use até 100 etapas.');let id=save(state,'plans',values);for(let [i,s]of steps.entries())save(state,'plan_steps',{...(typeof s==='string'?{title:s}:s),plan_id:id,state:'A fazer',priority:s.priority||'Normal',position:i});return id;}
export function overview(state,day){
  iso(day);let rows=k=>active(state,k,day),sum=(rs,key)=>rs.reduce((n,r)=>n+(r[key]||0),0),studies=rows('study'),workouts=rows('workout'),foods=rows('food'),sleep=rows('sleep');
  let daily=rows('daily')[0]||null,water=rows('hydration').filter(r=>r.is_water==='Sim'||(!r.is_water&&['agua','agua mineral','agua filtrada','agua sem gas','agua com gas'].includes(r.drink.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase().trim()))).reduce((n,r)=>n+r.volume_ml,0);
  let summary={study_min:sum(studies,'duration_min'),study_count:studies.length,exercise_min:sum(workouts,'duration_min'),exercise_count:workouts.length,bible_count:rows('bible').length,kcal:sum(foods,'kcal'),food_count:foods.length,unknown_kcal:foods.filter(r=>r.kcal==null).length,estimated_foods:foods.filter(r=>r.source==='Estimativa').length,protein_g:sum(foods,'protein_g'),sleep_min:sleep.reduce((n,r)=>n+(Date.parse(r.end.replace(' ','T')+'Z')-Date.parse(r.start.replace(' ','T')+'Z'))/60000-r.awake_min,0),sleep_count:sleep.length,water_ml:water,daily};
  let pillars={};for(let [key,amount,count,goal]of [['medicine_status',summary.study_min,studies.length,60],['exercise_status',summary.exercise_min,workouts.length,40],['bible_status',summary.bible_count,summary.bible_count,1]]){let explicit=daily?.[key];pillars[key]=explicit&&explicit!=='Não informado'?{done:explicit==='Realizado',source:'Seu relato: '+explicit,known:true}:{done:amount>=goal,source:count?'Pelos registros':'–',known:!!count};}
  let weights=active(state,'body').filter(r=>r.weight_kg!=null&&r.date<=day).sort((a,b)=>(a.date+(a.time||'')).localeCompare(b.date+(b.time||''))||a.id-b.id),weight=weights.at(-1)||null,record=rows('routine')[0]||null,target=weight?weight.weight_kg*50:null;
  let series=new Map(weights.map(r=>[r.date,r.weight_kg]));let end=new Date(day+'T12:00:00Z');end.setUTCDate(end.getUTCDate()+6);
  return {summary,pillars,checks:{record,weight,water_ml:water,water_target_ml:target,water_complete:target!=null&&water>=target,counts:Object.fromEntries(definitions.groups.map(([l,ks])=>[l,ks.filter(k=>record?.[k]===1).length]))},check_groups:definitions.groups,upcoming:active(state,'agenda').filter(r=>r.state==='Pendente'&&r.date>=day).sort((a,b)=>(a.date+(a.time||'23:59')).localeCompare(b.date+(b.time||'23:59'))).slice(0,30),weight_series:[...series].slice(-90),planned_steps:plans(state,day).filter(p=>p.status==='Ativo').flatMap(p=>p.steps.filter(s=>s.state!=='Concluído'&&s.due_date&&s.due_date<=end.toISOString().slice(0,10)).map(s=>({...s,plan_title:p.title}))).sort((a,b)=>a.due_date.localeCompare(b.due_date)).slice(0,20)};
}
export function modulePreferences(input={}){
 if(!input||typeof input!=='object'||Array.isArray(input))throw Error('Preferências inválidas.');
 const result={};for(const key of ['planning','agenda','bible','notebook']){if(input[key]!==undefined&&typeof input[key]!=='boolean')throw Error('Preferência de módulo inválida.');result[key]=input[key]!==false;}return result;
}
export function mutate(state,path,data){
  if(path==='preferences'){state.preferences={modules:modulePreferences(data.modules)};return state.preferences;}
  if(path==='notebook/save'){
    const existing=data.id?active(state,'notebook').find(r=>r.id===data.id):null;
    if(data.id&&(!existing||existing.updated_at!==data.expected_updated_at))throw Error('Esta anotação foi alterada em outro dispositivo. Mantenha seu texto e recarregue a lista.');
    const id=save(state,'notebook',data.values,data.id||null);const entry=state.audit.at(-1);if(entry.before)entry.before={id:entry.before.id,title:entry.before.title,date:entry.before.date,content_length:(entry.before.content||'').length};return {id,updated_at:active(state,'notebook').find(r=>r.id===id).updated_at};
  }
  if(path==='save')return {id:save(state,data.kind,data.values,data.id??null,data.taco_code)};
  if(path==='delete'){let row=active(state,data.kind).find(r=>r.id===data.id);if(!row)throw Error('Registro não encontrado.');if(data.kind==='plans'&&active(state,'plan_steps').some(r=>r.plan_id===row.id))throw Error('Arquive o plano para preservar suas etapas.');if(data.kind==='workout'&&active(state,'sets').some(r=>r.workout_id===row.id))throw Error('Remova as séries antes de excluir o treino.');state.audit.push({kind:data.kind,id:row.id,action:'excluir',at:new Date().toISOString(),before:{...row}});row.deleted_at=new Date().toISOString();return {ok:true};}
  if(path==='check'){iso(data.day);if(typeof data.checked!=='boolean')throw Error('Checagem inválida.');let pillar=['medicine_status','exercise_status','bible_status'].includes(data.key);if(!pillar&&!definitions.groups.flatMap(g=>g[1]).includes(data.key))throw Error('Checagem inválida.');let kind=pillar?'daily':'routine',row=active(state,kind,data.day)[0];return {id:save(state,kind,{...(pillar?{shift:'Não informado',medicine_status:'Não informado',exercise_status:'Não informado',bible_status:'Não informado'}:{}),...row,date:data.day,[data.key]:pillar?(data.checked?'Realizado':'Não realizado'):+data.checked},row?.id)};}
  if(path==='plans/create')return {id:createPlan(state,data.values,data.steps)};
  if(path==='plans/check'){if(typeof data.checked!=='boolean')throw Error('Checagem inválida.');let row=active(state,'plan_steps').find(r=>r.id===data.id);if(!row)throw Error('Etapa não encontrada.');return {id:save(state,'plan_steps',{...row,state:data.checked?'Concluído':'A fazer'},row.id)};}
  if(path==='plans/duplicate'){let p=plans(state,'9999-12-31').find(r=>r.id===data.id);if(!p)throw Error('Plano não encontrado.');return {id:createPlan(state,{...p,title:p.title+' · cópia',status:'Ativo',start_date:null,end_date:null},p.steps.map(s=>({...s,due_date:null})))};}
  throw Error('Ação não disponível.');
}
export function tacoSearch(query){let clean=s=>s.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase(),words=clean(query).split(/\s+/).filter(Boolean);return taco.foods.filter(f=>words.every(w=>clean(f.name).includes(w))).slice(0,50);}
