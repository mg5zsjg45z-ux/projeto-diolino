"""Native Tk dashboard: analytical charts and keyboard-accessible habit calendar."""
import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta
from charts import chart
from dashboard_data import activity_series, habit_calendar, demo_series, PERIODS
from design_system import adaptive_grid
from surface_ui import card_body
from review_cards import review_forecast
from appearance import refresh_widget

COLORS = {'study':'#7650aa','exercise':'#16805e','sleep':'#2476a5','weight':'#b45309'}
STATUS = {'done':('✓','#20734f','Cumprido'),
          'missed':('×','#b84f48','Não realizado'),
          'unknown':('?', '#68736e','Sem registro'),
          'inactive':('·','#68736e','Ainda não ativo')}

def render_dashboard(parent, store, selected_day):
    end = date.fromisoformat(selected_day)
    outer = card_body(parent,padding=16)
    outer.master.pack(fill='x',pady=(0,16))
    ttk.Label(outer,text='Sua evolução',style='Surface.TLabel',font=('Segoe UI Semibold',18)).pack(anchor='w')
    controls = ttk.Frame(outer,style='Surface.TFrame')
    controls.pack(fill='x',pady=(8,6))
    period = tk.StringVar(master=outer,value='7')
    demo = tk.BooleanVar(master=outer,value=False)
    ttk.Label(controls,text='Período',style='SurfaceMuted.TLabel').pack(side='left')
    picker = ttk.Combobox(controls,textvariable=period,values=PERIODS,state='readonly',width=5)
    picker.pack(side='left',padx=8)
    mode = ttk.Label(outer,style='SurfaceMuted.TLabel',wraplength=500)
    mode.pack(anchor='w',pady=(0,8))
    plots = ttk.Frame(outer,style='Surface.TFrame')
    plots.pack(fill='x')
    def redraw(event=None):
        for widget in plots.winfo_children():
            widget.destroy()
        # A new inner frame avoids accumulating Configure callbacks.
        grid = ttk.Frame(plots,style='Surface.TFrame')
        grid.pack(fill='x')
        count = int(period.get())
        start = end-timedelta(days=count-1)
        sample = demo.get()
        mode.configure(text='DEMONSTRAÇÃO · somente gráficos fictícios; nenhum registro salvo' if sample else
                       'Registros reais · dias sem registro não são zero')
        data = demo_series(end,count) if sample else activity_series(store,end,count)
        specs = [('study','Estudo médico','min',True),('exercise','Exercício','min',True),
                 ('sleep','Sono registrado','h',True),('weight','Peso registrado','kg',False)]
        widgets = [chart(grid,title,data[key],start,end,unit,color=COLORS[key],bars=bars,height=220)
                   for key,title,unit,bars in specs]
        adaptive_grid(grid,widgets,minimum=340,maximum=2)
        refresh_widget(grid)
    ttk.Checkbutton(controls,text='Demonstração dos gráficos',variable=demo,command=redraw).pack(side='left',padx=8)
    picker.bind('<<ComboboxSelected>>',redraw)
    redraw()
    forecast = review_forecast(store,days=7,area='Medicina')
    rows = forecast['days']
    ttk.Label(outer,text=f"FSRS · {forecast['pending']} pendente(s) agora; vencimentos futuros já agendados",
              style='Surface.TLabel',wraplength=500).pack(anchor='w',pady=(14,4))
    chart(outer,'Revisões futuras · Medicina',[(r['date'],r['count']) for r in rows],
          date.fromisoformat(rows[0]['date']),date.fromisoformat(rows[-1]['date']),
          'cartões',color='#7650aa',bars=True,height=205).pack(fill='x')
    render_habit_calendar(outer,store,end)
    return outer.master

def render_habit_calendar(parent,store,end):
    ttk.Label(parent,text='Calendário de hábitos · 30 dias',style='Surface.TLabel',
              font=('Segoe UI Semibold',13)).pack(anchor='w',pady=(16,4))
    rows = habit_calendar(store,end)
    if not rows:
        ttk.Label(parent,text='Crie um hábito em Hábitos e metas para acompanhar seu histórico.',
                  style='SurfaceMuted.TLabel',wraplength=480).pack(anchor='w')
        return
    select = ttk.Combobox(parent,values=[r['name'] for r in rows],state='readonly')
    select.pack(anchor='w',fill='x',pady=4)
    select.current(0)
    cells = ttk.Frame(parent,style='Surface.TFrame')
    cells.pack(fill='x')
    detail = ttk.Label(parent,style='SurfaceMuted.TLabel',wraplength=480)
    detail.pack(anchor='w',pady=4)
    def draw(event=None):
        for widget in cells.winfo_children():
            widget.destroy()
        for i,(day,status) in enumerate(rows[select.current()]['cells']):
            symbol,color,label = STATUS[status]
            description = f'{date.fromisoformat(day):%d/%m/%Y} · {label}'
            button = tk.Button(cells,text=f'{date.fromisoformat(day):%d/%m} {symbol}',
                               fg='#ffffff',bg=color,activebackground=color,activeforeground='#ffffff',
                               font=('Segoe UI',9),takefocus=True,relief='flat',
                               command=lambda text=description: detail.configure(text=text))
            button.grid(row=i//5,column=i%5,sticky='ew',padx=2,pady=2)
        for i in range(5):
            cells.columnconfigure(i,weight=1)
        detail.configure(text='✓ Cumprido  × Não realizado  ? Sem registro  · Ainda não ativo')
        refresh_widget(cells)
    select.bind('<<ComboboxSelected>>',draw)
    draw()
