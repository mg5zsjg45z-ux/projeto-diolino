"""Organized application views, chart exploration and energy calculator."""
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox
from datetime import date, timedelta
from charts import chart
from energy import energy_estimate, FORMULA_SOURCE, ACTIVITY_SOURCE
from theme import SURFACE, INK, MUTED, LINE
from surface_ui import card_body
from design_system import metric_card, adaptive_grid, action_grid
from workspace_data import module_states


def num(value):
    return '—' if value is None else f'{value:g}'.replace('.', ',')


def brday(day):
    return date.fromisoformat(day).strftime('%d/%m/%Y')


def pillar_visual(state):
    if state['done']:
        return '✓', '#237653', '#e9f4ed', 'Confirmado'
    if state['source'] == 'Seu relato: Não realizado':
        return '×', '#b84f48', '#faeeeb', 'Não realizado'
    if state['known']:
        return '◔', MUTED, '#f0f0ed', 'Em andamento'
    return '–', '#8b8b84', '#f0f0ed', '–'


class OrganizedViews:
    def open_editor(self, kind, record=None):
        from app import Editor
        return Editor(self, kind, record)

    def section_links(self, links):
        row = ttk.Frame(self.content)
        row.pack(fill='x', pady=(12, 18))
        for i, (label, target) in enumerate(links):
            ttk.Button(row, text=label, style='Accent.TButton' if i == 0 else 'TButton',
                       command=lambda p=target: self.navigate(p)).grid(row=i // 4, column=i % 4, sticky='ew', padx=(0, 8), pady=4)
            row.columnconfigure(i % 4, weight=1)

    def pillar_cards(self):
        summary = self.store.summary(self.day.get())
        states = self.store.pillar_states(self.day.get())
        panel = ttk.Frame(self.content)
        panel.pack(fill='x', pady=(0, 16))
        specs = [('Medicina', 'medicine_status', 'study', f"{num(summary['study_min'])} / 60 min" if summary['study_count'] else '–'),
                 ('Exercício', 'exercise_status', 'workout', f"{num(summary['exercise_min'])} / 40 min" if summary['exercise_count'] else '–'),
                 ('Bíblia', 'bible_status', 'bible', f"{summary['bible_count']} estudo(s)" if summary['bible_count'] else '–')]
        self.pillar_buttons = {}
        for col, (label, key, model, progress) in enumerate(specs):
            tile = card_body(panel, padding=22)
            tile.master.grid(row=0, column=col, sticky='nsew', padx=(0, 8))
            panel.columnconfigure(col, weight=1, uniform='pillars')
            ttk.Label(tile, text=label.upper(), font=('Segoe UI Semibold', 9), style='SurfaceMuted.TLabel').pack(anchor='w')
            symbol, color, background, caption = pillar_visual(states[key])
            tk.Label(tile, text=symbol + '  ' + caption, fg=color, bg=SURFACE, font=('Segoe UI Semibold', 11)).pack(anchor='w', pady=(10, 0))
            ttk.Label(tile, text=progress, font=('Georgia', 22), style='Surface.TLabel').pack(anchor='w', pady=(14, 18))
            var = tk.BooleanVar(value=states[key]['done'])
            button = ttk.Checkbutton(tile, text='Compromisso cumprido', variable=var, style='Surface.TCheckbutton',
                command=lambda k=key, v=var, d=self.day.get(): self.toggle_pillar(d, k, v.get()))
            button.pack(anchor='w')
            self.pillar_buttons[key] = (button, var)
            ttk.Label(tile, text='–' if not states[key]['known'] else states[key]['source'], style='SurfaceMuted.TLabel').pack(anchor='w', pady=(8, 14))
            ttk.Button(tile, text='Registrar detalhes', command=lambda k=model: self.open_editor(k)).pack(anchor='w')

    def toggle_pillar(self, day, key, checked):
        self.store.set_pillar(day, key, checked)
        self.set_status('Checagem do pilar salva. Os registros detalhados foram preservados.')
        self.render()

    def render_overview(self):
        self.heading('Minha central diária', f'{brday(self.day.get())} · Registros, metas e próximos compromissos.')
        s = self.store.summary(self.day.get())
        states = self.store.pillar_states(self.day.get())
        weight = self.store.latest_measurement(self.day.get())
        metrics = ttk.Frame(self.content)
        metrics.pack(fill='x', pady=(0, 12))
        from review_cards import cards as review_cards
        pending = len(review_cards(self.store, due_only=True))
        adaptive_grid(metrics, [
            metric_card(metrics, 'Medicina', f"{num(s['study_min'])} / 60 min" if s['study_count'] else '—', 'Tempo registrado na data selecionada'),
            metric_card(metrics, 'Exercício', f"{num(s['exercise_min'])} / 40 min" if s['exercise_count'] else '—', 'Tempo registrado na data selecionada'),
            metric_card(metrics, 'Revisões pendentes', str(pending), 'Fila FSRS no momento atual'),
        ])
        enabled = module_states(self.store)
        actions = [('Checagem diária', lambda: self.navigate('checklist')),
                   ('Buscar em tudo', self.show_global_search)]
        if enabled.get('studies', True):
            actions.extend([('Iniciar Pomodoro', self.show_pomodoro), ('Revisar cartões', self.show_review_cards)])
        if enabled.get('agenda', True):
            actions.append(('Agenda', lambda: self.navigate('agenda')))
        if enabled.get('planning', True):
            actions.append(('Meus planos', lambda: self.navigate('planning')))
        action_grid(self.content, actions)
        cards = ttk.Frame(self.content)
        cards.pack(fill='x')
        frame = card_body(cards, padding=22)
        frame.master.grid(row=0, column=0, sticky='nsew')
        cards.columnconfigure(0, weight=1, uniform='cards')
        tk.Label(frame, text='PILARES DIÁRIOS', bg=SURFACE, fg=MUTED, font=('Segoe UI Semibold', 9)).pack(anchor='w')
        indicators = tk.Frame(frame, bg=SURFACE)
        indicators.pack(fill='x', pady=(15, 12))
        for index, (key, title) in enumerate([('medicine_status', 'Medicina'), ('exercise_status', 'Exercício'), ('bible_status', 'Bíblia')]):
            symbol, color, fill, caption = pillar_visual(states[key])
            column = tk.Frame(indicators, bg=SURFACE)
            column.grid(row=0, column=index, sticky='nsew')
            indicators.columnconfigure(index, weight=1)
            canvas = tk.Canvas(column, width=42, height=42, bg=SURFACE, highlightthickness=0)
            canvas.create_oval(2, 2, 40, 40, fill=fill, outline=fill)
            canvas.create_text(21, 21, text=symbol, fill=color, font=('Segoe UI Semibold', 20))
            canvas.pack()
            canvas.bind('<Button-1>', lambda _: self.navigate('checklist'))
            tk.Label(column, text=title, bg=SURFACE, fg=INK, font=('Segoe UI', 9)).pack(pady=(5, 0))
            tk.Label(column, text=caption, bg=SURFACE, fg=color, font=('Segoe UI', 8)).pack()
        self.card(cards, 1, 'ÚLTIMO PESO', f"{num(weight['weight_kg'])} kg" if weight else '–', brday(weight['date']) if weight else 'Adicione em Saúde › Medidas')
        self.card(cards, 2, 'SONO DO DIA', f"{s['sleep_min']/60:.1f} h".replace('.', ',') if s['sleep_count'] else '–', 'Sono principal e cochilos registrados')
        self.section_links([('Fazer checagem diária', 'checklist'), ('Consultar saúde', 'health_overview'), ('Abrir agenda', 'agenda'), ('Calculadora calórica', 'calculator')])
        agenda = card_body(self.content, padding=24)
        agenda.master.pack(fill='x', pady=(8, 0))
        header = ttk.Frame(agenda, style='Surface.TFrame')
        header.pack(fill='x')
        ttk.Label(header, text='Próximos compromissos', style='Surface.TLabel', font=('Georgia', 18)).pack(side='left')
        ttk.Button(header, text='Ver agenda  →', command=lambda: self.navigate('agenda')).pack(side='right')
        ttk.Label(agenda, text='Tarefas, compromissos e anotações para os próximos dias.',
                  style='SurfaceMuted.TLabel').pack(anchor='w', pady=(8, 20))
        ttk.Separator(agenda).pack(fill='x')
        upcoming = self.store.upcoming_agenda(self.day.get())[:4]
        for r in upcoming:
            row = ttk.Frame(agenda, style='Surface.TFrame', padding=(0, 14))
            row.pack(fill='x')
            ttk.Label(row, text=f"{r['start'][8:10]}/{r['start'][5:7]}  {r['start'][11:]}",
                      style='SurfaceMuted.TLabel', width=17).pack(side='left')
            ttk.Label(row, text=r['title'], style='Surface.TLabel', wraplength=650).pack(side='left', fill='x')
            ttk.Separator(agenda).pack(fill='x')
        if not upcoming:
            empty = ttk.Frame(agenda, style='Surface.TFrame', padding=(0, 24, 0, 8))
            empty.pack(fill='x')
            ttk.Label(empty, text='\ue787', font=('Segoe MDL2 Assets', 24), style='SurfaceMuted.TLabel').pack(side='left', padx=(0, 18))
            copy = ttk.Frame(empty, style='Surface.TFrame')
            copy.pack(side='left', fill='x')
            ttk.Label(copy, text='Nenhum compromisso pendente', font=('Segoe UI Semibold', 11), style='Surface.TLabel').pack(anchor='w')
            ttk.Label(copy, text='Adicione uma tarefa ou nota na agenda quando precisar.', style='SurfaceMuted.TLabel').pack(anchor='w', pady=(5, 0))

    def render_health_overview(self):
        self.heading('Saúde', 'Antropometria, sono, alimentação e acompanhamento de saúde reunidos nesta área.')
        end = date.fromisoformat(self.day.get())
        start = end - timedelta(days=29)
        s = self.store.summary(self.day.get())
        water = self.store.checklist(self.day.get())
        cards = ttk.Frame(self.content)
        cards.pack(fill='x')
        self.card(cards, 0, 'CALORIAS REGISTRADAS', f"{num(s['kcal'])} kcal" if s['food_count'] else '–', f"{s['unknown_kcal']} alimento(s) sem calorias · não confirma o total do dia")
        self.card(cards, 1, 'ÁGUA REGISTRADA', f"{num(water['water_ml']/1000)} L", f"Meta pessoal: {num(water['water_target_ml']/1000)} L" if water['water_target_ml'] else 'Cadastre o peso para calcular a meta')
        self.card(cards, 2, 'MEDICAÇÃO', f"{water['counts']['Checagem da medicação']} / 2", 'Checagens da rotina prescrita')
        self.section_links([('Registrar medidas', 'body'), ('Registrar sono', 'sleep'), ('Rever alimentação', 'food'), ('Estimar gasto calórico', 'calculator')])
        chart(self.content, 'Peso · últimos 30 dias (kg)', self.store.body_series('weight_kg', start.isoformat(), self.day.get()), start, end, 'kg').pack(fill='x', pady=(0, 14))
        chart(self.content, 'Sono registrado · últimos 30 dias (h)', self.metric_points('sleep', start, end), start, end, 'h', bars=True).pack(fill='x')
        ttk.Label(self.content, text='As linhas ligam apenas medições existentes. Use Gráficos para explorar outras medidas e períodos.', style='Muted.TLabel').pack(anchor='w', pady=10)

    def metric_points(self, metric, start, end):
        if metric.startswith('body:'):
            return self.store.body_series(metric.split(':')[1], start.isoformat(), end.isoformat())
        points = []
        for i in range((end - start).days + 1):
            day = (start + timedelta(days=i)).isoformat()
            s = self.store.summary(day)
            if metric == 'sleep' and s['sleep_count']:
                points.append((day, s['sleep_min'] / 60))
            elif metric == 'calories' and s['food_count'] and s['unknown_kcal'] == 0:
                points.append((day, s['kcal']))
            elif metric == 'water' and self.store.rows('hydration', day):
                points.append((day, s['water_ml'] / 1000))
            elif metric == 'exercise' and s['exercise_count']:
                points.append((day, s['exercise_min']))
            elif metric == 'study' and s['study_count']:
                points.append((day, s['study_min']))
            elif metric == 'pillars':
                states = self.store.pillar_states(day)
                if any(v['known'] for v in states.values()):
                    points.append((day, sum(v['done'] for v in states.values())))
        return points

    def render_graphs(self):
        self.heading('Evolução da saúde', 'Escolha uma medida e um período. Passe o mouse sobre os pontos para consultar os valores.')
        options = {'Peso (kg)': ('body:weight_kg', 'kg'), 'Cintura (cm)': ('body:waist_cm', 'cm'),
                   'Quadril (cm)': ('body:hip_cm', 'cm'), 'Tórax (cm)': ('body:chest_cm', 'cm'),
                   'Braço (cm)': ('body:arm_cm', 'cm'), 'Coxa (cm)': ('body:thigh_cm', 'cm'),
                   'Gordura corporal (%)': ('body:fat_pct', '%'), 'Sono (h)': ('sleep', 'h'),
                   'Calorias registradas (kcal)': ('calories', 'kcal'), 'Água (L)': ('water', 'L')}
        if not hasattr(self, 'graph_metric'):
            self.graph_metric = tk.StringVar(value='Peso (kg)')
            self.graph_days = tk.StringVar(value='30')
        controls = ttk.Frame(self.content)
        controls.pack(fill='x', pady=(0, 18))
        ttk.Label(controls, text='Indicador').pack(side='left')
        combo = ttk.Combobox(controls, textvariable=self.graph_metric, values=list(options), state='readonly', width=30)
        combo.pack(side='left', padx=8)
        combo.bind('<<ComboboxSelected>>', lambda _: self.render())
        ttk.Label(controls, text='Dias').pack(side='left', padx=(12, 0))
        days = ttk.Combobox(controls, textvariable=self.graph_days, values=['7', '30', '90', '365'], state='readonly', width=6)
        days.pack(side='left', padx=8)
        days.bind('<<ComboboxSelected>>', lambda _: self.render())
        end = date.fromisoformat(self.day.get())
        start = end - timedelta(days=int(self.graph_days.get()) - 1)
        metric, unit = options[self.graph_metric.get()]
        points = self.metric_points(metric, start, end)
        chart(self.content, self.graph_metric.get(), points, start, end, unit, bars=not metric.startswith('body:'), height=300).pack(fill='x')
        if points:
            first, last = points[0], points[-1]
            text = f'{len(points)} dia(s) com informação · Primeiro: {num(first[1])} {unit} · Último: {num(last[1])} {unit}'
            if metric.startswith('body:') and len(points) > 1:
                text += f' · Variação: {last[1]-first[1]:+.1f} {unit}'
            ttk.Label(self.content, text=text, wraplength=850).pack(anchor='w', pady=12)
        ttk.Label(self.content, text='Medidas: última medição disponível de cada dia. Sono e consumo: soma dos registros.\nDias sem informação não viram zero. Calorias com valores faltantes são omitidas; os demais totais ainda dependem de você registrar todas as refeições.', wraplength=900, style='Muted.TLabel').pack(anchor='w', pady=10)

    def render_activity_overview(self, studies=False, adherence=False):
        title = 'Constância dos pilares' if adherence else 'Estudos' if studies else 'Treinos'
        self.heading(title, 'Consulte seus registros e acompanhe a evolução dos últimos 30 dias.')
        if studies:
            self.section_links([('Estudo médico', 'study'), ('Estudo bíblico', 'bible')])
            ttk.Button(self.content, text='Iniciar Pomodoro', style='Accent.TButton',
                       command=self.show_pomodoro).pack(anchor='w', pady=(0, 14))
            ttk.Button(self.content,text='Cartões de revisão espaçada',command=self.show_review_cards).pack(anchor='w',pady=(0,14))
        elif not adherence:
            self.section_links([('Treinos e atividades', 'workout'), ('Séries e cargas', 'sets')])
        end = date.fromisoformat(self.day.get())
        start = end - timedelta(days=29)
        metric = 'pillars' if adherence else 'study' if studies else 'exercise'
        unit = 'pilares' if adherence else 'min'
        chart(self.content, title, self.metric_points(metric, start, end), start, end, unit, bars=True, height=300,
              fixed_max=3 if adherence else None).pack(fill='x')
        ttk.Label(self.content, text='Dias sem registros ficam em aberto. Consulte os detalhes nas abas acima.', style='Muted.TLabel').pack(anchor='w', pady=12)

    def render_calculator(self):
        self.heading('Calculadora calórica', 'Simule gasto em repouso, gasto diário total e déficit. Os parâmetros são estimativas editáveis.')
        if not hasattr(self, 'calc_vars') or self.calc_day != self.day.get():
            self.calc_day = self.day.get()
            profile = next(iter(self.store.rows('profile')), {})
            weight = self.store.latest_measurement(self.day.get())
            age = ''
            if profile.get('birth_date'):
                birth, reference = date.fromisoformat(profile['birth_date']), date.fromisoformat(self.day.get())
                age = reference.year - birth.year - ((reference.month, reference.day) < (birth.month, birth.day))
            initial = {'weight_kg': weight['weight_kg'] if weight else '', 'height_cm': profile.get('height_cm') or '',
                       'age_years': age, 'coefficient': '', 'activity_factor': '', 'deficit_pct': '0'}
            self.calc_vars = {key: tk.StringVar(value=num(value) if isinstance(value, (int, float)) else str(value)) for key, value in initial.items()}
            for var in self.calc_vars.values():
                var.trace_add('write', lambda *_: self.invalidate_calculation())
        form = ttk.Frame(self.content)
        form.pack(fill='x')
        labels = [('weight_kg', 'Peso (kg)'), ('height_cm', 'Altura (cm)'), ('age_years', 'Idade (anos)'),
                  ('coefficient', 'Coeficiente da equação'), ('activity_factor', 'Fator de atividade'), ('deficit_pct', 'Déficit simulado (%)')]
        for i, (key, label) in enumerate(labels):
            box = ttk.Frame(form, padding=(0, 0, 18, 12))
            box.grid(row=i // 3, column=i % 3, sticky='ew')
            form.columnconfigure(i % 3, weight=1)
            ttk.Label(box, text=label).pack(anchor='w', pady=(0, 5))
            if key == 'coefficient':
                entry = ttk.Combobox(box, textvariable=self.calc_vars[key], values=['Masculino (+5)', 'Feminino (−161)'], state='readonly')
            else:
                entry = ttk.Entry(box, textvariable=self.calc_vars[key])
            entry.pack(fill='x')
        ttk.Label(self.content, text='Peso, altura e idade usam os registros disponíveis como ponto de partida. Escolha o coeficiente e o fator de atividade.\nReferência de atividade: valores típicos de 1,4 (sedentário) a 2,5 (muito ativo); o fator não é medido pelo aplicativo. Déficit 0% = manutenção.', style='Muted.TLabel', wraplength=950).pack(anchor='w', pady=(0, 12))
        actions = ttk.Frame(self.content)
        actions.pack(fill='x')
        ttk.Button(actions, text='Calcular cenário', style='Accent.TButton', command=self.calculate_energy).pack(side='left')
        ttk.Button(actions, text='Salvar simulação', command=lambda: self.calculate_energy(True)).pack(side='left', padx=8)
        ttk.Button(actions, text='Carregar última simulação', command=self.load_energy).pack(side='left')
        self.calc_output = ttk.Frame(self.content, padding=(0, 18))
        self.calc_output.pack(fill='x')
        ttk.Label(self.calc_output, text='Preencha os parâmetros e clique em Calcular cenário.', style='Muted.TLabel').pack(anchor='w')
        ttk.Label(self.content, text='Método: Mifflin–St Jeor estima gasto energético de repouso (GER), usado aqui como aproximação do metabolismo basal.\nGER = 10 × kg + 6,25 × cm − 5 × idade + coeficiente. Gasto diário = GER × fator. Ingestão simulada = gasto diário − déficit.\nO fator já inclui atividade: não somamos novamente as calorias dos treinos. Esta simulação para adultos não se aplica à gestação ou amamentação e não é prescrição nem previsão de perda de peso.', wraplength=950, style='Muted.TLabel').pack(anchor='w', pady=12)
        links = ttk.Frame(self.content)
        links.pack(fill='x')
        ttk.Button(links, text='Fonte: Mifflin–St Jeor', command=lambda: webbrowser.open(FORMULA_SOURCE)).pack(side='left')
        ttk.Button(links, text='Referência: NIDDK', command=lambda: webbrowser.open(ACTIVITY_SOURCE)).pack(side='left', padx=8)

    def invalidate_calculation(self):
        if hasattr(self, 'calc_output') and self.calc_output.winfo_exists():
            for widget in self.calc_output.winfo_children():
                widget.destroy()
            ttk.Label(self.calc_output, text='Parâmetros alterados. Clique em Calcular cenário para atualizar.', style='Muted.TLabel').pack(anchor='w')

    def calculate_energy(self, save=False):
        data = {key: value.get() for key, value in self.calc_vars.items()}
        try:
            result = energy_estimate(*(data[k] for k in ('weight_kg', 'height_cm', 'age_years', 'coefficient', 'activity_factor', 'deficit_pct')))
        except ValueError as exc:
            self.invalidate_calculation()
            messagebox.showerror('Confira os parâmetros', str(exc), parent=self)
            return None
        for widget in self.calc_output.winfo_children():
            widget.destroy()
        cards = ttk.Frame(self.calc_output)
        cards.pack(fill='x')
        self.card(cards, 0, 'REPOUSO ESTIMADO', f"{result['resting_kcal']:.0f} kcal", 'GER · aproximação do metabolismo basal')
        self.card(cards, 1, 'GASTO DIÁRIO ESTIMADO', f"{result['total_kcal']:.0f} kcal", 'Inclui o fator de atividade escolhido')
        self.card(cards, 2, 'INGESTÃO SIMULADA', f"{result['intake_kcal']:.0f} kcal", f"Déficit: {result['deficit_kcal']:.0f} kcal ({result['deficit_pct']:g}%)")
        ttk.Label(self.calc_output, text='Resultado estimado. Não constitui uma meta alimentar validada para você.', style='Muted.TLabel').pack(anchor='w', pady=10)
        if save:
            self.store.save('energy', data | {'date': self.day.get()})
            self.set_status('Simulação e parâmetros salvos em Saúde › Simulações.')
        return result

    def load_energy(self):
        rows = [r for r in self.store.rows('energy') if r['date'] <= self.day.get()]
        if not rows:
            messagebox.showinfo('Sem simulação', 'Não há simulação salva até esta data.', parent=self)
            return
        for key, var in self.calc_vars.items():
            value = rows[0][key]
            var.set(num(value) if isinstance(value, (int, float)) else str(value))
        self.calculate_energy()
        self.set_status(f"Parâmetros carregados da simulação de {brday(rows[0]['date'])}.")
