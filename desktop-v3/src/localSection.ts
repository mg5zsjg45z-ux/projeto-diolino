import {invoke,isTauri} from '@tauri-apps/api/core';
import {useEffect,useRef,useState} from 'react';

const writes=new Map<string,Promise<void>>();

export function useLocalSection<T>(key:string,load:()=>T) {
 const [value,setValue]=useState(load);
 const [ready,setReady]=useState(false);
 const [error,setError]=useState('');
 const initial=useRef(value);
 useEffect(()=>{
  if(!isTauri()){setReady(true);return}
  let live=true;
  (writes.get(key)??Promise.resolve())
   .catch(()=>{})
   .then(()=>invoke<T|null>('read_local_section',{key}))
   .then(stored=>{
    if(!live)return;
    let pending=false;
    try{pending=localStorage.getItem(key+'.sqlite-pending')!==null}catch{/* SQLite still available */}
    if(stored!==null&&!pending)setValue(current=>current===initial.current?stored:current);
    setReady(true);
   })
   .catch(()=>{if(live)setError('O banco 3.0 não pôde ser aberto. Os registros continuam no armazenamento da interface.')});
  return()=>{live=false};
 },[key]);
 useEffect(()=>{
  // Keep the existing fallback while SQLite is unavailable or migrating.
  const serialized=JSON.stringify(value);
  const native=isTauri();
  try{
   localStorage.setItem(key,serialized);
   if(native&&(ready||value!==initial.current))localStorage.setItem(key+'.sqlite-pending',serialized);
  }
  catch{if(!isTauri())setError('Não foi possível salvar os registros neste navegador.')}
  if(!ready||!native)return;
  const write=(writes.get(key)??Promise.resolve()).catch(()=>{})
   .then(()=>invoke<void>('write_local_section',{key,value}));
  writes.set(key,write);
  write.then(()=>{
   try{if(localStorage.getItem(key+'.sqlite-pending')===serialized)localStorage.removeItem(key+'.sqlite-pending')}catch{/* SQLite write already completed */}
   setError('');
  }).catch(()=>setError('Não foi possível gravar no banco 3.0. Confira o armazenamento local.'))
   .finally(()=>{if(writes.get(key)===write)writes.delete(key)});
 },[key,ready,value]);
 return [value,setValue,error] as const;
}
