"""Manual, additive reconciliation of active records via portable JSON files."""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from models import MODELS
from storage import validate

FORMAT = 'diolino-sync-1'
LIMIT = 1_800_000
KINDS = ['plans', 'workout', *[k for k in MODELS if k not in ('plans', 'workout')], 'notebook']
NATURAL = dict(study=('date','time','topic'), workout=('date','time','name'), food=('date','time','meal','food_name'),
               hydration=('date','time','drink'), sleep=('date','start','type'), body=('date','time'),
               bible=('date','time','passage'), medication=('date','time','name'), health=('date','time'),
               exams=('date','name'), agenda=('date','time','title'), plans=('title','area'),
               plan_steps=('plan_id','title'), sets=('workout_id','exercise','set_number'),
               energy=('date','weight_kg','height_cm','age_years'), notebook=('date','title'))


def metadata(store):
    row = store.conn.execute("SELECT value FROM preferences WHERE key='manual_sync'").fetchone()
    return json.loads(row[0]) if row else dict(device=uuid.uuid4().hex, aliases={})


def snapshot(store):
    meta = metadata(store)
    records = {}
    for kind in KINDS:
        records[kind] = []
        for raw in store.conn.execute(f'SELECT * FROM "{kind}" ORDER BY id'):
            row = dict(raw)
            if kind == 'notebook':
                values = dict(title=row['title'], date=row['date'], content=row['body'],
                              labels=row['labels'], favorite='Sim' if row['favorite'] else 'Não')
            else:
                values = {field.key: row[field.key] for field in MODELS[kind][1]}
            key = f'{kind}:{row["id"]}'
            aliases = list(dict.fromkeys([f'{meta["device"]}:{key}', *meta['aliases'].get(key, [])]))
            values.update(id=row['id'], sync_ids=aliases, deleted_at=row['deleted_at'])
            if kind == 'food':
                nutrition = store.conn.execute('SELECT snapshot_json FROM food_nutrition WHERE food_id=?', (row['id'],)).fetchone()
                if nutrition:
                    values['_nutrition'] = json.loads(nutrition[0])
            records[kind].append(values)
    return dict(format=FORMAT, source=meta['device'], records=records)


def stamp(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def export_file(store, path):
    meta = metadata(store)
    with store.conn:
        store.conn.execute("INSERT OR REPLACE INTO preferences VALUES('manual_sync',?)", (json.dumps(meta),))
    data = snapshot(store)
    data['exported_at'] = datetime.now(timezone.utc).isoformat()
    # Tombstones are deliberately not propagated by this initial manual version.
    data['records'] = {k: [r for r in rows if not r['deleted_at']] for k, rows in data['records'].items()}
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text.encode()) > LIMIT:
        raise ValueError('O arquivo excede o limite online de 1,8 MB. Nenhum arquivo foi criado.')
    with Path(path).open('x', encoding='utf-8') as file:
        file.write(text)
    return data


def load_file(path):
    if Path(path).stat().st_size > LIMIT:
        raise ValueError('O arquivo excede o limite de 1,8 MB.')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def normalized(kind, row):
    if kind == 'notebook':
        result = {key: row.get(key) for key in ('title', 'date', 'content', 'labels', 'favorite')}
        from datetime import date
        date.fromisoformat(result['date'])
        for key in ('title', 'content', 'labels'):
            if not isinstance(result[key], str) or len(result[key]) > 20000:
                raise ValueError('Anotação inválida ou acima de 20.000 caracteres.')
        if result['favorite'] not in ('Sim', 'Não'):
            raise ValueError('Favorito inválido.')
        return result
    result = validate(kind, row)
    if any(isinstance(v, str) and len(v) > 20000 for v in result.values()):
        raise ValueError('Texto acima do limite online de 20.000 caracteres.')
    if kind == 'food' and row.get('_nutrition'):
        from nutrition import validate_snapshot
        nutrition = row['_nutrition']
        if 'food' not in nutrition:
            nutrition = dict(metadata=nutrition.get('metadata'), food={k: nutrition.get(k) for k in ('code', 'name', 'nutrients')})
        validate_snapshot(nutrition)
        result['_nutrition'] = nutrition
    return result


