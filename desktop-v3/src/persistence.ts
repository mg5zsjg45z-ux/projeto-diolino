import {invoke,isTauri} from '@tauri-apps/api/core';
const keys=['diolino-library','diolino-health-entries','diolino-health-goals','diolino-bible-days','diolino-preview-reviews','diolino-habits-v1','diolino-habit-marks-v1','diolino-focus-settings','diolino-focus-timer','diolino-focus-sessions','diolino-preview-agenda','diolino-preview-tasks','diolino-preview-studies'];
let queue=Promise.resolve();
let ready=false;
let failed=false;
export async function hydrate(){
 if(!isTauri())return;
 for(const key of keys){
  const local=localStorage.getItem(key);
  if(local!==null)await invoke('preview_storage',{request:{action:'import',key,value:JSON.parse(local)}});
  const value=await invoke('preview_storage',{request:{action:'get',key}});
  if(value!==null)localStorage.setItem(key,JSON.stringify(value));
 }
 ready=true;
}
export function persist(key:string,value:unknown){
 localStorage.setItem(key,JSON.stringify(value));
 if(isTauri()&&ready)queue=queue.then(async()=>{await invoke('preview_storage',{request:{action:'put',key,value}})}).catch(error=>{failed=true;console.error(error);window.dispatchEvent(new CustomEvent('diolino-storage-error',{detail:String(error)}))});
}
export async function backup(){await queue;if(!ready||failed)throw new Error('SQLite indisponível ou gravação pendente de recuperação.');return invoke<string>('preview_storage',{request:{action:'backup'}})}
