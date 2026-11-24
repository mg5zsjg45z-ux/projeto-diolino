"""Plans are optional projects, independent of daily pillar confirmation."""
from datetime import date, datetime, timedelta
from storage import validate

TEMPLATES = [
    {'name': 'Semana de estudos médicos', 'area': 'Medicina',
     'objective': 'Organizar temas e revisões da semana.',
     'steps': ['Escolher os temas da semana', 'Separar os materiais de estudo', 'Estudar o primeiro tema', 'Revisar os pontos principais', 'Rever dúvidas ao fim da semana']},
    {'name': 'Organizar a semana', 'area': 'Pessoal',
     'objective': 'Organizar compromissos, prioridades e horários da semana.',
     'steps': ['Conferir a agenda e os plantões', 'Definir prioridades da semana', 'Reservar horários para os três pilares', 'Planejar os cuidados pessoais', 'Revisar o que ficou pendente']},
    {'name': 'Plano de estudo bíblico', 'area': 'Bíblia',
     'objective': 'Definir leituras, registrar reflexões e acompanhar a execução.',
     'steps': ['Escolher o livro ou tema', 'Definir os trechos de leitura', 'Registrar dúvidas e reflexões', 'Revisar os aprendizados']},
]


def list_plans(store, day=None):
    day = day or date.today().isoformat()
    date.fromisoformat(day)
    steps = store.rows('plan_steps')
    result = []
    for plan in store.rows('plans'):
        children = sorted((s for s in steps if s['plan_id'] == plan['id']), key=lambda s: (s['position'] or 0, s['id']))
        done = sum(s['state'] == 'Concluído' for s in children)
        result.append(dict(plan, steps=children, total=len(children), done=done,
                           progress=round(100 * done / len(children)) if children else 0,
                           overdue=sum(s['state'] != 'Concluído' and bool(s['due_date']) and s['due_date'] < day for s in children)))
    return result


def upcoming_steps(store, day):
    week_end = (date.fromisoformat(day) + timedelta(days=6)).isoformat()
    active = {p['id']: p for p in store.rows('plans') if p['status'] == 'Ativo'}
    rows = [dict(s, plan_title=active[s['plan_id']]['title']) for s in store.rows('plan_steps')
            if s['plan_id'] in active and s['state'] != 'Concluído' and s['due_date'] and s['due_date'] <= week_end]
    return sorted(rows, key=lambda s: (s['due_date'], {'Alta': 0, 'Normal': 1, 'Baixa': 2}[s['priority']], s['id']))


def create_plan(store, values, steps):
    if not isinstance(steps, list) or len(steps) > 100:
        raise ValueError('Use até 100 etapas por plano.')
    plan = validate('plans', values)
    prepared = []
    for index, step in enumerate(steps):
        if isinstance(step, str):
            step = {'title': step}
        if not isinstance(step, dict):
            raise ValueError('Etapa inválida.')
        prepared.append(validate('plan_steps', dict(step, plan_id=1, state=step.get('state', 'A fazer'),
                                                   priority=step.get('priority', 'Normal'), position=index)))
    # One transaction: a bad step or failed insert never leaves half a plan.
    def insert(kind, row):
        now = datetime.now().isoformat(timespec='seconds')
        columns = ','.join('"' + key + '"' for key in row)
        placeholders = ','.join('?' for _ in row)
        cursor = store.conn.execute(f'INSERT INTO {kind}({columns},created_at,updated_at) VALUES({placeholders},?,?)', (*row.values(), now, now))
        rid = cursor.lastrowid
        store.audit(kind, rid, 'criar', None, store.get(kind, rid))
        return rid
    with store.conn:
        rid = insert('plans', plan)
        for step in prepared:
            insert('plan_steps', dict(step, plan_id=rid))
    return rid


def check_step(store, rid, checked):
    if not isinstance(checked, bool):
        raise ValueError('Marque ou desmarque a etapa.')
    store.conn.execute('BEGIN IMMEDIATE')
    try:
        row = store.get('plan_steps', rid)
        if not row:
            raise ValueError('Etapa não encontrada.')
        store.save('plan_steps', dict(row, state='Concluído' if checked else 'A fazer'), rid)
    except Exception:
        store.conn.rollback()
        raise


def duplicate_plan(store, rid):
    source = store.get('plans', rid)
    if not source:
        raise ValueError('Plano não encontrado.')
    steps = sorted((s for s in store.rows('plan_steps') if s['plan_id'] == rid), key=lambda s: (s['position'] or 0, s['id']))
    # A copy is a new, unchecked plan with no stale deadlines.
    values = dict(source, title=source['title'] + ' · cópia', status='Ativo', start_date=None, end_date=None)
    return create_plan(store, values, [dict(s, state='A fazer', due_date=None) for s in steps])
