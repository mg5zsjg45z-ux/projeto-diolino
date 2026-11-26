import {useEffect, useRef, type ReactNode} from 'react';

type ModalDialogProps={titleId:string;onClose:()=>void;children:ReactNode};

export function ModalDialog({titleId,onClose,children}:ModalDialogProps){
 const root=useRef<HTMLDivElement>(null);
 const close=useRef(onClose);
 close.current=onClose;

 useEffect(()=>{
  const element=root.current;
  if(!element)return;
  const previous=document.activeElement instanceof HTMLElement?document.activeElement:null;
  const getFocusable=()=>Array.from(element.querySelectorAll<HTMLElement>(
   'a[href],button:not(:disabled),input:not(:disabled):not([type="hidden"]),select:not(:disabled),textarea:not(:disabled),[tabindex]:not([tabindex="-1"])',
  )).filter(item=>item.getClientRects().length>0);
  const focusables=getFocusable();
  (focusables.find(item=>item.hasAttribute('autofocus'))??focusables[0]??element).focus();

  const onKeyDown=(event:KeyboardEvent)=>{
   if(event.key==='Escape'){
    event.preventDefault();
    close.current();
    return;
   }
   if(event.key!=='Tab')return;
   const current=getFocusable();
   if(current.length===0){event.preventDefault();element.focus();return;}
   const first=current[0],last=current[current.length-1];
   if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
   else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  };
  document.addEventListener('keydown',onKeyDown);
  return()=>{
   document.removeEventListener('keydown',onKeyDown);
   if(previous?.isConnected)previous.focus();
  };
 },[]);

 return <div ref={root} className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>{children}</div>;
}