def reconcile(current, incoming, choices=None):
    """Pure preview; returns a complete candidate and operations. Neither input mutates."""
    choices = choices or {}
    if incoming.get('format') != FORMAT or not isinstance(incoming.get('records'), dict):
        raise ValueError('Use um arquivo exportado pelo botão de troca manual do Diolino.')
    if not isinstance(incoming.get('source'), str) or not incoming['source'] or len(incoming['source']) > 100:
        raise ValueError('Origem inválida.')
    import copy
    result = copy.deepcopy(current)
    mapping, operations, conflicts = {}, [], []
    counts = dict(new=0, same=0, conflicts=0, blocked=0, updated=0)
    for kind in KINDS:
        rows = incoming['records'].get(kind, [])
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError('Lista de registros inválida.')
        local = result['records'].setdefault(kind, [])
        seen, claimed, seen_aliases = set(), set(), set()
        for raw in rows:
            if not isinstance(raw, dict) or not isinstance(raw.get('id'), int) or isinstance(raw['id'], bool) or raw['id'] < 1 or raw['id'] in seen:
                raise ValueError('Identificador inválido ou duplicado.')
            seen.add(raw['id'])
            if raw.get('deleted_at'):
                continue
            aliases = raw.get('sync_ids')
            if not isinstance(aliases, list) or not 1 <= len(aliases) <= 100 or any(not isinstance(a, str) or not a or len(a) > 250 for a in aliases):
                raise ValueError('Vínculo de sincronização inválido.')
            if seen_aliases.intersection(aliases):
                raise ValueError('Vínculo repetido no arquivo.')
            seen_aliases.update(aliases)
            values = normalized(kind, raw)
            blocked = False
            if kind in ('sets', 'plan_steps'):
                parent, field = ('workout', 'workout_id') if kind == 'sets' else ('plans', 'plan_id')
                mapped = mapping.get(f'{parent}:{values[field]}')
                if mapped is None:
                    blocked = True
                else:
                    values[field] = mapped
            if blocked:
                counts['blocked'] += 1
                continue
            matches = [r for r in local if set(r['sync_ids']) & set(aliases)]
            if len(matches) > 1:
                raise ValueError('Vínculos ambíguos. Nenhum dado foi importado.')
            match = matches[0] if matches else None
            if not match:
                identical = [r for r in local if r['id'] not in claimed and not r.get('deleted_at') and normalized(kind, r) == values]
                if len(identical) > 1:
                    raise ValueError('Há registros iguais ambíguos. Revise as duplicações antes de importar.')
                match = identical[0] if identical else None
            if not match and kind in ('daily', 'routine', 'profile'):
                match = next((r for r in local if not r.get('deleted_at') and (kind == 'profile' or r['date'] == values['date'])), None)
            possible = False
            key = f'{kind}:{raw["id"]}'
            if not match and kind in NATURAL:
                similar = [r for r in local if not r.get('deleted_at') and r['id'] not in claimed
                           and all(r.get(k) == values.get(k) for k in NATURAL[kind])]
                if len(similar) > 1:
                    raise ValueError('Há registros semelhantes ambíguos. Revise antes de importar.')
                if similar:
                    possible = True
                    if choices.get(key) != 'separate':
                        match = similar[0]
            if match and match['id'] in claimed:
                raise ValueError('Mais de um registro do arquivo aponta para o mesmo registro local.')
            if match and match.get('deleted_at'):
                counts['blocked'] += 1
                continue
            if match:
                rid = match['id']
                if normalized(kind, match) == values:
                    counts['same'] += 1
                    action = 'same'
                else:
                    counts['conflicts'] += 1
                    conflicts.append(dict(key=key, kind=kind, local=copy.deepcopy(match), incoming=copy.deepcopy(values), possible=possible))
                    action = 'update' if choices.get(key) == 'incoming' else 'keep'
                    if action == 'update':
                        counts['updated'] += 1
                if action == 'update':
                    match.update(values)
                match['sync_ids'] = list(dict.fromkeys([*match['sync_ids'], *aliases]))
            else:
                rid = max([r['id'] for r in local] or [0]) + 1
                action = 'new'
                match = dict(values, id=rid, sync_ids=list(aliases), deleted_at=None)
                local.append(match)
                counts['new'] += 1
            mapping[key] = rid
            claimed.add(rid)
            operations.append(dict(kind=kind, id=rid, action=action, values=values, aliases=match['sync_ids']))
    return dict(candidate=result, operations=operations, conflicts=conflicts, counts=counts)


