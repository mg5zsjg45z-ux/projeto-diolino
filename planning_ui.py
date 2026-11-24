from surface_ui import card_body
"""Native Windows companion to the mobile planning views."""
import tkinter as tk
from tkinter import ttk, messagebox
from planning import list_plans, create_plan, check_step, TEMPLATES
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
