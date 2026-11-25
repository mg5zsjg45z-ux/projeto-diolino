"""Local FSRS cards in the existing preferences table; no schema migration."""
import json
import uuid
from datetime import datetime, timezone, timedelta
from fsrs import Card, Scheduler, Rating

PREFIX = 'review_card:'


def cards(store, due_only=False, now=None):
    now = now or datetime.now(timezone.utc)
    result = [json.loads(row[0]) for row in store.conn.execute("SELECT value FROM preferences WHERE key LIKE 'review_card:%'")]
    result = [r for r in result if not r.get('archived')]
    if due_only:
        result = [r for r in result if Card.from_json(r['schedule']).due <= now]
    return sorted(result, key=lambda r: (Card.from_json(r['schedule']).due, r['id']))


def get_card(store, key):
    row = store.conn.execute('SELECT value FROM preferences WHERE key=?', (PREFIX+key,)).fetchone()
    return json.loads(row[0]) if row else None


def save_card(store, question, answer, area='Medicina', key=None, expected=None, source=''):
    question, answer = question.strip(), answer.strip()
    if not question or not answer or len(question)>10000 or len(answer)>20000 or len(source)>1000:
        raise ValueError('Preencha pergunta e resposta, dentro dos limites de 10.000 e 20.000 caracteres.')
    if area not in ('Medicina','Bíblia','Pessoal'):
        raise ValueError('Área inválida.')
    with store.conn:
        store.conn.execute('BEGIN IMMEDIATE')
        before = get_card(store,key) if key else None
        if key and (not before or before['revision'] != expected):
            raise ValueError('O cartão mudou. Abra-o novamente antes de salvar.')
        key = key or uuid.uuid4().hex
        result = dict(before or {}, id=key,question=question,answer=answer,area=area,source=source,
                      archived=False,revision=(before or {}).get('revision',0)+1,
                      schedule=before['schedule'] if before else Card().to_json())
        store.conn.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)', (PREFIX+key,json.dumps(result,ensure_ascii=False)))
        store.audit('review_cards',key,'editar' if before else 'criar',before,result)
    return result


def rate_card(store, key, rating, expected, now=None):
    now = now or datetime.now(timezone.utc)
    with store.conn:
        store.conn.execute('BEGIN IMMEDIATE')
        before = get_card(store,key)
        if not before or before.get('archived') or before['revision'] != expected:
            raise ValueError('O cartão mudou. Atualize a revisão antes de responder.')
        card = Card.from_json(before['schedule'])
        if card.due > now:
            raise ValueError('Este cartão ainda não está agendado para revisão.')
        updated, log = Scheduler().review_card(card,Rating(rating),review_datetime=now)
        result = dict(before,schedule=updated.to_json(),revision=before['revision']+1)
        store.conn.execute('UPDATE preferences SET value=? WHERE key=?',(json.dumps(result,ensure_ascii=False),PREFIX+key))
        store.audit('review_cards',key,'revisar',before,dict(result,review_log=log.to_json()))
    return result


def archive_card(store,key,expected):
    with store.conn:
        store.conn.execute('BEGIN IMMEDIATE')
        before=get_card(store,key)
        if not before or before['revision']!=expected:
            raise ValueError('O cartão mudou. Atualize a lista.')
        result=dict(before,archived=True,revision=before['revision']+1)
        store.conn.execute('UPDATE preferences SET value=? WHERE key=?',(json.dumps(result,ensure_ascii=False),PREFIX+key))
        store.audit('review_cards',key,'arquivar',before,result)


def review_forecast(store, days=7, now=None, area='Todas', local_tz=None):
    """Count current due dates, not simulated future reviews. Read-only."""
    if type(days) is not int or not 1 <= days <= 90:
        raise ValueError('Período inválido.')
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError('Horário sem fuso.')
    if area not in ('Todas', 'Medicina', 'Bíblia', 'Pessoal'):
        raise ValueError('Área inválida.')
    local_day = now.astimezone(local_tz).date()
    buckets = [0] * days
    overdue = 0
    for row in cards(store):
        if area != 'Todas' and row['area'] != area:
            continue
        due = Card.from_json(row['schedule']).due
        if due <= now:
            overdue += 1
            continue
        offset = (due.astimezone(local_tz).date() - local_day).days
        if 0 <= offset < days:
            buckets[offset] += 1
    return {'pending': overdue, 'days': [
        {'date': (local_day + timedelta(days=i)).isoformat(), 'count': count}
        for i, count in enumerate(buckets)
    ]}
