"""Small presentation components shared by native Windows views."""
from datetime import date, timedelta
import tkinter as tk
from tkinter import ttk, font as tkfont
from theme import BG, INK, MUTED, SURFACE, SOFT, LINE, TITLE_FONT

MONTHS = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')


class ShadowTitle(tk.Canvas):
    """One-pixel light shadow under large type; body text stays crisp."""
    def __init__(self, parent, text, font=TITLE_FONT, background=BG):
        metrics = tkfont.Font(root=parent, font=font)
        super().__init__(parent, background=background, highlightthickness=0,
                         height=metrics.metrics('linespace') + 5)
        self.create_text(1, 2, text=text, anchor='nw', fill='#dededb', font=font, tags='shadow')
        self.create_text(0, 1, text=text, anchor='nw', fill=INK, font=font, tags='title')
        self.bind('<Configure>', self.wrap_title)

    def wrap_title(self, event):
        for tag in ('shadow', 'title'):
            self.itemconfigure(tag, width=max(20, event.width - 3))
        bounds = self.bbox('all')
        if bounds:
            self.configure(height=bounds[3] + 3)


class WeekStrip(ttk.Frame):
    def __init__(self, parent, variable, on_change):
        super().__init__(parent)
        self.variable, self.on_change = variable, on_change
        style = ttk.Style(self)
        style.configure('Week.TButton', font=('Segoe UI', 10), padding=(8, 9),
                        background=BG, foreground=MUTED, bordercolor=BG, relief='flat')
        style.map('Week.TButton', background=[('active', SOFT)], bordercolor=[('focus', INK)])
        style.configure('WeekSelected.TButton', font=('Segoe UI Semibold', 10), padding=(8, 9),
                        background=INK, foreground=SURFACE, bordercolor=INK, relief='flat')
        style.map('WeekSelected.TButton', background=[('active', '#333333')], foreground=[('!disabled', SURFACE)])
        heading = ttk.Frame(self)
        heading.pack(fill='x', pady=(0, 8))
        self.month_label = ttk.Label(heading, style='Muted.TLabel')
        self.month_label.pack(side='left')
        ttk.Button(heading, text='Semana ›', command=lambda: self.move_week(1)).pack(side='right')
        ttk.Button(heading, text='‹ Semana', command=lambda: self.move_week(-1)).pack(side='right', padx=(0, 6))
        self.days = ttk.Frame(self)
        self.days.pack(fill='x')
        self.buttons = []
        for index in range(7):
            button = ttk.Button(self.days, style='Week.TButton', width=5)
            button.grid(row=0, column=index, sticky='nsew', padx=(0 if index == 0 else 5, 0))
            self.days.columnconfigure(index, weight=1, uniform='weekdays')
            self.buttons.append(button)
        self.trace = variable.trace_add('write', self.refresh)
        self.refresh()

    def refresh(self, *args):
        try:
            selected = date.fromisoformat(self.variable.get())
        except ValueError:
            return
        monday = selected - timedelta(days=selected.weekday())
        sunday = monday + timedelta(days=6)
        self.month_label.configure(text=f'{MONTHS[selected.month - 1].capitalize()} de {selected.year}  ·  {monday:%d/%m} — {sunday:%d/%m}')
        for index, button in enumerate(self.buttons):
            current = monday + timedelta(days=index)
            button.configure(text=('SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB', 'DOM')[index] + '\n' + str(current.day),
                             style='WeekSelected.TButton' if current == selected else 'Week.TButton',
                             command=lambda value=current.isoformat(): self.select(value))

    def select(self, value):
        self.variable.set(value)
        self.on_change()

    def move_week(self, amount):
        try:
            current = date.fromisoformat(self.variable.get())
        except ValueError:
            return
        self.select((current + timedelta(days=7 * amount)).isoformat())

    def destroy(self):
        self.variable.trace_remove('write', self.trace)
        super().destroy()
