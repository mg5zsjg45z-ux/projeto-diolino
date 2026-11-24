"""Self-contained A4 documents. Exporting never writes to the personal database."""
import calendar
from datetime import date, datetime, timedelta
from html import escape
from models import MODELS, CHECK_GROUPS

TEMPLATES = {'daily': 'Planner diário', 'weekly': 'Planner semanal', 'monthly': 'Planner mensal',
             'medical': 'Ficha de estudo médico', 'biblical': 'Ficha de estudo bíblico',
             'plan': 'Plano de ação', 'bundle': 'Caderno integrado semanal'}
WEEKDAYS = ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')
MONTHS = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')
CSS = '''
@page{size:A4 portrait;margin:14mm 15mm 16mm}
*{box-sizing:border-box}body{color:#191919;background:#ececec;font:10pt 'Segoe UI',Arial,sans-serif;margin:0;line-height:1.45}
main{width:180mm;margin:12mm auto;background:white;padding:0}h1{font:27pt Georgia,serif;margin:3mm 0 2mm}h2{font-size:13pt;margin:6mm 0 3mm;border-bottom:1px solid #888;padding-bottom:2mm;break-after:avoid}h3{font-size:11pt;margin:0 0 2mm}
.eyebrow{font-size:8pt;letter-spacing:2px;color:#555}.meta,.hint,footer{font-size:8pt;color:#555}header{border-bottom:1.5px solid #222;padding-bottom:4mm;margin-bottom:5mm}footer{border-top:1px solid #aaa;margin-top:5mm;padding-top:2mm}
.sheet{break-before:page;padding:0 0 2mm}.sheet:first-child{break-before:auto}.grid{display:grid;grid-template-columns:1fr 1fr;gap:4mm}.box{border:1px solid #bbb;padding:3mm;break-inside:avoid}.lines{background:repeating-linear-gradient(to bottom,transparent 0,transparent 7mm,#ccc 7mm,#ccc 7.2mm);min-height:22mm}
.line{border-bottom:1px solid #ccc;min-height:8mm}.checks{display:flex;gap:5mm;flex-wrap:wrap}.check{display:inline-block;width:3mm;height:3mm;border:1px solid #333;margin-right:1.5mm;vertical-align:middle}.checked:after{content:'✓';position:relative;top:-1.4mm;font-size:10pt}
table{border-collapse:collapse;width:100%;font-size:8.5pt;table-layout:fixed}th,td{padding:2mm;border:1px solid #bbb;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#f0f0f0}thead{display:table-header-group}tr{break-inside:avoid}.calendar td{height:24mm}.calendar small{display:block;font-size:7pt}.habit td:not(:first-child){padding:1mm;text-align:center}.habit{font-size:7pt}.habit th:first-child{width:31mm}
.entry{border:1px solid #ccc;padding:3mm;margin:3mm 0;break-inside:auto}.entry h3{break-after:avoid}.fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:2mm 4mm}.field{overflow-wrap:anywhere;white-space:pre-wrap}.field.long{grid-column:1/-1}.field strong{display:block;font-size:8pt;color:#555}.field p{margin:0}p,li{overflow-wrap:anywhere}ul{padding-left:5mm;margin:2mm 0}.toolbar{padding:12px;text-align:center;background:#202020;color:white;position:sticky;top:0;z-index:2}.toolbar button{padding:9px 18px;background:white;border:0;margin-right:12px;cursor:pointer}.toolbar span{font-size:12px}.badge{font-size:8pt;border:1px solid #aaa;padding:1mm 2mm}.long{white-space:pre-wrap}.blank-row td{height:8mm}
.lines{background:none;min-height:0}.ruled{height:7mm;border-bottom:1px solid #ccc}.weekday{padding:2mm}.weekday h3{font-size:10pt;margin-bottom:1mm}.weekday .line{min-height:5mm}.weeklyhabits th:first-child{width:46mm}
@media print{body{background:white}main{width:auto;margin:0}.toolbar{display:none}a{color:inherit;text-decoration:none}.lines{-webkit-print-color-adjust:exact;print-color-adjust:exact}th{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
'''


