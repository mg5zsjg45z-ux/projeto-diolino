import calendar
import tkinter as tk
from datetime import date
from tkinter import ttk,messagebox
from routine_planner import planner_data,shift,hours
from cloud_calendar import SERIES_PREFIX
from planning import check_step
from print_documents import build_template
from surface_ui import card_body

DAYS=['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']


class RoutinePlannerViews:
    def planner_readonly(self,row):
        if self.store.conn.execute('SELECT 1 FROM calendar_links WHERE agenda_id=? AND uid LIKE ?',
                                   (row['id'],SERIES_PREFIX+'%')).fetchone():
            messagebox.showinfo('Evento recorrente do iCloud','Edite esta ocorrência no Calendário da Apple. A alteração chegará pela integração existente.',parent=self)
            return True
        return False

    def planner_new_event(self,day=None,time=None):
        from app import Editor
        Editor(self,'agenda',dict(date=day or self.day.get(),time=time or '',category='Tarefa',
                                  state='Pendente',reminder='Sim' if time else 'Não',title=''))

    def planner_edit_event(self,rid):
        row=self.store.get('agenda',rid)
        if row and not self.planner_readonly(row):self.open_editor('agenda',row)

    def planner_toggle_event(self,rid,checked):
        row=self.store.get('agenda',rid)
        if not row:return
        if self.planner_readonly(row):self.render();return
        try:self.store.save('agenda',dict(row,state='Concluído' if checked else 'Pendente'),rid)
        except Exception as exc:messagebox.showerror('Planner',str(exc),parent=self)
        self.render()

    def planner_toggle_step(self,rid,checked):
        try:check_step(self.store,rid,checked)
        except Exception as exc:messagebox.showerror('Planner',str(exc),parent=self)
        self.render()

    def planner_item(self,parent,row,step=False,compact=False):
        line=ttk.Frame(parent);line.pack(fill='x',pady=3)
        checked=tk.BooleanVar(value=row['state']=='Concluído')
        command=(lambda:self.planner_toggle_step(row['id'],checked.get())) if step else (lambda:self.planner_toggle_event(row['id'],checked.get()))
        ttk.Checkbutton(line,variable=checked,command=command).pack(side='left',anchor='n')
        text=row['title']
        if step:text+='\n'+row['plan_title']
        elif row.get('time'):text=row['time']+' · '+text
        button=ttk.Button(line,text=text,command=(lambda:self.open_editor('plan_steps',self.store.get('plan_steps',row['id']))) if step else (lambda:self.planner_edit_event(row['id'])))
        button.pack(side='left',fill='x',expand=True)
        # Wrap long labels so the weekly grid keeps all seven days on screen.
        if len(text)>(20 if compact else 75):
            button.configure(text=text[:(55 if compact else 160)]+'…')

    def render_routine_planner(self):
        mode=getattr(self,'planner_mode','day');self.planner_mode=mode
        data=planner_data(self.store,self.day.get(),mode)
        self.heading('Planner Diário','Agenda e etapas dos planos no mesmo lugar. As marcações não confirmam os pilares.')
        controls=ttk.Frame(self.content);controls.pack(fill='x',pady=(0,10))
        def choose(value):self.planner_mode=value;self.render()
        for key,label in [('day','Diário'),('week','Semanal'),('month','Mensal')]:
            ttk.Button(controls,text=label,style='Accent.TButton' if mode==key else 'TButton',command=lambda k=key:choose(k)).pack(side='left',padx=(0,6))
        def move(amount):
            try:self.day.set(shift(self.day.get(),mode,amount));self.render()
            except ValueError as exc:messagebox.showerror('Data',str(exc),parent=self)
        ttk.Button(controls,text='‹ Anterior',command=lambda:move(-1)).pack(side='left',padx=(12,4))
        ttk.Button(controls,text='Próximo ›',command=lambda:move(1)).pack(side='left')
        ttk.Button(controls,text='Hoje',command=self.today).pack(side='left',padx=6)
        dates=data['dates']
        label=lambda day:date.fromisoformat(day).strftime('%d/%m/%Y')
        ttk.Label(self.content,text=label(dates[0])+((' a '+label(dates[-1])) if len(dates)>1 else ''),style='Muted.TLabel').pack(anchor='w')
        actions=ttk.Frame(self.content);actions.pack(fill='x',pady=12)
        ttk.Button(actions,text='+ Adicionar tarefa',style='Accent.TButton',command=self.planner_new_event).pack(side='left')
        ttk.Button(actions,text='Planos e objetivos',command=lambda:self.navigate('planning')).pack(side='left',padx=6)
        ttk.Button(actions,text='Imprimir modelo',command=lambda:self.open_print_document(build_template(self.store,{'day':'daily','week':'weekly','month':'monthly'}[mode],self.day.get(),False))).pack(side='left')
        if mode=='month':
            grid=ttk.Frame(self.content);grid.pack(fill='x')
            for col,name in enumerate(DAYS):
                ttk.Label(grid,text=name,anchor='center').grid(row=0,column=col,sticky='ew',pady=5);grid.columnconfigure(col,weight=1,uniform='month')
            selected=date.fromisoformat(self.day.get());weeks=calendar.Calendar(firstweekday=0).monthdatescalendar(selected.year,selected.month)
            def open_day(day):self.day.set(day);self.planner_mode='day';self.render()
            for week,cells in enumerate(weeks,1):
                for col,day in enumerate(cells):
                    if day.month!=selected.month:continue
                    items=[r for r in data['events'] if r['date']==day.isoformat()]+[r for r in data['steps'] if r['due_date']==day.isoformat()]
                    title=f'{day.day}'+(' · hoje' if day==date.today() else '')
                    if items:title+='\n'+str(len(items))+' item(ns)'
                    ttk.Button(grid,text=title,command=lambda d=day.isoformat():open_day(d),style='Accent.TButton' if day.isoformat()==self.day.get() else 'TButton').grid(row=week,column=col,sticky='nsew',padx=3,pady=3,ipady=12)
            ttk.Label(self.content,text='Clique em um dia para consultar os títulos, horários e etapas.',style='Muted.TLabel').pack(anchor='w',pady=10)
        else:
            full=tk.BooleanVar(value=getattr(self,'planner_full',False))
            def full_changed():self.planner_full=full.get();self.render()
            ttk.Checkbutton(self.content,text='Mostrar todas as 24 horas',variable=full,command=full_changed).pack(anchor='w',pady=(0,10))
            grid=ttk.Frame(self.content);grid.pack(fill='x')
            timed_hours=hours(data['events'],full.get())
            for column,day in enumerate(dates,1):
                grid.columnconfigure(column,weight=1,uniform='planner-days')
                ttk.Label(grid,text=DAYS[date.fromisoformat(day).weekday()]+' '+label(day)[:5],anchor='center').grid(row=0,column=column,sticky='ew',pady=5)
                untimed=ttk.Frame(grid,padding=5);untimed.grid(row=1,column=column,sticky='nsew',padx=2,pady=2)
                for row in data['events']:
                    if row['date']==day and not row['time']:self.planner_item(untimed,row,compact=mode=='week')
                for row in data['steps']:
                    if row['due_date']==day:self.planner_item(untimed,row,step=True,compact=mode=='week')
                if not untimed.winfo_children():ttk.Label(untimed,text='—',style='Muted.TLabel').pack()
                for index,hour in enumerate(timed_hours,2):
                    cell=ttk.Frame(grid,padding=4);cell.grid(row=index,column=column,sticky='nsew',padx=2,pady=2)
                    events=[row for row in data['events'] if row['date']==day and row['time'] and int(row['time'][:2])==hour]
                    for row in events:self.planner_item(cell,row,compact=mode=='week')
                    if not events:ttk.Button(cell,text='+',width=3,command=lambda d=day,h=hour:self.planner_new_event(d,f'{h:02d}:00')).pack(anchor='w')
            ttk.Label(grid,text='Sem hora / etapas',wraplength=85).grid(row=1,column=0,sticky='nw',padx=5)
            for index,hour in enumerate(timed_hours,2):ttk.Label(grid,text=f'{hour:02d}:00').grid(row=index,column=0,sticky='n',padx=5,pady=10)
            ttk.Label(self.content,text='As faixas organizam pelo horário de início; a altura não representa a duração. Horários fora de 06–22h também aparecem.',wraplength=950,style='Muted.TLabel').pack(anchor='w',pady=10)
        if data['undated']:
            ttk.Label(self.content,text='Etapas sem prazo',font=('Segoe UI Semibold',13)).pack(anchor='w',pady=(16,6))
            for row in data['undated'][:30]:self.planner_item(self.content,row,step=True)
