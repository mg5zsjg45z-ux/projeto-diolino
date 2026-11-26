from surface_ui import card_body
"""Native Windows companion to the mobile planning views."""
import tkinter as tk
from tkinter import ttk, messagebox
from productivity_metrics import eisenhower
from planning import list_plans, create_plan, check_step, TEMPLATES, move_step
from theme import SURFACE, LINE
from desktop_details import ShadowTitle


class PlanningViews:
    def render_planning(self):
        ShadowTitle(self.content, 'Planos e etapas').pack(fill='x')
        ttk.Label(self.content, text='Organize objetivos em etapas. Checar uma etapa não confirma os pilares diários.',
                  style='Muted.TLabel', wraplength=900).pack(anchor='w', pady=(8, 18))
        row = ttk.Frame(self.content)
        row.pack(fill='x', pady=(0, 16))
        ttk.Button(row, text='+ Novo plano', style='Accent.TButton', command=self.new_plan).pack(side='left')
        ttk.Button(row, text='Editar planos', command=lambda: self.navigate('plans')).pack(side='left', padx=8)
        ttk.Button(row, text='Todas as etapas', command=lambda: self.navigate('plan_steps')).pack(side='left')
        ttk.Button(row, text='Kanban', command=self.show_task_board).pack(side='left', padx=8)
        ttk.Button(row, text='Eisenhower', command=lambda: self.show_task_board(True)).pack(side='left')
        ttk.Button(row, text='Semana visual', command=self.show_week_planner).pack(side='left', padx=8)
        plans = [p for p in list_plans(self.store, self.day.get()) if p['status'] != 'Arquivado']
        if not plans:
            ttk.Label(self.content, text='Nenhum plano ativo cadastrado.',
                      font=('Georgia', 18), wraplength=900).pack(anchor='w', pady=20)
            ttk.Label(self.content, text='Crie seu primeiro plano ou escolha um modelo na janela Novo plano.', style='Muted.TLabel').pack(anchor='w')
        for plan in plans:
            card = card_body(self.content, padding=24)
            card.master.pack(fill='x', pady=(0, 12))
            ttk.Label(card, text=plan['title'], font=('Georgia', 20), style='Surface.TLabel').pack(anchor='w')
            ttk.Label(card, text=f"{plan['area']} · {plan['status']} · {plan['done']}/{plan['total']} etapas · {plan['progress']}%",
                      style='SurfaceMuted.TLabel').pack(anchor='w', pady=6)
            ttk.Progressbar(card, maximum=100, value=plan['progress']).pack(fill='x', pady=(0, 10))
            if plan['objective']:
                ttk.Label(card, text=plan['objective'], wraplength=900, style='Surface.TLabel').pack(anchor='w', pady=5)
            for step in plan['steps']:
                line = ttk.Frame(card, style='Surface.TFrame')
                line.pack(fill='x', pady=4)
                var = tk.BooleanVar(value=step['state'] == 'Concluído')
                text = step['title'] + (f" · prazo {step['due_date']}" if step['due_date'] else '')
                ttk.Checkbutton(line, text=text, variable=var, style='Surface.TCheckbutton',
                    command=lambda rid=step['id'], value=var: self.check_plan_step(rid, value.get())).pack(side='left')
            actions = ttk.Frame(card, style='Surface.TFrame')
            actions.pack(fill='x', pady=(12, 0))
            ttk.Button(actions, text='+ Adicionar etapa', command=lambda rid=plan['id']: self.open_editor('plan_steps',
                {'plan_id': rid, 'state': 'A fazer', 'priority': 'Normal'})).pack(side='left')
            ttk.Button(actions, text='Editar plano', command=lambda record=plan: self.open_editor('plans', record)).pack(side='left', padx=8)

    def show_task_board(self, matrix=False):
        day = self.day.get()
        win = tk.Toplevel(self)
        win.title('Matriz de Eisenhower' if matrix else 'Kanban')
        win.transient(self)
        win.geometry('1000x600')
        if matrix:
            ttk.Label(win, text=f'Urgente: prazo até {day}. Importante: prioridade Alta.').pack(anchor='w', padx=12)
        board = ttk.Frame(win, padding=12)
        board.pack(fill='both', expand=True)
        groups = ('fazer', 'planejar', 'delegar', 'reavaliar') if matrix else ('A fazer', 'Em andamento', 'Concluído')
        lists = {}
        for column, group in enumerate(groups):
            panel = ttk.LabelFrame(board, text=group.capitalize(), padding=6)
            panel.grid(row=0, column=column, sticky='nsew')
            board.columnconfigure(column, weight=1)
            tree = ttk.Treeview(panel, show='tree', selectmode='browse', height=12)
            tree.column('#0', width=175)
            tree.pack(fill='both', expand=True)
            lists[group] = tree
        board.rowconfigure(0, weight=1)
        drag = {'id': None, 'x': 0, 'y': 0}
        def refresh(event=None):
            totals = dict(self.store.conn.execute(
                "SELECT substr(key,12,instr(substr(key,12),':')-1), SUM(CAST(value AS REAL)) "
                "FROM preferences WHERE key GLOB 'step_focus:*' GROUP BY 1"))
            for tree in lists.values():
                tree.delete(*tree.get_children())
            for plan in list_plans(self.store, day):
                if plan['status'] != 'Ativo':
                    continue
                for step in plan['steps']:
                    group = step['state']
                    if matrix:
                        if group == 'Concluído':
                            continue
                        urgent = bool(step['due_date'] and step['due_date'] <= day)
                        group = eisenhower(urgent, step['priority'] == 'Alta')
                    minutes = totals.get(str(step['id']), 0)
                    suffix = f' · {minutes:g} min' if minutes else ''
                    lists[group].insert('', 'end', iid=str(step['id']), text=f"{plan['title']} · {step['title']}{suffix}")
        def return_to_step(event):
            refresh()
            key = str(getattr(self, 'last_focus_step', ''))
            for tree in lists.values():
                if tree.exists(key):
                    tree.selection_set(key)
                    tree.see(key)
                    if getattr(self, 'focus_origin', None) is win:
                        win.lift()
                        tree.focus_set()
        def edit(event):
            selection = event.widget.selection()
            if selection:
                record = self.store.get('plan_steps', int(selection[0]))
                if record:
                    editor = self.open_editor('plan_steps', record)
                    win.wait_window(editor)
                refresh()
        def reserve(event):
            selection = event.widget.selection()
            if selection:
                step = self.store.get('plan_steps', int(selection[0]))
                if step:
                    self.open_editor('agenda', dict(date=day, title=step['title'], category='Tarefa',
                                                    state='Pendente', reminder='Não', duration_min=25))
        def start_focus(tree, flowtime):
            selected = tree.selection()
            if not selected:
                messagebox.showinfo('Foco', 'Selecione uma etapa nesta coluna.', parent=win)
                return
            step = self.store.get('plan_steps', int(selected[0]))
            if not step:
                refresh()
                return
            self.show_pomodoro()
            timer = self.pomodoro
            if timer.state['session'] or timer.state['running'] or timer.state['phase'] != 'focus':
                messagebox.showinfo('Foco', 'Conclua a sessão ou o descanso atual antes de iniciar outra etapa.',
                                    parent=self.pomodoro_window)
                return
            plan = self.store.get('plans', step['plan_id'])
            if not plan:
                refresh()
                return
            kind = {'Medicina': 'study', 'Bíblia': 'bible'}.get(plan['area'], 'task')
            timer.configure(timer.state['focus'], timer.state['short'], timer.state['long'], flowtime)
            timer.start(kind, step['title'], study_format=self.pomo_format.get(), step_id=step['id'])
            self.focus_origin = win
            self.pomo_free.set(flowtime)
            self.pomo_topic.set(step['title'])
            self.pomo_kind.set(plan['area'])
            self.refresh_pomodoro()
        def move(rid, target):
            try:
                move_step(self.store, int(rid), target)
            except ValueError as exc:
                messagebox.showerror('Kanban', str(exc), parent=win)
            refresh()
            if lists[target].exists(rid):
                lists[target].selection_set(rid)
                lists[target].see(rid)

        def drag_start(event):
            drag.update(id=event.widget.identify_row(event.y), x=event.x_root, y=event.y_root)

        def drag_end(event):
            rid = drag.pop('id', None)
            if not rid or abs(event.x_root-drag['x'])+abs(event.y_root-drag['y']) < 8:
                return
            target = win.winfo_containing(event.x_root,event.y_root)
            while target is not None and target is not win:
                for group, tree in lists.items():
                    if target is tree or target is tree.master:
                        move(rid,group)
                        return
                target = target.master

        def move_selected(tree, target):
            selected = tree.selection()
            if selected:
                move(selected[0],target)

        win.bind('<<FocusRecorded>>', return_to_step)
        for tree in lists.values():
            controls = ttk.Frame(tree.master)
            controls.pack(fill='x')
            for label, free in [('Pomodoro', False), ('Flowtime', True)]:
                ttk.Button(controls, text=label, command=lambda t=tree, f=free: start_focus(t, f)).pack(side='left')
            if not matrix:
                movement = ttk.Frame(tree.master)
                movement.pack(fill='x',pady=(4,0))
                for target in groups:
                    if target != next(group for group,t in lists.items() if t is tree):
                        ttk.Button(movement,text=target,command=lambda t=tree,g=target:move_selected(t,g)).pack(fill='x')
                tree.bind('<ButtonPress-1>', drag_start, add='+')
                tree.bind('<ButtonRelease-1>', drag_end, add='+')
            tree.bind('<Double-1>', edit)
            tree.bind('<Return>', edit)
            tree.bind('<Control-b>', reserve)
        ttk.Label(win, text='Enter: editar · Ctrl+B: reservar horário' + ('' if matrix else ' · Arraste entre colunas ou use os botões de estado')).pack(pady=6)
        refresh()

    def show_week_planner(self):
        from week_planner_ui import show_week_planner
        show_week_planner(self)

    def check_plan_step(self, rid, checked):
        try:
            check_step(self.store, rid, checked)
            self.set_status('Etapa atualizada. Os registros da rotina permanecem independentes.')
            self.render()
        except ValueError as exc:
            messagebox.showerror('Não foi possível atualizar', str(exc), parent=self)

    def new_plan(self):
        window = tk.Toplevel(self)
        window.title('Novo plano · Diolino')
        window.geometry('680x730')
        window.transient(self)
        panel = ttk.Frame(window, padding=24)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Planejamento', font=('Georgia', 24)).pack(anchor='w')
        ttk.Label(panel, text='Modelo opcional').pack(anchor='w', pady=(14, 4))
        template = ttk.Combobox(panel, state='readonly', values=['Começar do zero'] + [t['name'] for t in TEMPLATES])
        template.current(0)
        template.pack(fill='x')
        ttk.Label(panel, text='Nome do plano').pack(anchor='w', pady=(14, 4))
        title = ttk.Entry(panel)
        title.pack(fill='x')
        ttk.Label(panel, text='Área').pack(anchor='w', pady=(14, 4))
        area = ttk.Combobox(panel, state='readonly', values=['Pessoal', 'Medicina', 'Treinos', 'Bíblia', 'Saúde', 'Outra'])
        area.set('Pessoal')
        area.pack(fill='x')
        ttk.Label(panel, text='Objetivo').pack(anchor='w', pady=(14, 4))
        objective = tk.Text(panel, height=3, wrap='word', font=('Segoe UI', 10))
        objective.pack(fill='x')
        ttk.Label(panel, text='Etapas · uma por linha').pack(anchor='w', pady=(14, 4))
        steps = tk.Text(panel, height=8, wrap='word', font=('Segoe UI', 10))
        steps.pack(fill='both', expand=True)
        def use_template(event=None):
            index = template.current() - 1
            if index < 0:
                return
            choice = TEMPLATES[index]
            title.delete(0, 'end'); title.insert(0, choice['name'])
            area.set(choice['area'])
            objective.delete('1.0', 'end'); objective.insert('1.0', choice['objective'])
            steps.delete('1.0', 'end'); steps.insert('1.0', '\n'.join(choice['steps']))
        template.bind('<<ComboboxSelected>>', use_template)
        def save():
            try:
                create_plan(self.store, {'title': title.get(), 'area': area.get(), 'status': 'Ativo', 'priority': 'Normal',
                    'objective': objective.get('1.0', 'end-1c')}, [s.strip() for s in steps.get('1.0', 'end-1c').splitlines() if s.strip()])
                window.destroy()
                self.navigate('planning')
                self.set_status('Plano criado. Ajuste prioridades e prazos em Editar planos / Todas as etapas.')
            except ValueError as exc:
                messagebox.showerror('Confira o plano', str(exc), parent=window)
        ttk.Button(panel, text='Criar plano', style='Accent.TButton', command=save).pack(anchor='e', pady=(16, 0))
