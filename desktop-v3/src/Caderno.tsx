import {useRef,useState} from 'react';
import {loadLocalSection,useLocalSection} from './localSection';
import './caderno.css';

type Entry = {id: string; text: string};
type Journal = {draft: string; entries: Entry[]};
const key = 'diolino-caderno';
const empty: Journal = {draft: '', entries: []};
const load = () => loadLocalSection(key, empty);

export function Caderno() {
  const [journal, setJournal, error, ready] = useLocalSection(key, load);
  const [history, setHistory] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const editor = useRef<HTMLTextAreaElement>(null);
  const entry = journal.entries.find(row => row.id === selected);

  function conclude() {
    if (!ready || entry || !journal.draft.trim()) return;
    const completed = {id: crypto.randomUUID(), text: journal.draft.trim()};
    setJournal({draft: '', entries: [completed, ...journal.entries]});
    setMessage('Entrada concluída');
    editor.current?.focus();
  }

  return <section className="caderno" aria-label="Caderno de Papel">
    <div className="caderno-bar">
      <button type="button" aria-expanded={history} aria-controls="caderno-history"
        onClick={() => setHistory(!history)}>Caderno</button>
      <div className="caderno-brand">Diolino<small>Caderno de Papel</small></div>
      <button type="button" disabled={!ready || !!entry || !journal.draft.trim()} onClick={conclude}>Concluir</button>
    </div>
    <div className="caderno-linen">
      <div id="caderno-history" className="caderno-history" hidden={!history}>
        <button type="button" onClick={() => {setSelected(null); setHistory(false); editor.current?.focus();}}>Voltar ao rascunho</button>
        {journal.entries.length === 0 && <p>Nenhuma entrada concluída.</p>}
        {journal.entries.map(row => <button type="button" key={row.id} aria-pressed={row.id === selected}
          onClick={() => {setSelected(row.id); setHistory(false); editor.current?.focus();}}>
          {row.text.split('\n')[0].slice(0, 64)}
        </button>)}
      </div>
      <div className="caderno-sheet">
        <textarea ref={editor} aria-label={entry ? 'Entrada concluída' : 'Reflexão pessoal'}
          readOnly={!!entry} disabled={!ready} value={entry?.text ?? journal.draft}
          onChange={event => {setJournal({...journal, draft: event.target.value}); setMessage('');}}/>
        {error && <p role="alert" className="caderno-error">{error}</p>}
        <div className="caderno-status" role="status">
          <span key={entry ? 'reading' : message || 'draft'}>
            {entry ? 'Entrada concluída · leitura' : !ready ? 'Abrindo caderno…' : message || 'Rascunho local'}
          </span>
        </div>
      </div>
    </div>
  </section>;
}
