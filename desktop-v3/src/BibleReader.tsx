import {useEffect,useRef,useState} from 'react';
import {Bookmark} from 'lucide-react';
import {loadLocalSection,useLocalSection} from './localSection';

const editions={
 BPM:{label:'Bíblia Portuguesa Mundial',credit:'eBible.org · Domínio público · Tradução em revisão',load:()=>import('../../data/bibles/BPM.json')},
 BLIVRE:{label:'Bíblia Livre',credit:'© 2018 Diego Santos, Mario Sérgio e Marco Teles · CC BY 4.0 · eBible.org/porbr2018 · texto extraído do USFX',load:()=>import('../../data/bibles/desktop-v3/BLIVRE.json')},
 BLT:{label:'Bíblia Livre Para Todos (Novo Testamento)',credit:'© 2022 Free Bible Ministry, Inc. · CC BY-SA 4.0 · eBible.org/porblt · texto extraído do USFX',load:()=>import('../../data/bibles/desktop-v3/BLT.json')},
};
type Edition=keyof typeof editions;
type Note={edition:Edition;book:string;bookName:string;chapter:string;verse:string;marked:boolean;comment:string};
const notesKey='diolino-bible-notes';
const idOf=(note:Pick<Note,'edition'|'book'|'chapter'|'verse'>)=>[note.edition,note.book,note.chapter,note.verse].join(':');

type Chapters=Record<string,Record<string,string>>;
type Translation={
 name:string;
 books:Record<string,{name:string;chapters:Chapters}>;
};
type Reference={book:string;chapter:string;verse:string;text:string};

const normalize=(text:string)=>text.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/\p{M}/gu,'');

