"""Weekly agenda with editable, explicit time blocks."""
from datetime import date, timedelta
import tkinter as tk
from tkinter import ttk
from design_system import adaptive_grid
from surface_ui import card_body
from appearance import refresh_widget

WEEKDAYS = ('Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo')

def week_dates(day):
    monday = day - timedelta(days=day.weekday())
    return [monday + timedelta(days=i) for i in range(7)]

def show_week_planner(app):
    win = tk.Toplevel(app)
    win.title('Diolino · Semana visual')
    win.geometry('1000x680')
    win.transient(app)
    selected = date.fromisoformat(app.day.get())
    header = ttk.Frame(win,padding=12)
    header.pack(fill='x')
    title = ttk.Label(header,font=('Segoe UI Semibold',16))
    title.pack(side='left',fill='x',expand=True)
    shell = ttk.Frame(win)
    shell.pack(fill='both',expand=True,padx=12,pady=(0,12))
    canvas = tk.Canvas(shell,highlightthickness=0)
    scrollbar = ttk.Scrollbar(shell,orient='vertical',command=canvas.yview)
    scrollbar.pack(side='right',fill='y')
    canvas.pack(side='left',fill='both',expand=True)
    canvas.configure(yscrollcommand=scrollbar.set)
    panel = ttk.Frame(canvas)
    window = canvas.create_window((0,0),window=panel,anchor='nw')
    panel.bind('<Configure>',lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>',lambda e: canvas.itemconfigure(window,width=e.width))
    def edit(record):
        editor = app.open_editor('agenda',record)
        win.wait_window(editor)
        redraw()
    def redraw():
        for child in panel.winfo_children():
            child.destroy()
        days = week_dates(selected)
        title.configure(text=f'{days[0]:%d/%m/%Y} — {days[-1]:%d/%m/%Y}')
        grid = ttk.Frame(panel)
        grid.pack(fill='x')
        cards = []
        for day in days:
            iso = day.isoformat()
            body = card_body(grid,padding=12)
            cards.append(body.master)
            ttk.Label(body,text=f'{WEEKDAYS[day.weekday()]} · {day:%d/%m}',
                      style='Surface.TLabel',font=('Segoe UI Semibold',12)).pack(anchor='w')
            rows = sorted(app.store.rows('agenda',iso),key=lambda row:(row['time'] or '99:99',row['id']))
            if not rows:
                ttk.Label(body,text='Sem compromissos',style='SurfaceMuted.TLabel').pack(anchor='w',pady=6)
            for row in rows:
                duration = f" · {row['duration_min']} min" if row['duration_min'] else ''
                text = f"{row['time'] or 'Sem hora'}{duration}\n{row['title']} · {row['state']}"
                ttk.Button(body,text=text,command=lambda r=row:edit(r)).pack(fill='x',pady=3)
            ttk.Button(body,text='+ Reservar horário',command=lambda d=iso:edit(dict(
                       date=d,category='Tarefa',state='Pendente',reminder='Não',duration_min=25))).pack(fill='x',pady=(8,0))
        adaptive_grid(grid,cards,minimum=235,maximum=3)
        refresh_widget(panel)
    def shift(delta):
        nonlocal selected
        selected += timedelta(days=7*delta)
        redraw()
        canvas.yview_moveto(0)
    ttk.Button(header,text='‹ Semana',command=lambda:shift(-1)).pack(side='left',padx=3)
    ttk.Button(header,text='Semana ›',command=lambda:shift(1)).pack(side='left',padx=3)
    redraw()
