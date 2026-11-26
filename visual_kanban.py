"""Card-based Kanban, independent of the legacy accessible tree board."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from planning import list_plans, move_step
from design_system import adaptive_grid
from surface_ui import card_body
from appearance import refresh_widget
from theme import SURFACE, INK, MUTED

STATES = ('A fazer','Em andamento','Concluído')
COLORS = ('#53657b','#17685a','#20734f')

def show_visual_kanban(app):
    win = tk.Toplevel(app)
    win.title('Diolino · Kanban visual')
    win.geometry('1080x700')
    win.transient(app)
    day = app.day.get()
    header = ttk.Frame(win,padding=12)
    header.pack(fill='x')
    ttk.Label(header,text='Quadro de planejamento',font=('Segoe UI Semibold',18)).pack(side='left')
    ttk.Button(header,text='Quadro em lista',command=app.show_task_board).pack(side='right')
    ttk.Label(win,text='Arraste pelo título ou use Mover para. Enter abre a etapa.',
              style='Muted.TLabel').pack(anchor='w',padx=12)
    shell = ttk.Frame(win)
    shell.pack(fill='both',expand=True,padx=12,pady=12)
    canvas = tk.Canvas(shell,highlightthickness=0)
    scrollbar = ttk.Scrollbar(shell,orient='vertical',command=canvas.yview)
    scrollbar.pack(side='right',fill='y')
    canvas.pack(side='left',fill='both',expand=True)
    canvas.configure(yscrollcommand=scrollbar.set)
    panel = ttk.Frame(canvas)
    window = canvas.create_window((0,0),window=panel,anchor='nw')
    panel.bind('<Configure>',lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>',lambda e: canvas.itemconfigure(window,width=e.width))
    drag = {}
    zones = {}
    def move(rid,state):
        try:
            move_step(app.store,rid,state)
        except ValueError as exc:
            messagebox.showerror('Kanban',str(exc),parent=win)
        redraw()
    def press(event,rid):
        drag.update(id=rid,x=event.x_root,y=event.y_root)
    def release(event):
        rid = drag.pop('id',None)
        if rid is None or abs(event.x_root-drag['x'])+abs(event.y_root-drag['y']) < 8:
            return
        target = win.winfo_containing(event.x_root,event.y_root)
        while target is not None and target is not win:
            if target in zones:
                move(rid,zones[target])
                return
            target = target.master
    def edit(rid):
        record = app.store.get('plan_steps',rid)
        if record:
            editor = app.open_editor('plan_steps',record)
            win.wait_window(editor)
            redraw()
    def reserve(step):
        editor = app.open_editor('agenda',dict(date=day,title=step['title'],
            category='Tarefa',state='Pendente',reminder='Não',duration_min=25))
        win.wait_window(editor)
    def redraw():
        zones.clear()
        for child in panel.winfo_children():
            child.destroy()
        grid = ttk.Frame(panel)
        grid.pack(fill='x')
        grouped = {state:[] for state in STATES}
        for plan in list_plans(app.store,day):
            if plan['status'] == 'Ativo':
                for step in plan['steps']:
                    grouped[step['state']].append((plan,step))
        columns = []
        for state,color in zip(STATES,COLORS):
            column = ttk.Frame(grid,padding=4)
            columns.append(column)
            zones[column] = state
            tk.Label(column,text=f'{state}  ·  {len(grouped[state])}',bg=color,fg='#ffffff',
                     font=('Segoe UI Semibold',12),pady=8).pack(fill='x')
            if not grouped[state]:
                ttk.Label(column,text='Nenhuma etapa',style='Muted.TLabel').pack(pady=18)
            for plan,step in grouped[state]:
                rid = step['id']
                body = card_body(column,padding=12,radius=12)
                body.master.pack(fill='x',pady=5)
                tk.Label(body,text=plan['title'],fg=MUTED,bg=SURFACE,wraplength=200,
                         justify='left',anchor='w').pack(fill='x')
                title = tk.Label(body,text=step['title'],fg=INK,bg=SURFACE,wraplength=200,
                                 justify='left',anchor='w',font=('Segoe UI Semibold',12),
                                 cursor='hand2',takefocus=True,highlightthickness=1)
                title.pack(fill='x',pady=4)
                title.bind('<ButtonPress-1>',lambda e,r=rid:press(e,r))
                title.bind('<ButtonRelease-1>',release)
                title.bind('<Double-1>',lambda e,r=rid:edit(r))
                title.bind('<Return>',lambda e,r=rid:edit(r))
                due = step['due_date']
                late = bool(due and due < day and state != 'Concluído')
                ttk.Label(body,text=f"Prioridade: {step['priority']}" + (' · Prazo vencido' if late else ''),
                          style='SurfaceMuted.TLabel',wraplength=200).pack(anchor='w')
                if due:
                    ttk.Label(body,text=f'Prazo: {date.fromisoformat(due):%d/%m/%Y}',
                              style='SurfaceMuted.TLabel').pack(anchor='w')
                ttk.Button(body,text='Editar',command=lambda r=rid:edit(r)).pack(fill='x',pady=(6,2))
                ttk.Button(body,text='Reservar horário',command=lambda s=step:reserve(s)).pack(fill='x',pady=2)
                picker = ttk.Combobox(body,values=[s for s in STATES if s!=state],state='readonly')
                picker.set('Mover para…')
                picker.pack(fill='x',pady=2)
                picker.bind('<<ComboboxSelected>>',lambda e,r=rid,p=picker:move(r,p.get()))
        adaptive_grid(grid,columns,minimum=265,maximum=3)
        refresh_widget(panel)
    redraw()