def e(value):
    return escape(str(value if value is not None and value != '' else '–'), quote=True)


def number(value):
    return f'{value:g}'.replace('.', ',') if isinstance(value, (float, int)) else str(value)


def day_label(value):
    return date.fromisoformat(value).strftime('%d/%m/%Y')


def document(title, pages):
    return ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="referrer" content="no-referrer"><title>' + e(title) + '</title><style>' + CSS + '</style></head>'
            '<body><div class="toolbar"><button onclick="window.print()">Imprimir / Salvar PDF</button>'
            '<span>A4 · Retrato · Escala 100% · Desative cabeçalhos e rodapés do navegador</span></div><main>'
            + ''.join(pages) + '</main></body></html>')


def sheet(title, subtitle, body):
    return '<section class="sheet"><header><div class="eyebrow">DIOLINO / CONTROLE PESSOAL</div><h1>' + e(title) + '</h1><div class="meta">' + e(subtitle) + '</div></header>' + body + '<footer>Diolino · Documento local · Anotações em papel não são sincronizadas automaticamente.</footer></section>'


def box(title, height=24):
    return f'<div class="box"><h3>{e(title)}</h3>' + lines(height) + '</div>'


def lines(height):
    return f'<div class="lines" style="min-height:{height}mm">' + '<div class="ruled"></div>' * (height // 7) + '</div>'


def check(label, done=False):
    return '<span><i class="check' + (' checked' if done else '') + '"></i>' + (e(label) if label else '') + '</span>'


def table(headers, rows, cls=''):
    return '<table class="' + cls + '"><thead><tr>' + ''.join('<th>' + e(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + ('' if cell == '' else e(cell)) + '</td>' for cell in row) + '</tr>' for row in rows) + '</tbody></table>'


def scheduled(store, start, end):
    agenda = [dict(r, label=(r['time'] or 'Sem horário') + ' · ' + r['title']) for r in store.rows('agenda')
              if start <= r['date'] <= end and r['state'] != 'Cancelado']
    plans = {p['id']: p for p in store.rows('plans') if p['status'] == 'Ativo'}
    steps = [dict(r, date=r['due_date'], label='Etapa · ' + plans[r['plan_id']]['title'] + ': ' + r['title'])
             for r in store.rows('plan_steps') if r['plan_id'] in plans and r['due_date'] and start <= r['due_date'] <= end]
    return sorted(agenda + steps, key=lambda r: (r['date'], r.get('time') or '', r['id']))


def daily(store, selected, filled):
    iso = selected.isoformat()
    states = store.pillar_states(iso) if filled else {}
    body = '<h2>Pilares diários</h2><div class="checks">' + ''.join(check(label, states.get(key, {}).get('done', False)) for key, label in [
        ('medicine_status', 'Medicina · 60 min'), ('exercise_status', 'Exercício · 40 min'), ('bible_status', 'Estudo bíblico')]) + '</div>'
    body += '<p class="hint">Caixa vazia = item para checar; não significa ausência de realização.</p>'
    body += '<h2>Prioridades</h2>' + ''.join('<div class="line">' + str(i) + '.</div>' for i in range(1, 4))
    body += '<h2>Agenda e etapas dos planos</h2>'
    rows = scheduled(store, iso, iso) if filled else []
    body += '<ul>' + ''.join('<li>' + e(r['label']) + (' [concluído]' if r['state'] == 'Concluído' else '') + '</li>' for r in rows) + '</ul>' if rows else lines(35)
    body += '<h2>Hábitos secundários</h2>'
    record = (store.checklist(iso)['record'] or {}) if filled else {}
    for label, keys in CHECK_GROUPS:
        body += '<p>' + e(label) + ' · ' + ' '.join(check(str(index), record.get(key) == 1) for index, key in enumerate(keys, 1)) + '</p>'
    water = store.checklist(iso) if filled else {}
    actual = number(water['water_ml']) if filled and store.rows('hydration', iso) else '______'
    target = number(water['water_target_ml']) if water.get('water_target_ml') is not None else '______'
    body += '<p>Água: ' + e(actual) + ' mL / meta pessoal: ' + e(target) + ' mL (50 mL/kg cadastrados)</p>'
    body += '<div class="grid">' + box('Sono / saúde / alimentação', 22) + box('Revisão do dia / pendências', 22) + '</div>'
    return sheet('Planner diário', WEEKDAYS[selected.weekday()] + ' · ' + day_label(iso), body)


def weekly(store, selected, filled):
    monday = selected - timedelta(days=selected.weekday())
    end = monday + timedelta(days=6)
    items = scheduled(store, monday.isoformat(), end.isoformat()) if filled else []
    body = '<div class="grid">' + box('Prioridades da semana', 16) + box('Plantões / compromissos fixos', 16) + '</div><h2>Programação semanal</h2>'
    for index in range(7):
        current = monday + timedelta(days=index)
        rows = [r for r in items if r['date'] == current.isoformat()]
        states = store.pillar_states(current.isoformat()) if filled else {}
        body += '<div class="box weekday" style="margin-bottom:2mm"><h3>' + WEEKDAYS[index] + ' · ' + current.strftime('%d/%m') + '</h3><div class="checks">' + ''.join(check(label, states.get(key, {}).get('done', False)) for key, label in [('medicine_status','Medicina 60 min'),('exercise_status','Exercício 40 min'),('bible_status','Bíblia')]) + '</div>'
        body += '<ul>' + ''.join('<li>' + e(r['label']) + '</li>' for r in rows) + '</ul>' if rows else '<div class="line"></div>'
        body += '</div>'
    body += '<p class="hint">Os três pilares também se aplicam ao domingo. Use as páginas diárias para detalhar os hábitos.</p>'
    subtitle = day_label(monday.isoformat()) + ' a ' + day_label(end.isoformat())
    habits = table(['Hábitos / registros'] + [d[:3] for d in WEEKDAYS], [[label] + [''] * 7 for label in ['Escovação 1 / 2 / 3', 'Banho 1 / 2', 'Medicação 1 / 2', 'Água mL / meta', 'Sono (horas)', 'Peso (kg)', 'Alimentação / kcal']], 'weeklyhabits')
    habits += '<p class="hint">Registre as checagens nos campos do dia. A meta pessoal de água é calculada no aplicativo a partir do peso cadastrado.</p>'
    habits += '<h2>Revisão semanal</h2>' + box('Resultados / registros pendentes', 35) + box('Prioridades para a próxima semana', 35)
    return sheet('Planner semanal', subtitle, body) + sheet('Hábitos semanais', subtitle, habits)


def monthly(store, selected, filled):
    weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(selected.year, selected.month)
    title = MONTHS[selected.month - 1] + ' de ' + str(selected.year)
    body = '<div class="grid">' + box('Objetivos do mês', 16) + box('Datas / compromissos prioritários', 16) + '</div><h2>Calendário</h2>'
    body += '<table class="calendar"><thead><tr>' + ''.join('<th>' + d[:3] + '</th>' for d in WEEKDAYS) + '</tr></thead><tbody>'
    for week in weeks:
        body += '<tr>'
        for day in week:
            body += '<td>'
            if day:
                body += '<strong>' + str(day) + '</strong>'
                if filled:
                    states = store.pillar_states(date(selected.year, selected.month, day).isoformat())
                    body += '<small>' + ' · '.join(k + ':' + ('✓' if s['done'] else '–' if not s['known'] else '○') for k, s in zip(('M', 'E', 'B'), states.values())) + '</small>'
            body += '</td>'
        body += '</tr>'
    body += '</tbody></table><p class="hint">M: medicina · E: exercício · B: Bíblia. ✓ confirmado · ○ informado sem confirmação · – sem informação.</p>'
    pages = [sheet('Planner mensal', title, body)]
    body = '<h2>Checagem mensal</h2>'
    # Two tables keep the writing cells large enough on portrait A4.
    days = calendar.monthrange(selected.year, selected.month)[1]
    for start, finish in [(1, 16), (17, days)]:
        body += table(['Hábito'] + list(range(start, finish + 1)), [[label] + [''] * (finish - start + 1) for label in ['Medicina', 'Exercício', 'Bíblia', 'Higiene 3×', 'Banho 2×', 'Água', 'Medicação 2×']], 'habit') + '<br>'
    body += box('Revisão mensal / ajustes', 16)
    pages.append(sheet('Hábitos mensais', title, body))
    if filled:
        rows = scheduled(store, selected.replace(day=1).isoformat(), selected.replace(day=days).isoformat())
        pages.append(sheet('Agenda mensal', title, table(['Data', 'Compromisso / etapa'], [(day_label(r['date']), r['label']) for r in rows]) if rows else '<p>–</p>'))
    return pages


def study_page(kind, selected, reference=''):
    title = 'Estudo médico' if kind == 'medical' else 'Estudo bíblico'
    body = '<p>Data: ' + day_label(selected.isoformat()) + ' · ' + ('Tema / fonte: ____________________' if kind == 'medical' else 'Passagem / versão: ' + e(reference or '____________________')) + '</p>'
    prompts = (['Objetivo / perguntas', 'Conteúdo / evidências', 'Aplicação / pontos de atenção', 'Resumo / revisão programada'] if kind == 'medical'
               else ['Observação / contexto', 'Interpretação / comparação de versões', 'Aplicação / reflexão', 'Dúvidas / oração / próxima leitura'])
    body += ''.join(box(prompt, 38) for prompt in prompts)
    return sheet(title, 'FICHA DE ESTUDO', body)


def plan_page(selected):
    body = box('Objetivo / resultado esperado', 21) + '<p>Início: __/__/____ · Prazo: __/__/____ · Prioridade: __________</p>'
    body += '<h2>Etapas</h2><table><thead><tr><th style="width:12mm">OK</th><th>Etapa / critério de conclusão</th><th style="width:30mm">Prazo</th></tr></thead><tbody>' + ''.join('<tr class="blank-row"><td>' + check('') + '</td><td></td><td></td></tr>' for _ in range(10)) + '</tbody></table>'
    body += '<h2>Acompanhamento</h2>' + box('Pendências / ajustes / avaliação', 21)
    return sheet('Plano de ação', day_label(selected.isoformat()), body)


def build_template(store, kind, day, filled=False, reference=''):
    selected = date.fromisoformat(day)
    if kind not in TEMPLATES:
        raise ValueError('Modelo inválido.')
    if kind == 'daily': pages = [daily(store, selected, filled)]
    elif kind == 'weekly': pages = [weekly(store, selected, filled)]
    elif kind == 'monthly': pages = monthly(store, selected, filled)
    elif kind in ('medical', 'biblical'): pages = [study_page(kind, selected, reference)]
    elif kind == 'plan': pages = [plan_page(selected)]
    else:
        monday = selected - timedelta(days=selected.weekday())
        pages = [weekly(store, monday, filled)] + [daily(store, monday + timedelta(days=i), filled) for i in range(7)]
        pages += [study_page('medical', selected), study_page('biblical', selected, reference), plan_page(selected)]
    return document(TEMPLATES[kind], pages)


def build_report(store, start, end, kinds, include_notes=True, include_summary=True, include_empty=False):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last < first or (last - first).days > 365:
        raise ValueError('Escolha um período de até 366 dias, com o fim após o início.')
    if not isinstance(kinds, (list, tuple)) or any(kind not in MODELS for kind in kinds):
        raise ValueError('Área de relatório inválida.')
    if not kinds and not include_summary:
        raise ValueError('Selecione ao menos uma área ou o resumo da rotina.')
    subtitle = day_label(start) + ' a ' + day_label(end) + ' · Gerado em ' + datetime.now().strftime('%d/%m/%Y %H:%M')
    pages = []
    if include_summary:
        rows = []
        current = first
        while current <= last:
            iso = current.isoformat()
            s, states = store.summary(iso), store.pillar_states(iso)
            status = lambda key: 'Sim' if states[key]['done'] else '–' if not states[key]['known'] else states[key]['source'].replace('Seu relato: ', '')
            rows.append([day_label(iso), number(s['study_min']) if s['study_count'] else '–', number(s['exercise_min']) if s['exercise_count'] else '–',
                         status('medicine_status'), status('exercise_status'), status('bible_status'),
                         number(s['sleep_min'] / 60) if s['sleep_count'] else '–'])
            current += timedelta(days=1)
        pages.append(sheet('Relatório de rotina', subtitle, '<p class="hint">– = ausência de informação. Confirmações consideram o fechamento diário e os registros. Horas de sono incluem cochilos.</p>' + table(['Data', 'Medicina min', 'Exercício min', 'Medicina confirmada', 'Exercício confirmado', 'Bíblia confirmada', 'Sono h'], rows)))
    workouts = {r['id']: r for r in store.rows('workout')}
    plans = {r['id']: r for r in store.rows('plans')}
    for kind in dict.fromkeys(kinds):
        records = store.rows(kind)
        if kind == 'sets':
            records = [r for r in records if r['workout_id'] in workouts and start <= workouts[r['workout_id']]['date'] <= end]
        elif kind == 'plan_steps':
            records = [r for r in records if not r['due_date'] or start <= r['due_date'] <= end]
        elif kind == 'plans':
            records = [r for r in records if (not r['start_date'] or r['start_date'] <= end) and (not r['end_date'] or r['end_date'] >= start)]
        elif kind != 'profile':
            records = [r for r in records if start <= r['date'] <= end]
        records.sort(key=lambda r: (r.get('date') or r.get('due_date') or '', r.get('time') or '', r['id']))
        if not records and not include_empty:
            continue
        body = '<p class="hint">' + str(len(records)) + ' registro(s). Campos sem informação: –.' + (' Planos sem datas, etapas sem prazo e perfil são incluídos quando selecionados.' if kind in ('plans', 'plan_steps', 'profile') else '') + '</p>'
        for row in records:
            body += '<article class="entry"><h3>Registro #' + str(row['id']) + '</h3><div class="fields">'
            for field in MODELS[kind][1]:
                if not include_notes and field.type == 'long':
                    continue
                value = row.get(field.key)
                if value is not None and value != '':
                    if field.type == 'date': value = day_label(value)
                    elif field.type == 'datetime': value = datetime.fromisoformat(value).strftime('%d/%m/%Y %H:%M')
                    elif field.type == 'workout':
                        linked = workouts.get(value, {})
                        value = f"#{value} · {linked.get('date', '')} · {linked.get('name', '')}"
                    elif field.type == 'plan': value = f"#{value} · {plans.get(value, {}).get('title', '')}"
                    elif field.type in ('number', 'integer'): value = number(value)
                body += '<div class="field' + (' long' if field.type == 'long' else '') + '"><strong>' + e(field.label) + '</strong><p>' + e(value) + '</p></div>'
            body += '</div></article>'
        pages.append(sheet(MODELS[kind][0], subtitle, body))
    if not pages:
        pages.append(sheet('Relatório Diolino', subtitle, '<p>Nenhum registro nas áreas e no período selecionados.</p>'))
    return document('Relatório Diolino', pages)
