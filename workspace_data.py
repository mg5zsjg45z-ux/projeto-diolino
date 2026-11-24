"""Offline notebook and module settings. SQLite writes are transactional."""
import json
from datetime import date, datetime
from navigation import AREAS

ESSENTIAL = {'home', 'checklist', 'data', 'appearance'}
TAGS = {'bold', 'italic', 'underline', 'highlight', 'center', 'right', 'link'}


def module_states(store):
    row = store.conn.execute("SELECT value FROM preferences WHERE key='modules'").fetchone()
    values = json.loads(row[0]) if row else {}
    return {key: key in ESSENTIAL or values.get(key, True) for key, _, _ in AREAS}


def set_modules(store, values):
    states = {key: True if key in ESSENTIAL else bool(values.get(key, True)) for key, _, _ in AREAS}
    with store.conn:
        store.conn.execute("INSERT OR REPLACE INTO preferences VALUES('modules',?)", (json.dumps(states),))


def preference(store, key, default=None, value=None):
    if value is not None:
        with store.conn:
            store.conn.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)', (key, json.dumps(value)))
        return value
    row = store.conn.execute('SELECT value FROM preferences WHERE key=?', (key,)).fetchone()
    return json.loads(row[0]) if row else default


def save_note(store, title, day, body, formatting=None, rid=None, labels='', favorite=False):
    day = date.fromisoformat(day).isoformat()
    if len(title) > 300 or len(body) > 1000000 or len(labels) > 1000:
        raise ValueError('A anotação excede o tamanho permitido.')
    formatting = formatting or []
    for span in formatting:
        if span.get('tag') not in TAGS or not 0 <= span['start'] <= span['end'] <= len(body):
            raise ValueError('Formatação inválida.')
    now = datetime.now().isoformat(timespec='microseconds')
    values = (title.strip() or 'Sem título', day, body, json.dumps(formatting), labels, int(favorite), now)
    with store.conn:
        before = store.conn.execute('SELECT * FROM notebook WHERE id=? AND deleted_at IS NULL', (rid,)).fetchone() if rid else None
        if rid and not before:
            raise ValueError('Esta anotação não está mais disponível.')
        if rid:
            store.conn.execute('UPDATE notebook SET title=?,date=?,body=?,formatting=?,labels=?,favorite=?,updated_at=? WHERE id=?', (*values, rid))
        else:
            rid = store.conn.execute('INSERT INTO notebook(title,date,body,formatting,labels,favorite,updated_at,created_at) VALUES(?,?,?,?,?,?,?,?)', (*values, now)).lastrowid
        store.audit('notebook', rid, 'update' if before else 'create', dict(before) if before else None, dict(title=values[0], date=day, body=body, formatting=formatting, labels=labels, favorite=bool(favorite)))
    return rid


def notes(store, query='', period=''):
    # User search strings are literal text, not SQL LIKE patterns.
    rows = store.conn.execute('SELECT * FROM notebook WHERE deleted_at IS NULL ORDER BY date DESC, created_at DESC').fetchall()
    return [dict(r) for r in rows if r['date'].startswith(period) and query.casefold() in (' '.join(str(r[k]) for k in ('title','body','date','labels'))).casefold()]


def delete_note(store, rid):
    with store.conn:
        row = store.conn.execute('SELECT * FROM notebook WHERE id=? AND deleted_at IS NULL', (rid,)).fetchone()
        if not row:
            return
        store.conn.execute('UPDATE notebook SET deleted_at=? WHERE id=?', (datetime.now().isoformat(), rid))
        store.audit('notebook', rid, 'delete', dict(row), None)