export function BibleReader(){
 const [edition,setEdition]=useState<Edition>('BPM');
 const [loaded,setLoaded]=useState<{edition:Edition;text:Translation}>();
 const [notes,setNotes,notesError]=useLocalSection<Note[]>(notesKey,()=>loadLocalSection(notesKey,[]));
 const [saved,setSaved]=useState(false);
 const [pending,setPending]=useState<Note|null>(null);
 const [failed,setFailed]=useState(false);
 const [book,setBook]=useState('');
 const [chapter,setChapter]=useState('1');
 const [selectedVerse,setSelectedVerse]=useState('');
 const commentInput=useRef<HTMLTextAreaElement>(null);
 useEffect(()=>{if(selectedVerse)commentInput.current?.focus()},[selectedVerse,book,chapter,edition]);
 const [query,setQuery]=useState('');
 const [results,setResults]=useState<Reference[]|null>(null);

 useEffect(()=>{
  let mounted=true;
  editions[edition].load().then(({default:text})=>{
   if(!mounted)return;
   const translation:Translation=text;
   const firstBook=Object.keys(translation.books)[0];
   const nextBook=book in translation.books?book:firstBook;
   const chapters=translation.books[nextBook].chapters;
   setBook(nextBook);
   setChapter(chapter in chapters?chapter:Object.keys(chapters)[0]);
   setLoaded({edition,text});
  }).catch(()=>{if(mounted)setFailed(true)});
  return()=>{mounted=false};
 },[edition]);

 const changeEdition=(next:Edition)=>{
  setFailed(false);setSelectedVerse('');setResults(null);setEdition(next);
 };
 const goToNote=(note:Note)=>{
  setSaved(false);setResults(null);
  if(note.edition===edition){setBook(note.book);setChapter(note.chapter);setSelectedVerse(note.verse)}
  else{changeEdition(note.edition);setPending(note)}
 };
 useEffect(()=>{
  if(pending&&loaded?.edition===pending.edition){
   setBook(pending.book);setChapter(pending.chapter);setSelectedVerse(pending.verse);setPending(null);
  }
 },[loaded,pending]);

 const translation=loaded?.edition===edition?loaded.text:undefined;
 const current=translation?.books[book];
 const chapters=Object.keys(current?.chapters??{});
 const chapterIndex=chapters.indexOf(chapter);
 const reference:Note={edition,book,bookName:current?.name??book,chapter,verse:selectedVerse,marked:false,comment:''};
 const existing=notes.find(note=>idOf(note)===idOf(reference));
 const updateNote=(note:Note)=>setNotes(items=>{
  const remaining=items.filter(item=>idOf(item)!==idOf(note));
  return note.marked||note.comment?[...remaining,note]:remaining;
 });
 const books=translation?.books??{};
 const selectChapter=(value:string)=>{setChapter(value);setSelectedVerse('')};
 const search=()=>{
  const term=normalize(query.trim());
  if(!term){setResults(null);return}
  const matches:Reference[]=[];
  for(const [code,entry] of Object.entries(books)){
   for(const [number,verses] of Object.entries(entry.chapters)){
    for(const [verse,text] of Object.entries(verses)){
     if(normalize(text).includes(term))matches.push({book:code,chapter:number,verse,text});
     if(matches.length===200){setResults(matches);return}
    }
   }
  }
  setResults(matches);
 };

 return <section className="panel bible-reader" aria-labelledby="bible-reader-title">
  <div className="agenda-heading"><h2 id="bible-reader-title">Bíblia offline</h2></div>
  <div className="bible-controls">
   <label>Tradução<select aria-label="Tradução" value={edition} onChange={event=>{setPending(null);changeEdition(event.target.value as Edition)}}>
    {Object.entries(editions).map(([key,item])=><option key={key} value={key}>{item.label}</option>)}
   </select></label>
   <button type="button" aria-expanded={saved} onClick={()=>setSaved(value=>!value)}><Bookmark size={16} aria-hidden="true"/> Marcações e comentários ({notes.length})</button>
  </div>
  <p className="muted">{editions[edition].credit}</p>
  {notesError&&<p className="error" role="alert">{notesError}</p>}
  {saved?<section aria-label="Referências salvas">
   {notes.length===0?<p className="muted">Selecione um versículo para marcar ou comentar.</p>:<ul className="bible-results">{notes.map(note=><li key={idOf(note)}>
    <button type="button" onClick={()=>goToNote(note)}>{note.bookName} {note.chapter}:{note.verse} · {note.edition}</button>
    <span>{note.marked&&'Marcado'}{note.marked&&note.comment&&' · '}{note.comment}</span>
   </li>)}</ul>}
  </section>:failed?<p className="error" role="alert">Não foi possível abrir esta edição offline.</p>:!current?<p role="status">Carregando Bíblia offline…</p>:<>
  <form className="bible-controls" onSubmit={event=>{event.preventDefault();search()}}>
   <label>Buscar versículos<input type="search" value={query} onChange={event=>{setQuery(event.target.value);if(!event.target.value)setResults(null)}}/></label>
   <button type="submit">Buscar</button>
   {results&&<button type="button" onClick={()=>setResults(null)}>Voltar à leitura</button>}
  </form>
  {results?<section aria-label="Resultados da busca">
   <p role="status">{results.length===0?'Nenhum versículo encontrado.':results.length===200?'Mostrando os primeiros 200 resultados.':results.length+' resultado(s).'}</p>
   <ul className="study-list bible-results">{results.map(result=><li key={result.book+':'+result.chapter+':'+result.verse}>
    <button type="button" onClick={()=>{
     setBook(result.book);setChapter(result.chapter);setSelectedVerse(result.verse);setResults(null);
    }}>{books[result.book].name} {result.chapter}:{result.verse}</button>
    <span>{result.text}</span>
   </li>)}</ul>
  </section>:<>
   <div className="bible-controls">
    <label>Livro<select aria-label="Livro" value={book} onChange={event=>{
     setBook(event.target.value);selectChapter(Object.keys(books[event.target.value].chapters)[0]);
    }}>{Object.entries(books).map(([code,entry])=><option key={code} value={code}>{entry.name}</option>)}</select></label>
    <label>Capítulo<select aria-label="Capítulo" value={chapter} onChange={event=>selectChapter(event.target.value)}>
     {chapters.map(value=><option key={value}>{value}</option>)}
    </select></label>
    <button type="button" disabled={chapterIndex<=0} onClick={()=>selectChapter(chapters[chapterIndex-1])}>Capítulo anterior</button>
    <button type="button" disabled={chapterIndex>=chapters.length-1} onClick={()=>selectChapter(chapters[chapterIndex+1])}>Próximo capítulo</button>
   </div>
   <h3>{current.name} {chapter}</h3>
   {!selectedVerse&&<p className="muted">Selecione um versículo para comentar ou marcar.</p>}
   {selectedVerse&&<form key={idOf(reference)+(existing?.comment??'')} className="bible-comment" onSubmit={event=>{
    event.preventDefault();
    const comment=String(new FormData(event.currentTarget).get('comment')??'').trim();
    updateNote({...reference,marked:existing?.marked??false,comment});
   }}>
    <label>Comentário · {current.name} {chapter}:{selectedVerse}
     <textarea ref={commentInput} name="comment" maxLength={3000} rows={3} defaultValue={existing?.comment}/>
    </label>
    <div className="event-actions">
     <button type="submit">Salvar comentário</button>
     <button type="button" aria-pressed={existing?.marked??false} onClick={()=>updateNote({...reference,comment:existing?.comment??'',marked:!existing?.marked})}>{existing?.marked?'Remover marcação':'Marcar versículo'}</button>
    </div>
   </form>}
   <ol className="bible-verses" aria-label={'Versículos de '+current.name+' '+chapter}>
    {Object.entries(current.chapters[chapter]??{}).map(([verse,text])=><li key={verse} value={Number(verse)}>
     <button className="bible-verse" type="button" aria-pressed={verse===selectedVerse} onClick={()=>setSelectedVerse(verse)}>
      {notes.some(note=>note.marked&&idOf(note)===idOf({...reference,verse}))?<mark>{text}</mark>:text}
     </button>
    </li>)}
   </ol>
  </>}
  </>}
 </section>;
}
