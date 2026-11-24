"""Ephemeral full-text index and typo-tolerant local search."""
import re
import sqlite3
import unicodedata
from rapidfuzz import fuzz, process
from models import MODELS


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold()) if not unicodedata.combining(c))


class SearchIndex:
    def __init__(self, store):
        self.store = store
        self.conn = sqlite3.connect(':memory:')
        self.conn.execute("CREATE VIRTUAL TABLE documents USING fts5(title,body,tokenize='unicode61 remove_diacritics 2')")
        self.version = None
        self.items = {}

    def refresh(self):
        version = (self.store.cache_epoch,self.store.conn.total_changes, self.store.conn.execute('PRAGMA data_version').fetchone()[0])
        if version == self.version:
            return
        self.items = {}
        self.conn.execute('DELETE FROM documents')
        for kind in [*MODELS, 'notebook']:
            label = MODELS[kind][0] if kind in MODELS else 'Anotações'
            for raw in self.store.conn.execute(f'SELECT * FROM "{kind}" WHERE deleted_at IS NULL'):
                row = dict(raw)
                title = next((str(row[k]) for k in ('title','topic','passage','name','food_name','drink','exercise') if row.get(k)), label)
                fields = [f.key for f in MODELS[kind][1]] if kind in MODELS else ['title','body','labels','date']
                body = ' '.join(str(row[k]) for k in fields if row.get(k) is not None)
                index = len(self.items) + 1
                self.items[index] = dict(kind=kind, id=row['id'], label=label, title=title,
                                         date=row.get('date') or row.get('due_date') or '', text=body)
                self.conn.execute('INSERT INTO documents(rowid,title,body) VALUES(?,?,?)', (index,title,body))
        self.conn.commit()
        self.version = version

    def search(self, query, limit=40):
        query = query.strip()[:200]
        if not query:
            return []
        self.refresh()
        tokens = re.findall(r'\w+', query, flags=re.UNICODE)[:12]
        exact = []
        if tokens:
            expression = ' AND '.join('"'+word.replace('"','""')+'"*' for word in tokens)
            exact = [r[0] for r in self.conn.execute('SELECT rowid FROM documents WHERE documents MATCH ? ORDER BY bm25(documents,4,1) LIMIT ?', (expression,limit))]
        ranked = list(exact)
        if len(query) >= 3 and len(ranked) < limit:
            candidates = {i: normalize(v['title']+' '+v['text']) for i,v in self.items.items() if i not in exact}
            ranked.extend(i for _,score,i in process.extract(normalize(query), candidates, scorer=fuzz.WRatio,
                                                            score_cutoff=70, limit=limit-len(ranked)))
        return [dict(self.items[i], approximate=i not in exact) for i in ranked[:limit]]

    def close(self):
        self.conn.close()