def preview(store, incoming):
    # Establish identity once; previews never change personal records.
    meta = metadata(store)
    with store.conn:
        store.conn.execute("INSERT OR REPLACE INTO preferences VALUES('manual_sync',?)", (json.dumps(meta),))
    current = snapshot(store)
    return dict(reconcile(current, incoming), base=stamp(current))


def apply_file(store, incoming, base, choices=None):
    safety = store.backup()
    now = datetime.now().isoformat(timespec='microseconds')
    with store.conn:
        store.conn.execute('BEGIN IMMEDIATE')
        current = snapshot(store)
        if stamp(current) != base:
            raise ValueError('Os dados locais mudaram. Gere uma nova prévia antes de importar.')
        plan = reconcile(current, incoming, choices)
        meta = metadata(store)
        for op in plan['operations']:
            kind, rid, values = op['kind'], op['id'], op['values']
            meta['aliases'][f'{kind}:{rid}'] = op['aliases']
            if op['action'] not in ('new', 'update'):
                continue
            before = store.conn.execute(f'SELECT * FROM "{kind}" WHERE id=?', (rid,)).fetchone()
            if kind == 'notebook':
                fields = dict(title=values['title'], date=values['date'], body=values['content'], labels=values['labels'],
                              favorite=int(values['favorite'] == 'Sim'),
                              formatting=before['formatting'] if before and before['body'] == values['content'] else '[]')
            else:
                fields = {f.key: values[f.key] for f in MODELS[kind][1]}
            if before:
                sql = ','.join(f'"{k}"=?' for k in fields)
                store.conn.execute(f'UPDATE "{kind}" SET {sql},updated_at=? WHERE id=?', (*fields.values(), now, rid))
            else:
                keys = ','.join(f'"{k}"' for k in fields)
                slots = ','.join('?' for _ in fields)
                store.conn.execute(f'INSERT INTO "{kind}"(id,{keys},created_at,updated_at) VALUES(?,{slots},?,?)', (rid, *fields.values(), now, now))
            if kind == 'food':
                if values.get('_nutrition'):
                    from nutrition import validate_snapshot
                    nutrition = values['_nutrition']
                    # Online exports use either original desktop snapshot or compact TACO metadata.
                    if 'food' in nutrition:
                        validate_snapshot(nutrition)
                    store.conn.execute('INSERT OR REPLACE INTO food_nutrition VALUES(?,?)', (rid, json.dumps(nutrition)))
                else:
                    store.conn.execute('DELETE FROM food_nutrition WHERE food_id=?', (rid,))
            after = dict(store.conn.execute(f'SELECT * FROM "{kind}" WHERE id=?', (rid,)).fetchone())
            store.audit(kind, rid, 'importar manualmente', dict(before) if before else None, after)
        if store.conn.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Associação inválida; nenhuma alteração foi aplicada.')
        store.conn.execute("INSERT OR REPLACE INTO preferences VALUES('manual_sync',?)", (json.dumps(meta),))
    return dict(counts=plan['counts'], backup=str(safety))
