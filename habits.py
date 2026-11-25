"""Personal weekly habits and dated goals stored with the local preferences."""
from datetime import date, timedelta
import json
from uuid import uuid4


def save_habit(store, name, target, day, key=None):
    name = name.strip()
    if not name or len(name) > 100 or type(target) is not int or not 1 <= target <= 7:
        raise ValueError('Informe um nome e uma frequência entre 1 e 7 dias por semana.')
    key = key or uuid4().hex
    day = date.fromisoformat(day).isoformat()
    write_event(store, f'habit_goal:{key}:{day}', {'name': name, 'target': target})
    return key


def write_event(store, key, value):
    with store.conn:
        store.conn.execute('BEGIN IMMEDIATE')
        previous = store.conn.execute('SELECT value FROM preferences WHERE key=?', (key,)).fetchone()
        store.conn.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)', (key, json.dumps(value)))
        store.audit('habits', key, 'registrar', json.loads(previous[0]) if previous else None, value)


def week_status(store, day):
    end = date.fromisoformat(day)
    start = (end - timedelta(days=end.weekday())).isoformat()
    goals = {}
    for key, raw in store.conn.execute("SELECT key,value FROM preferences WHERE key GLOB 'habit_goal:*' ORDER BY key"):
        _, habit, effective = key.split(':')
        if effective <= day:
            goals[habit] = dict(json.loads(raw), id=habit, done=0, observed=0, today=None)
    for key, raw in store.conn.execute("SELECT key,value FROM preferences WHERE key GLOB 'habit_day:*'"):
        _, habit, recorded = key.split(':')
        if habit in goals and start <= recorded <= day:
            value = json.loads(raw)
            goals[habit]['done'] += int(value)
            goals[habit]['observed'] += 1
            if recorded == day:
                goals[habit]['today'] = value
    return sorted(goals.values(), key=lambda g: g['name'].casefold())


def record_habit(store, key, day, done):
    if type(done) is not bool or key not in {g['id'] for g in week_status(store, day)}:
        raise ValueError('Hábito ou registro inválido para esta data.')
    write_event(store, f'habit_day:{key}:{day}', done)
