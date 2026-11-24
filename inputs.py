"""Structured local date/time inputs; persistence still uses ISO dates."""
import tkinter as tk
from tkinter import ttk
from datetime import datetime


class DateTimeInput(ttk.Frame):
    def __init__(self, parent, kind, value='', variable=None, shortcuts=True):
        super().__init__(parent)
        self.kind = kind
        self.parts = {}
        self.external = variable
        self.setting = False
        if kind in ('date', 'datetime'):
            for key, label, width, low, high in [('d', 'Dia', 3, 1, 31), ('m', 'Mês', 3, 1, 12), ('y', 'Ano', 5, 1900, 2200)]:
                self.add_part(key, label, width, low, high)
        if kind in ('time', 'datetime'):
            for key, label, width, low, high in [('h', 'Hora', 3, 0, 23), ('min', 'Minuto', 3, 0, 59)]:
                self.add_part(key, label, width, low, high)
        if shortcuts:
            ttk.Button(self, text='Agora' if kind != 'date' else 'Hoje', command=self.now).pack(side='left', padx=6, anchor='s')
            ttk.Button(self, text='Limpar', command=lambda: self.set('')).pack(side='left', anchor='s')
        self.set(value)
        if variable is not None:
            for var in self.parts.values():
                var.trace_add('write', self.update_external)
            self.external_trace = variable.trace_add('write', self.read_external)
            self.bind('<Destroy>', self.remove_trace)

    def remove_trace(self, event):
        if event.widget == self and self.external is not None:
            self.external.trace_remove('write', self.external_trace)

    def update_external(self, *_):
        if not self.setting:
            self.setting = True
            self.external.set(self.get())
            self.setting = False

    def read_external(self, *_):
        if not self.setting:
            self.set(self.external.get())

    def add_part(self, key, label, width, low, high):
        box = ttk.Frame(self)
        box.pack(side='left', padx=(0, 6))
        ttk.Label(box, text=label, style='Muted.TLabel').pack(anchor='w')
        var = tk.StringVar()
        self.parts[key] = var
        check = (self.register(lambda s, n=width: s == '' or (s.isdigit() and len(s) <= n)), '%P')
        ttk.Spinbox(box, from_=low, to=high, width=width, textvariable=var, format='%02.0f' if key != 'y' else '%04.0f',
                    validate='key', validatecommand=check).pack(anchor='w')

    def now(self):
        now = datetime.now()
        self.set(now.strftime('%Y-%m-%d %H:%M' if self.kind == 'datetime' else '%Y-%m-%d' if self.kind == 'date' else '%H:%M'))

    def set(self, value):
        self.setting = True
        for var in self.parts.values():
            var.set('')
        if not value:
            self.setting = False
            if self.external is not None:
                self.update_external()
            return
        value = str(value)
        if self.kind in ('date', 'datetime'):
            parts = value[:10].split('-')
            if len(parts) == 3:
                for key, part in zip(('y', 'm', 'd'), parts):
                    self.parts[key].set(part)
        if self.kind in ('time', 'datetime'):
            parts = (value[11:] if self.kind == 'datetime' else value).split(':')
            if len(parts) == 2:
                self.parts['h'].set(parts[0])
                self.parts['min'].set(parts[1])
        self.setting = False
        if self.external is not None:
            self.update_external()

    def get(self):
        if not any(var.get() for var in self.parts.values()):
            return ''
        def part(key, width=2):
            text = self.parts[key].get()
            return text.zfill(width) if text else '?'
        day = f"{part('y', 4)}-{part('m')}-{part('d')}" if self.kind != 'time' else ''
        clock = f"{part('h')}:{part('min')}" if self.kind != 'date' else ''
        return day + ' ' + clock if self.kind == 'datetime' else day or clock
