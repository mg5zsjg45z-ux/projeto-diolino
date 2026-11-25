"""Diolino — offline Windows desktop application."""
from offline_bible_ui import OfflineBibleViews
from desktop_workspace import WorkspaceViews, NoteEditor
from workspace_data import module_states
import argparse
import json
import logging
import os
import queue
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from tkinter import ttk, messagebox, filedialog

from models import MODELS, HELP, CHECK_GROUPS
from storage import Store, default_directory
from views import OrganizedViews
from navigation import AREAS, TABS, area_for
from inputs import DateTimeInput
from windows_support import Tray, SingleInstance
from project_sync import write_snapshot, project_directory
from theme import BG, INK, MUTED, ACCENT, NAV, SURFACE, LINE, SOFT, NAV_TEXT, TITLE_FONT, BODY_FONT, VERSION
from nutrition_ui import TacoPicker, FoodNutritionEditor
from table_layout import fit_columns, CellPreview, SHORT_LABELS
from icloud_ui import CloudIntegration
from cloud_calendar import SERIES_PREFIX
from planning_ui import PlanningViews
from desktop_details import ShadowTitle, WeekStrip
from surface_ui import card_body
from design_system import navigation_width, adaptive_grid
from visual_icons import OutlineIcon, ICONS
from engraving_ui import EngravedRule, Monogram
from appearance import AppearanceController, load_preferences, refresh_widget
from appearance_ui import AppearanceViews
from library_ui import LibraryViews
from pomodoro_ui import PomodoroViews
from manual_sync_ui import ManualSyncViews
from productivity_ui import ProductivityViews
from site_sync_ui import SiteSyncViews


def display(value):
    if value is None:
        return '—'
    if isinstance(value, float):
        return f'{value:g}'.replace('.', ',')
    return str(value)


def friendly_date(value):
    try:
        return date.fromisoformat(value).strftime('%d/%m/%Y')
    except (TypeError, ValueError):
        return str(value or '—')


class Editor(FoodNutritionEditor, tk.Toplevel):
    def __init__(self, app, kind, record=None, duplicate=False):
        super().__init__(app)
        self.app, self.kind = app, kind
        self.rid = None if duplicate else (record or {}).get('id')
        self.title(('Editar' if self.rid else 'Novo registro') + ' • ' + MODELS[kind][0])
        self.geometry('760x740')
        self.minsize(600, 480)
        self.configure(bg=BG)
        self.transient(app)
        self.grab_set()
        self.vars = {}
        self.field_widgets = {}
        self.links = {}
        header = ttk.Frame(self, padding=(24, 18))
        header.pack(fill='x')
        ttk.Label(header, text=MODELS[kind][0], style='Title.TLabel').pack(anchor='w')
        ttk.Label(header, text='* Obrigatório · Datas por dia, mês e ano · Horas no formato de 24 horas', style='Muted.TLabel').pack(anchor='w', pady=(6, 0))
        if kind in HELP:
            ttk.Label(header, text=HELP[kind], wraplength=690, style='Muted.TLabel').pack(anchor='w', pady=(10, 0))
        if kind == 'food':
            self.build_nutrition_header(header, record)
        outer = ttk.Frame(self)
        outer.pack(fill='both', expand=True)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        form = ttk.Frame(canvas, padding=(24, 8, 24, 20))
        window = canvas.create_window((0, 0), window=form, anchor='nw')
        form.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(window, width=event.width))
        # Bind only while this modal exists; never leave global handlers behind.
        self.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
        data = dict(record or {})
        if kind == 'agenda' and not record:
            data.update(category='Tarefa', state='Pendente', reminder='Sim')
        if duplicate and kind == 'sets':
            data['set_number'] = int(data.get('set_number', 0)) + 1
        for idx, field in enumerate(MODELS[kind][1]):
            ttk.Label(form, text=field.label + (' *' if field.required else '')).grid(row=idx * 2, column=0, sticky='w', pady=(10, 4))
            initial = data.get(field.key)
            if initial is None:
                if field.type == 'date' and field.key == 'date':
                    initial = app.day.get()
                elif field.type == 'choice':
                    initial = 'Não informado' if 'Não informado' in field.choices else ''
                elif field.key == 'awake_min':
                    initial = '0'
                else:
                    initial = ''
            if field.type in ('date', 'time', 'datetime'):
                widget = DateTimeInput(form, field.type, initial)
                self.vars[field.key] = widget
            elif field.type == 'long':
                widget = tk.Text(form, height=3, wrap='word', font=BODY_FONT, bg=SURFACE, fg=INK,
                                 insertbackground=INK, selectbackground=INK, selectforeground=SURFACE,
                                 relief='flat', borderwidth=0, highlightthickness=1,
                                 highlightbackground=LINE, highlightcolor=INK, padx=10, pady=8)
                widget.insert('1.0', str(initial))
                self.vars[field.key] = widget
            else:
                var = tk.StringVar(value=display(initial) if initial != '' else '')
                self.vars[field.key] = var
                if field.type == 'choice':
                    widget = ttk.Combobox(form, textvariable=var, values=field.choices, state='readonly')
                elif field.type in ('workout', 'plan'):
                    options = ({f"#{r['id']} · {r['title']}": r['id'] for r in app.store.rows('plans')}
                               if field.type == 'plan' else {f"#{r['id']} · {friendly_date(r['date'])} · {r['name']}": r['id'] for r in app.store.rows('workout')})
                    self.links[field.key] = options
                    var.set(next((label for label, rid in options.items() if rid == initial), ''))
                    widget = ttk.Combobox(form, textvariable=var, values=list(options), state='readonly')
                else:
                    widget = ttk.Entry(form, textvariable=var)
            widget.grid(row=idx * 2 + 1, column=0, sticky='ew')
            self.field_widgets[field.key] = widget
        form.columnconfigure(0, weight=1)
        if kind == 'food':
            self.finish_nutrition_form()
        footer = ttk.Frame(self, padding=18)
        footer.pack(fill='x')
        ttk.Button(footer, text='Salvar registro', style='Accent.TButton', command=self.save).pack(side='right')
        ttk.Button(footer, text='Cancelar', command=self.destroy).pack(side='right', padx=10)
        self.bind('<Escape>', lambda _: self.destroy())
        self.bind('<Control-Return>', lambda _: self.save())
        refresh_widget(self)

    def save(self):
        values = {}
        for key, widget in self.vars.items():
            values[key] = widget.get('1.0', 'end-1c') if isinstance(widget, tk.Text) else widget.get()
            if key in self.links:
                values[key] = self.links[key].get(values[key])
        try:
            self.app.store.save(self.kind, values, self.rid,
                                nutrition=self.nutrition_snapshot if self.kind == 'food' else None)
        except Exception as exc:
            messagebox.showerror('Não foi possível salvar', str(exc), parent=self)
            return
        self.app.set_status('Registro salvo neste computador.')
        self.destroy()
        self.app.render()


class App(SiteSyncViews, ProductivityViews, ManualSyncViews, PomodoroViews, OfflineBibleViews, WorkspaceViews, LibraryViews, AppearanceViews, PlanningViews, CloudIntegration, OrganizedViews, tk.Tk):
    def __init__(self, store, native=False, background=False, instance=None):
        super().__init__()
        self.option_add('*Font', BODY_FONT)
        if background:
            self.withdraw()
        self.store = store
        self.init_cloud()
        self.native = native
        self.instance = instance
        self.tray = Tray() if native else None
        self.native_job = None
        self.last_reminder_check = None
        self.last_clock_date = date.today()
        self.title('Diolino')
        available_width = max(320, self.winfo_screenwidth() - 48)
        available_height = max(320, self.winfo_screenheight() - 100)
        self.geometry(f'{min(1320, available_width)}x{min(860, available_height)}')
        self.minsize(min(1050, available_width), min(690, available_height))
        self.configure(bg=BG)
        self.page = 'home'
        self.day = tk.StringVar(value=date.today().isoformat())
        self.search = tk.StringVar()
        self.all_dates = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='Dados locais • Resumo compartilhado com este projeto')
        self.nav_buttons = {}
        self.style_ui()
        self.build_shell()
        self.bind('<Control-k>',self.show_global_search)
        self.bind('<Control-K>',self.show_global_search)
        self.appearance = AppearanceController(self, load_preferences(store.directory))
        self.appearance.configure_styles()
        self.protocol('WM_DELETE_WINDOW', self.hide_window if native else self.shutdown)
        self.report_callback_exception = self.report_error
        try:
            self.store.daily_backup()
        except Exception as exc:
            self.set_status(f'Atenção: backup automático indisponível: {exc}')
        self.render()
        self.init_pomodoro()
        self.init_site_sync()
        if native:
            self.native_job = self.after(1000, self.poll_native)
            if background and not self.tray.available:
                self.iconify()

    def style_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=BODY_FONT, background=BG, foreground=INK, troughcolor=SOFT,
                        selectbackground=INK, selectforeground=SURFACE, bordercolor=LINE,
                        lightcolor=LINE, darkcolor=LINE, focuscolor=INK)
        style.configure('TFrame', background=BG)
        style.configure('Surface.TFrame', background=SURFACE)
        style.configure('TLabel', background=BG, foreground=INK)
        style.configure('Muted.TLabel', foreground=MUTED)
        style.configure('Surface.TLabel', background=SURFACE)
        style.configure('SurfaceMuted.TLabel', background=SURFACE, foreground=MUTED)
        style.configure('Title.TLabel', font=TITLE_FONT, foreground=INK)
        style.configure('Eyebrow.TLabel', font=('Segoe UI Semibold', 9), foreground=MUTED)
        style.configure('TButton', padding=(14, 10), background=SURFACE, foreground=INK,
                        borderwidth=1, relief='flat', bordercolor=LINE, lightcolor=SURFACE, darkcolor=SURFACE)
        style.map('TButton', background=[('disabled', BG), ('pressed', '#e6e6e6'), ('active', SOFT)],
                  foreground=[('disabled', '#999999')], bordercolor=[('focus', INK), ('active', '#b8b8b8')])
        style.configure('Accent.TButton', background=ACCENT, foreground=SURFACE, bordercolor=ACCENT,
                        lightcolor=ACCENT, darkcolor=ACCENT, font=('Segoe UI Semibold', 10))
        style.map('Accent.TButton', background=[('disabled', '#dedede'), ('pressed', '#080808'), ('active', '#3c3c3c')],
                  foreground=[('disabled', MUTED), ('!disabled', SURFACE)],
                  bordercolor=[('focus', '#888888'), ('!focus', ACCENT)],
                  lightcolor=[('!disabled', ACCENT)], darkcolor=[('!disabled', ACCENT)])
        style.configure('TEntry', padding=(12, 10), fieldbackground=SURFACE, borderwidth=1,
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, insertcolor=INK)
        style.configure('TCombobox', padding=(12, 10), fieldbackground=SURFACE, background=SURFACE,
                        arrowcolor=INK, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        style.map('TCombobox', fieldbackground=[('readonly', SURFACE)], foreground=[('readonly', INK)],
                  selectbackground=[('readonly', SURFACE)], selectforeground=[('readonly', INK)])
        style.configure('TSpinbox', padding=(10, 8), fieldbackground=SURFACE, background=SURFACE, arrowcolor=INK)
        for control in ('TEntry', 'TCombobox', 'TSpinbox'):
            style.map(control, bordercolor=[('focus', INK)], lightcolor=[('focus', INK)], darkcolor=[('focus', INK)])
        style.configure('Treeview', rowheight=40, background=SURFACE, fieldbackground=SURFACE, foreground=INK,
                        borderwidth=0, font=BODY_FONT)
        style.configure('Treeview.Heading', background=SOFT, foreground=MUTED,
                        font=('Segoe UI Semibold', 10), padding=(12, 12), relief='flat')
        style.map('Treeview.Heading', background=[('active', '#e5e5e5')])
        style.map('Treeview', background=[('selected', ACCENT)], foreground=[('selected', SURFACE)])
        style.configure('TCheckbutton', background=BG, foreground=INK)
        style.map('TCheckbutton', background=[('active', BG)], indicatorbackground=[('selected', INK), ('!selected', SURFACE)],
                  indicatorforeground=[('selected', SURFACE)], indicatorbordercolor=[('!selected', '#b0b0b0')])
        style.configure('Surface.TCheckbutton', background=SURFACE)
        style.map('Surface.TCheckbutton', background=[('active', SURFACE)])
        style.configure('Horizontal.TProgressbar', background=INK, troughcolor=LINE, borderwidth=0,
                        lightcolor=INK, darkcolor=INK, thickness=5)
        for orientation in ('Vertical', 'Horizontal'):
            style.configure(f'{orientation}.TScrollbar', background='#d9d9d9', troughcolor=BG,
                            arrowcolor=MUTED, borderwidth=0, arrowsize=12, relief='flat')
            style.map(f'{orientation}.TScrollbar', background=[('active', '#bdbdbd'), ('pressed', '#a0a0a0')])
        style.configure('TSeparator', background=LINE, lightcolor=LINE, darkcolor=LINE, bordercolor=LINE)
        self.option_add('*TCombobox*Listbox.background', SURFACE)
        self.option_add('*TCombobox*Listbox.foreground', INK)
        self.option_add('*TCombobox*Listbox.selectBackground', INK)
        self.option_add('*TCombobox*Listbox.selectForeground', SURFACE)

    def build_shell(self):
        sidebar = tk.Frame(self, bg=NAV, width=232)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        self.sidebar = sidebar
        self.sidebar_hidden = False
        self.bind('<Configure>', self.resize_navigation, add='+')
        tk.Label(sidebar, text='C O N T R O L E  P E S S O A L', bg=NAV, fg=NAV_TEXT,
                 font=('Segoe UI', 8)).pack(anchor='w', padx=24, pady=(32, 8))
        Monogram(sidebar, NAV, NAV_TEXT).pack(anchor='w', padx=24, pady=(4, 8))
        tk.Label(sidebar, text='Diolino.', bg=NAV, fg=SURFACE, font=('Georgia', 28)).pack(anchor='w', padx=24)
        tk.Label(sidebar, text='Rotina · Saúde · Planejamento', bg=NAV, fg=NAV_TEXT,
                 font=('Segoe UI', 9)).pack(anchor='w', padx=24, pady=(8, 25))
        tk.Frame(sidebar, bg='#353535', height=1).pack(fill='x', padx=24, pady=(0, 20))
        # Sidebar itself scrolls on smaller displays.
        nav_canvas = tk.Canvas(sidebar, bg=NAV, highlightthickness=0)
        nav_scroll = ttk.Scrollbar(sidebar, orient='vertical', command=nav_canvas.yview)
        nav_canvas.configure(yscrollcommand=nav_scroll.set)
        nav_scroll.pack(side='right', fill='y')
        nav_canvas.pack(fill='both', expand=True)
        nav = tk.Frame(nav_canvas, bg=NAV)
        win = nav_canvas.create_window((0, 0), window=nav, anchor='nw')
        nav.bind('<Configure>', lambda _: nav_canvas.configure(scrollregion=nav_canvas.bbox('all')))
        nav_canvas.bind('<Configure>', lambda e: nav_canvas.itemconfigure(win, width=e.width))
        for key, label, glyph in AREAS:
            row = tk.Frame(nav, background=NAV)
            row.pack(fill='x', padx=12, pady=3)
            icon = OutlineIcon(row, ICONS[key], bg=NAV, fg=NAV_TEXT, padx=12)
            icon.pack(side='left')
            icon.bind('<Button-1>', lambda e, k=key: self.navigate(k))
            button = tk.Button(row, text=label, anchor='w', bg=NAV, fg=NAV_TEXT, activebackground='#333333',
                               activeforeground=SURFACE, relief='flat', borderwidth=0, highlightthickness=2, highlightcolor=SURFACE, highlightbackground=NAV,
                               cursor='hand2', font=BODY_FONT, padx=5, pady=11, command=lambda k=key: self.navigate(k))
            button.pack(side='left', fill='x', expand=True)
            self.nav_buttons[key] = (row, icon, button)
        self.nav_tail = tk.Frame(nav, bg='#353535', height=1)
        self.nav_tail.pack(fill='x', padx=24, pady=(24, 8))
        tk.Label(nav, text=f'Dados neste PC  ·  v{VERSION}', justify='left', bg=NAV, fg=NAV_TEXT,
                 font=('Segoe UI', 8), padx=24, pady=14).pack(anchor='w')
        tk.Button(nav, text='Sair completamente', command=self.shutdown, bg=NAV, fg=NAV_TEXT,
                  activebackground=NAV, activeforeground=SURFACE, relief='flat', highlightthickness=0,
                  font=('Segoe UI', 9), cursor='hand2', anchor='w', padx=24).pack(fill='x')
        main = ttk.Frame(self)
        self.main_panel = main
        main.pack(side='left', fill='both', expand=True)
        menu_row = ttk.Frame(main, padding=(12, 4))
        menu_row.pack(fill='x')
        self.menu_button = ttk.Button(menu_row, text='Ocultar menu', command=self.toggle_navigation)
        self.menu_button.pack(side='left')
        toolbar = ttk.Frame(main, padding=(32, 18))
        toolbar.pack(fill='x')
        ttk.Label(toolbar, text='Data de referência', style='Muted.TLabel').pack(side='left')
        ttk.Button(toolbar, text='‹', width=3, command=lambda: self.change_day(-1)).pack(side='left', padx=(12, 4))
        DateTimeInput(toolbar, 'date', self.day.get(), variable=self.day, shortcuts=False).pack(side='left')
        ttk.Button(toolbar, text='›', width=3, command=lambda: self.change_day(1)).pack(side='left', padx=4)
        ttk.Button(toolbar, text='Aplicar', command=self.apply_day).pack(side='left', padx=(6, 4))
        ttk.Button(toolbar, text='Hoje', command=self.today).pack(side='left')
        ttk.Button(toolbar, text='Pomodoro', command=self.show_pomodoro).pack(side='left', padx=8)
        self.clock_text=tk.StringVar()
        ttk.Label(toolbar,textvariable=self.clock_text,style='Eyebrow.TLabel').pack(side='right')
        self.clock_job=None
        self.update_brasilia_clock()
        self.bind('<Destroy>',self.cancel_brasilia_clock,add='+')
        tools = ttk.Frame(main,padding=(32,0,32,10))
        tools.pack(fill='x')
        ttk.Button(tools,text='Buscar em tudo · Ctrl+K',command=self.show_global_search).pack(side='left')
        ttk.Button(tools,text='Cartões de revisão',command=self.show_review_cards).pack(side='left',padx=8)
        ttk.Button(tools,text='PDF e OCR',command=self.show_document_tools).pack(side='left')
        ttk.Button(tools,text='Site e sincronização',command=self.show_site_sync).pack(side='left',padx=8)
        ttk.Separator(main).pack(fill='x', padx=32)
        self.week_strip = WeekStrip(main, self.day, self.apply_day)
        self.week_strip.pack(fill='x', padx=32, pady=(14, 0))
        self.content = ttk.Frame(main, padding=(32, 24, 24, 20))
        self.content.pack(fill='both', expand=True)
        ttk.Label(main, textvariable=self.status, style='Muted.TLabel', padding=(32, 10)).pack(fill='x')

    def resize_navigation(self, event):
        if event.widget is self and hasattr(self, 'sidebar'):
            width = navigation_width(event.width)
            if int(self.sidebar.cget('width')) != width:
                self.sidebar.configure(width=width)
                short = {'checklist': 'Checagem', 'notebook': 'Anotações', 'data': 'Dados', 'printing': 'Relatórios', 'appearance': 'Configurações', 'home': 'Hoje'}
                for key, label, _ in AREAS:
                    if key in self.nav_buttons:
                        self.nav_buttons[key][2].configure(text=short.get(key, label) if width < 232 else label)

    def toggle_navigation(self):
        self.sidebar_hidden = not self.sidebar_hidden
        if self.sidebar_hidden:
            self.sidebar.pack_forget()
        else:
            self.sidebar.pack(side='left', fill='y', before=self.main_panel)
        self.menu_button.configure(text='Mostrar menu' if self.sidebar_hidden else 'Ocultar menu')

    def update_brasilia_clock(self):
        self.clock_text.set(datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%H:%M:%S')+' · Brasília')
        self.clock_job=self.after(1000,self.update_brasilia_clock)

    def cancel_brasilia_clock(self,event=None):
        if (event is None or event.widget is self) and self.clock_job:
            self.after_cancel(self.clock_job);self.clock_job=None

    def set_status(self, text):
        self.status.set(text)
        self.sync_project()

    def sync_project(self):
        try:
            write_snapshot(self.store)
        except Exception:
            logging.exception('Resumo local do projeto não foi atualizado')
            self.status.set('Registro salvo. Não foi possível atualizar o resumo local para o chat.')

    def report_error(self, exc_type, exc, tb):
        logging.error('Erro de interface', exc_info=(exc_type, exc, tb))
        messagebox.showerror('Operação não concluída', f'{exc}\n\nSeus registros salvos permanecem no banco local.', parent=self)

    def valid_day(self):
        try:
            self.day.set(date.fromisoformat(self.day.get()).isoformat())
            return True
        except ValueError:
            messagebox.showerror('Data inválida', 'Use o formato AAAA-MM-DD.', parent=self)
            return False

    def apply_day(self):
        if self.valid_day():
            self.render()

    def change_day(self, amount):
        if self.valid_day():
            self.day.set((date.fromisoformat(self.day.get()) + timedelta(days=amount)).isoformat())
            self.render()

    def today(self):
        self.day.set(date.today().isoformat())
        self.render()

    def navigate(self, page):
        if not self.valid_day():
            return
        self.page = 'offline_bible' if page == 'bible_library' else page
        if page == 'agenda':
            self.all_dates.set(True)
        self.search.set('')
        self.render()

    def render(self):
        for child in self.content.winfo_children():
            child.destroy()
        area = area_for(self.page)
        if area in ('home', 'checklist', 'planning'):
            self.week_strip.pack(fill='x', padx=32, pady=(14, 0), before=self.content)
        else:
            self.week_strip.pack_forget()
        enabled = module_states(self.store)
        if not enabled.get(area, True):
            self.page = area = 'home'
        for key, widgets in self.nav_buttons.items():
            if enabled.get(key, True):
                widgets[0].pack(fill='x', padx=12, pady=3, before=self.nav_tail)
            else:
                widgets[0].pack_forget()
            color = SURFACE if key == area else NAV
            for widget in widgets:
                widget.configure(bg=color)
            widgets[1].configure(fg=INK if key == area else NAV_TEXT)
            widgets[2].configure(fg=INK if key == area else NAV_TEXT,
                                 activebackground=SOFT if key == area else '#333333',
                                 activeforeground=INK if key == area else SURFACE)
        if area in TABS:
            tabs = ttk.Frame(self.content)
            tabs.pack(fill='x', pady=(0, 18))
            buttons = [ttk.Button(tabs, text=title, style='Accent.TButton' if key == self.page else 'TButton',
                                  command=lambda p=key: self.navigate(p)) for key, title in TABS[area]]
            adaptive_grid(tabs, buttons, minimum=145, maximum=6)
        if self.page == 'home':
            self.render_scrollable(self.render_overview)
        elif self.page == 'checklist':
            self.render_scrollable(self.render_checklist)
        elif self.page == 'health_overview':
            self.render_scrollable(self.render_health_overview)
        elif self.page == 'calculator':
            self.render_scrollable(self.render_calculator)
        elif self.page == 'icloud':
            self.render_scrollable(self.render_icloud)
        elif self.page == 'planning':
            self.render_scrollable(self.render_planning)
        elif self.page in ('training', 'studies', 'adherence'):
            self.render_scrollable(lambda: self.render_activity_overview(studies=self.page == 'studies', adherence=self.page == 'adherence'))
        elif self.page == 'data':
            self.render_scrollable(self.render_data)
        elif self.page == 'notebook':
            self.render_notebook()
        elif self.page == 'modules':
            self.render_scrollable(self.render_modules)
        elif self.page == 'appearance':
            self.render_scrollable(self.render_appearance)
        elif self.page in ('bible_library', 'bible_online'):
            self.render_scrollable(self.render_bible_library)
        elif self.page == 'offline_bible':
            self.render_scrollable(self.render_offline_bible)
        elif self.page == 'printing':
            self.render_scrollable(self.render_printing)
        elif self.page == 'trends':
            self.render_scrollable(self.render_graphs)
        else:
            self.render_table()
        self.appearance.apply_tree()
        self.sync_project()

    def render_scrollable(self, render_content):
        container = self.content
        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        bar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        inner = ttk.Frame(canvas, padding=(0, 0, 8, 12))
        window = canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))
        self.content = inner
        try:
            render_content()
        finally:
            self.content = container
        def bind_scroll(widget):
            widget.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-int(e.delta / 120), 'units'))
            for child in widget.winfo_children():
                bind_scroll(child)
        bind_scroll(inner)

    def heading(self, title, subtitle):
        ttk.Label(self.content, text='DIOLINO  /  ' + dict((key, label.upper()) for key, label, _ in AREAS).get(area_for(self.page), 'SEU DIA'),
                  style='Eyebrow.TLabel').pack(anchor='w', pady=(0, 10))
        ShadowTitle(self.content, title).pack(fill='x')
        ttk.Label(self.content, text=subtitle, style='Muted.TLabel', wraplength=950).pack(anchor='w', pady=(10, 26))
        EngravedRule(self.content).pack(fill='x', pady=(0, 14))

    def card(self, parent, column, title, value, detail, command=None):
        frame = card_body(parent, padding=22)
        frame.master.grid(row=0, column=column, sticky='nsew', padx=(0 if column == 0 else 10, 0))
        parent.columnconfigure(column, weight=1, uniform='cards')
        tk.Label(frame, text=title, bg=SURFACE, fg=MUTED, font=('Segoe UI Semibold', 9)).pack(anchor='w')
        ShadowTitle(frame, value, font=('Georgia', 25), background=SURFACE).pack(fill='x', pady=(14, 12))
        tk.Frame(frame, height=1, bg=LINE).pack(fill='x', pady=(0, 12))
        detail_label = tk.Label(frame, text=detail, bg='white', fg=MUTED, justify='left', font=('Segoe UI', 9), wraplength=230)
        detail_label.configure(anchor='w')
        detail_label.pack(anchor='w', fill='x')
        frame.bind('<Configure>', lambda e: detail_label.configure(wraplength=max(100, e.width - 44)))
        if command:
            ttk.Button(frame, text='Registrar', command=command).pack(anchor='w', pady=(14, 0))


    def render_checklist(self):
        day = self.day.get()
        state = self.store.checklist(day)
        record = state['record'] or {}
        self.heading('Checagem diária', f'{friendly_date(day)} · Primeiro os três pilares; depois os hábitos de apoio.')
        self.pillar_cards()
        ttk.Label(self.content, text='Ao marcar um pilar, você confirma seu cumprimento. Seu relato tem prioridade; os detalhes registrados continuam disponíveis.', style='Muted.TLabel', wraplength=850).pack(anchor='w', pady=(0, 16))
        ttk.Label(self.content, text='Hábitos secundários', font=('Segoe UI Semibold', 15)).pack(anchor='w', pady=(0, 10))
        self.check_buttons = {}
        habits = ttk.Frame(self.content)
        habits.pack(fill='x', pady=(2, 16))
        for column, (label, keys) in enumerate(CHECK_GROUPS):
            section = card_body(habits, padding=22)
            section.master.grid(row=0, column=column, sticky='nsew', padx=(0, 8))
            habits.columnconfigure(column, weight=1, uniform='habits')
            top = ttk.Frame(section, style='Surface.TFrame')
            top.pack(fill='x', pady=(0, 12))
            ttk.Label(top, text='Medicação' if keys[0] == 'med_1' else label,
                      style='Surface.TLabel', font=('Segoe UI Semibold', 11)).pack(side='left')
            ttk.Label(top, text=f"{state['counts'][label]} / {len(keys)}", style='SurfaceMuted.TLabel').pack(side='right')
            for index, key in enumerate(keys, 1):
                var = tk.BooleanVar(value=record.get(key) == 1)
                button = ttk.Checkbutton(section, text=f'{index}ª vez', variable=var, style='Surface.TCheckbutton',
                    command=lambda k=key, v=var, d=day: self.toggle_check(d, k, v.get()))
                button.pack(anchor='w', pady=5)
                self.check_buttons[key] = (button, var)
            if keys[0] == 'med_1':
                note = ttk.Label(section, text='Conforme sua rotina prescrita. Detalhes em Medicação.',
                                 style='SurfaceMuted.TLabel', wraplength=200)
                note.pack(anchor='w', pady=(10, 0))
                section.bind('<Configure>', lambda e, widget=note: widget.configure(wraplength=max(100, e.width - 36)))
        ttk.Separator(self.content).pack(fill='x', pady=(8, 18))
        ttk.Label(self.content, text='Consumo de água', font=('Segoe UI Semibold', 13)).pack(anchor='w')
        target, consumed = state['water_target_ml'], state['water_ml']
        if target is None:
            water_text = f'{display(consumed)} mL registrados · Cadastre seu peso para calcular a meta.'
        else:
            water_text = f"{'✓ Meta registrada atingida' if state['water_complete'] else 'Em andamento'} · {display(consumed)} / {display(target)} mL"
        ttk.Label(self.content, text=water_text, font=('Segoe UI', 12)).pack(anchor='w', pady=(10, 6))
        if target is not None:
            ttk.Progressbar(self.content, maximum=target, value=min(consumed, target)).pack(fill='x', pady=(0, 8))
            weight = state['weight']
            detail = f"Meta pessoal: 50 mL/kg × {display(weight['weight_kg'])} kg = {display(target / 1000)} L/dia. Peso de {friendly_date(weight['date'])}."
        else:
            detail = 'Meta pessoal definida por você: 50 mL/kg/dia. É necessário um peso registrado até a data selecionada.'
        ttk.Label(self.content, text=detail, style='Muted.TLabel', wraplength=850).pack(anchor='w')
        buttons = ttk.Frame(self.content, padding=(0, 12))
        buttons.pack(fill='x')
        ttk.Button(buttons, text='Registrar água', command=lambda: Editor(self, 'hydration', {
            'date': day, 'drink': 'Água', 'is_water': 'Sim', 'time': datetime.now().strftime('%H:%M') if day == date.today().isoformat() else ''
        })).pack(side='left')
        ttk.Button(buttons, text='Registrar peso', command=lambda: Editor(self, 'body')).pack(side='left', padx=8)
        ttk.Button(buttons, text='Ver histórico das checagens', command=lambda: self.navigate('routine')).pack(side='left')
        ttk.Label(self.content, text='As marcações são salvas ao clicar e podem ser desmarcadas. A água é conferida automaticamente pelo volume registrado.\nUma caixa vazia significa que a checagem ainda não está confirmada.', style='Muted.TLabel', wraplength=850).pack(anchor='w', pady=(14, 0))

    def toggle_check(self, day, key, checked):
        try:
            self.store.set_check(day, key, checked)
            self.set_status(f'Checagem salva para {friendly_date(day)}.')
        except Exception as exc:
            messagebox.showerror('Não foi possível salvar a checagem', str(exc), parent=self)
        self.render()

    def render_table(self):
        kind = self.page
        if kind == 'agenda':
            self.calendar_panel()
        title, fields = MODELS[kind]
        if kind == 'agenda':
            ttk.Label(self.content, text='Compromissos', font=('Segoe UI Semibold', 14)).pack(anchor='w', pady=(0, 10))
        else:
            self.heading(title, HELP.get(kind, 'Registre, consulte e atualize suas informações. Cada alteração fica no histórico local.'))
        actions = ttk.Frame(self.content)
        actions.pack(fill='x', pady=(0, 12))
        if kind == 'food':
            ttk.Button(actions, text='+ Buscar na TACO', style='Accent.TButton', command=self.open_taco).pack(side='left')
        ttk.Button(actions, text='Novo manual' if kind == 'food' else '+ Novo registro',
                   style='TButton' if kind == 'food' else 'Accent.TButton', command=lambda: Editor(self, kind)).pack(side='left', padx=(8 if kind == 'food' else 0, 0))
        ttk.Button(actions, text='Editar', command=self.edit_selected).pack(side='left', padx=(8, 0))
        ttk.Button(actions, text='Duplicar', command=lambda: self.edit_selected(True)).pack(side='left', padx=(8, 0))
        ttk.Button(actions, text='Excluir', command=self.delete_selected).pack(side='left', padx=(8, 0))
        ttk.Button(actions, text='Histórico', command=self.show_history).pack(side='left', padx=(8, 0))
        filters = ttk.Frame(self.content)
        filters.pack(fill='x', pady=(0, 12))
        ttk.Label(filters, text='Buscar').pack(side='left')
        entry = ttk.Entry(filters, textvariable=self.search, width=28)
        entry.pack(side='left', padx=8)
        entry.bind('<KeyRelease>', lambda _: self.fill_table())
        ttk.Checkbutton(filters, text='Todas as datas', variable=self.all_dates, command=self.fill_table).pack(side='left')
        self.count_label = ttk.Label(filters, text='', style='Muted.TLabel')
        self.count_label.pack(side='right')
        container = ttk.Frame(self.content)
        container.pack(fill='both', expand=True)
        columns = ['id'] + [f.key for f in fields]
        self.tree = ttk.Treeview(container, columns=columns, show='headings', selectmode='browse')
        self.tree.heading('id', text='ID')
        self.tree.column('id', width=55, minwidth=55, stretch=False)
        for field in fields:
            self.tree.heading(field.key, text=SHORT_LABELS.get(field.key, field.label) if kind == 'food' else field.label)
            self.tree.column(field.key, width=180 if field.type in ('text', 'long') else 140, minwidth=80, stretch=False)
        vertical = ttk.Scrollbar(container, orient='vertical', command=self.tree.yview)
        horizontal = ttk.Scrollbar(container, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.tree.bind('<Double-1>', lambda _: self.edit_selected())
        self.tree.bind('<Configure>', lambda e, tree=self.tree, specs=fields: fit_columns(tree, specs))
        self.tree.cell_preview = CellPreview(self.tree)
        self.fill_table()

    def open_taco(self):
        def selected(snapshot, grams):
            editor = Editor(self, 'food')
            editor.apply_taco(snapshot, grams)
        TacoPicker(self, selected)

    def fill_table(self):
        self.tree.delete(*self.tree.get_children())
        rows = self.store.rows(self.page, None if self.all_dates.get() else self.day.get())
        if self.page == 'agenda':
            rows.sort(key=lambda row: (row['state'] != 'Pendente', row['date'], row['time'] or '23:59', row['id']))
        needle = self.search.get().casefold().strip()
        rows = [r for r in rows if not needle or needle in ' '.join(display(v) for v in r.values()).casefold()]
        for row in rows:
            values = [row['id']] + [(friendly_date(row.get(f.key)) if f.type == 'date' and row.get(f.key) else
                      datetime.fromisoformat(row[f.key]).strftime('%d/%m/%Y %H:%M') if f.type == 'datetime' and row.get(f.key) else
                      display(row.get(f.key)).replace('\n', ' / ')) for f in MODELS[self.page][1]]
            self.tree.insert('', 'end', iid=str(row['id']), values=values)
        self.count_label.configure(text=f'{len(rows)} registro(s)')
        fit_columns(self.tree, MODELS[self.page][1])

    def selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo('Selecione um registro', 'Clique em uma linha da tabela primeiro.', parent=self)
            return None
        return self.store.get(self.page, int(selection[0]))

    def edit_selected(self, duplicate=False):
        record = self.selected()
        if record:
            if not duplicate and self.recurring_readonly(record):
                return
            Editor(self, self.page, record, duplicate)

    def recurring_readonly(self, record):
        if self.page == 'agenda' and self.store.conn.execute(
                'SELECT 1 FROM calendar_links WHERE agenda_id=? AND uid LIKE ?',
                (record['id'], SERIES_PREFIX + '%')).fetchone():
            messagebox.showinfo('Evento recorrente do iCloud',
                                'Edite ou exclua esta ocorrência no Calendário da Apple. O Diolino receberá a alteração na próxima sincronização.', parent=self)
            return True
        return False

    def delete_selected(self):
        record = self.selected()
        if record and self.recurring_readonly(record):
            return
        if record and messagebox.askyesno('Excluir registro', 'Excluir este registro da lista ativa? A versão anterior será preservada no histórico e na exportação.', parent=self):
            try:
                self.store.delete(self.page, record['id'])
                self.render()
                self.set_status('Registro excluído da lista ativa. Histórico preservado.')
            except ValueError as exc:
                messagebox.showerror('Não foi possível excluir', str(exc), parent=self)

    def show_history(self):
        record = self.selected()
        if not record:
            return
        window = tk.Toplevel(self)
        window.title(f"Histórico • Registro #{record['id']}")
        window.geometry('800x600')
        text = tk.Text(window, wrap='word', font=('Consolas', 10), padx=16, pady=16)
        text.pack(fill='both', expand=True)
        for row in self.store.history(self.page, record['id']):
            text.insert('end', f"{row['timestamp']} — {row['action']}\n")
            for label, key in [('Antes', 'before_json'), ('Depois', 'after_json')]:
                text.insert('end', label + ':\n' + json.dumps(json.loads(row[key]), ensure_ascii=False, indent=2) + '\n')
            text.insert('end', '\n' + '─' * 65 + '\n\n')
        text.configure(state='disabled')


    def render_data(self):
        self.heading('Seus dados, neste computador', 'Backup automático diário ao abrir. Crie uma cópia externa para se proteger também contra falha do computador.')
        ttk.Label(self.content, text='Banco de dados', font=('Segoe UI Semibold', 12)).pack(anchor='w')
        path_box = ttk.Entry(self.content)
        path_box.insert(0, str(self.store.path))
        path_box.configure(state='readonly')
        path_box.pack(fill='x', pady=(8, 18))
        for label, detail, command in [
            ('Abrir pasta dos dados', 'Banco SQLite, backups e arquivo de diagnóstico.', lambda: os.startfile(self.store.directory)),
            ('Criar backup…', 'Escolha onde salvar uma cópia completa e restaurável.', self.backup),
            ('Exportar todos os dados…', 'Arquivo ZIP com tabelas CSV, registros excluídos e histórico de alterações.', self.export),
            ('Restaurar backup…', 'Substitui os dados atuais por uma cópia anterior. Uma cópia de segurança é criada antes.', self.restore),
            ('Criar backup protegido…', 'Backup SQLite criptografado por senha, para guardar ou levar a outro PC.', self.export_protected_backup),
            ('Restaurar backup protegido…', 'Abre arquivo .diolinobak com sua senha, valida e cria uma cópia anterior.', self.import_protected_backup),
            ('Conectar site pela internet', 'Troca automática com a conta privada, inclusive em outro PC. Autorizações revogáveis.', self.show_site_sync),
            ('Exportar troca com o site…', 'JSON para importar no site, inclusive quando a conta já tem registros.', self.export_manual_sync),
            ('Importar troca do site…', 'Prévia das diferenças e escolha das versões. Cria backup antes de aplicar.', self.import_manual_sync),
        ]:
            frame = ttk.Frame(self.content, padding=(0, 10))
            frame.pack(fill='x')
            ttk.Button(frame, text=label, width=28, command=command).pack(side='left')
            ttk.Label(frame, text=detail, style='Muted.TLabel', wraplength=560).pack(side='left', padx=18)
        ttk.Label(self.content, text='Privacidade', font=('Segoe UI Semibold', 12)).pack(anchor='w', pady=(28, 8))
        ttk.Label(self.content, text='O uso local funciona offline. A conexão opcional com o iCloud envia somente a Agenda ao calendário escolhido, após sua autenticação. A senha dessa conexão é protegida pela sua conta do Windows. O banco, os backups e o resumo para o chat não têm criptografia própria. O resumo local pode ser lido pelo assistente neste projeto.', wraplength=900, style='Muted.TLabel').pack(anchor='w')
        ttk.Label(self.content, text='Integração com este projeto no chat', font=('Segoe UI Semibold', 12)).pack(anchor='w', pady=(24, 8))
        ttk.Label(self.content, text='O arquivo Resumo-para-o-chat.md nesta pasta é atualizado ao salvar e abrir o aplicativo. Inclui 7 dias de totais e títulos da agenda; não inclui doses, diagnósticos, exames ou notas privadas. O chat pode consultar esse arquivo quando solicitado; ele não recebe mensagens automáticas do aplicativo.', wraplength=900, style='Muted.TLabel').pack(anchor='w')
        ttk.Button(self.content, text='Atualizar resumo para o chat', command=lambda: self.set_status('Resumo local atualizado para este projeto.')).pack(anchor='w', pady=10)
        ttk.Label(self.content, text=f'Diolino · versão {VERSION}', style='Muted.TLabel').pack(anchor='w', pady=(16, 0))

    def backup(self):
        path = filedialog.asksaveasfilename(parent=self, title='Salvar backup', defaultextension='.sqlite3', initialfile=f'diolino-backup-{date.today()}.sqlite3', filetypes=[('Banco SQLite', '*.sqlite3')])
        if path:
            result = self.store.backup(path)
            messagebox.showinfo('Backup criado', str(result), parent=self)

    def export(self):
        path = filedialog.asksaveasfilename(parent=self, title='Exportar registros', defaultextension='.zip', initialfile=f'diolino-exportacao-{date.today()}.zip', filetypes=[('ZIP', '*.zip')])
        if path:
            self.store.export(path)
            messagebox.showinfo('Exportação concluída', str(path), parent=self)

    def restore(self):
        if getattr(self, 'site_sync_busy', False):
            self.site_sync_status.set('Aguarde a sincronização antes de restaurar um backup.')
            self.show_site_sync()
            return
        for window in list(self.winfo_children()):
            if isinstance(window, NoteEditor):
                if not window.save():
                    return
                window.close()
        path = filedialog.askopenfilename(parent=self, title='Escolher backup', filetypes=[('Banco SQLite', '*.sqlite3')])
        if path and messagebox.askyesno('Restaurar backup', 'Os registros ativos serão substituídos pelo conteúdo deste backup. Uma cópia do estado atual será salva antes. Continuar?', parent=self):
            if not self.pause_site_for_restore():
                return
            safety = self.store.restore(path)
            messagebox.showinfo('Backup restaurado', f'Cópia anterior preservada em:\n{safety}', parent=self)
            self.render()

    def shutdown(self):
        self.site_sync_stop = True
        if getattr(self, 'site_sync_busy', False):
            self.site_sync_status.set('Concluindo a troca atual antes de encerrar o aplicativo…')
            self.after(300, self.shutdown)
            return
        for window in self.winfo_children():
            if isinstance(window, NoteEditor) and not window.save():
                return
        self.stop_pomodoro()
        if getattr(self, 'site_sync_job', None):
            self.after_cancel(self.site_sync_job)
        if self.native_job:
            self.after_cancel(self.native_job)
        if self.tray:
            self.tray.close()
        self.sync_project()
        self.store.close()
        self.destroy()

    def hide_window(self):
        if self.tray and self.tray.available:
            self.withdraw()
        else:
            self.iconify()

    def show_window(self):
        self.deiconify()
        self.lift()

    def poll_native(self):
        if self.instance and self.instance.requested():
            self.show_window()
        if self.tray:
            while True:
                try:
                    action = self.tray.events.get_nowait()
                except queue.Empty:
                    break
                if action == 'exit':
                    self.shutdown()
                    return
                self.show_window()
        now = datetime.now()
        if now.date() != self.last_clock_date:
            if self.day.get() == self.last_clock_date.isoformat():
                self.day.set(now.date().isoformat())
                self.render()
            self.last_clock_date = now.date()
        if self.last_reminder_check is None or (now - self.last_reminder_check).total_seconds() >= 20:
            self.last_reminder_check = now
            try:
                due = self.store.due_reminders(now)
                if due:
                    row = due[0]
                    detail = f"{friendly_date(row['date'])} às {row['time']} · {row['category']}"
                    accepted = self.tray.notify(row['title'], detail) if self.tray else False
                    if not accepted:
                        popup = tk.Toplevel(self)
                        popup.title('Lembrete • Diolino')
                        popup.geometry('420x190')
                        popup.attributes('-topmost', True)
                        ttk.Label(popup, text=row['title'], font=('Segoe UI Semibold', 13), wraplength=380, padding=16).pack(fill='x')
                        ttk.Label(popup, text=detail, padding=16).pack(fill='x')
                        ttk.Button(popup, text='Abrir agenda', command=lambda: (self.show_window(), self.navigate('agenda'), popup.destroy())).pack()
                    self.store.mark_notified(row, now)
            except Exception:
                logging.exception('Não foi possível processar lembrete da agenda')
        self.check_cloud_schedule()
        self.native_job = self.after(1000, self.poll_native)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, help='Diretório alternativo para testes')
    parser.add_argument('--smoke-test', action='store_true')
    parser.add_argument('--background', action='store_true', help='Iniciar minimizado na bandeja do Windows')
    args = parser.parse_args()
    directory = args.data_dir or default_directory()
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=directory / 'diagnostico.log', level=logging.ERROR, encoding='utf-8')
    instance = SingleInstance(directory) if not args.smoke_test else None
    if instance and not instance.owned:
        instance.close()
        return
    try:
        store = Store(directory)
        app = App(store, native=not args.smoke_test, background=args.background, instance=instance)
        if args.data_dir:
            app.title('Projeto Diolino — dados de teste')
        if args.smoke_test:
            app.withdraw()
            from productivity_smoke import run as smoke_tools
            smoke_tools(store)
            for page in ['home', 'checklist', 'planning', 'health_overview', 'calculator', 'icloud', 'training', 'studies', 'adherence', *MODELS, 'trends', 'data', 'appearance', 'modules', 'notebook', 'offline_bible', 'bible_online', 'bible_library', 'printing']:
                app.navigate(page)
                app.update_idletasks()
            for kind in MODELS:
                editor = Editor(app, kind)
                editor.update_idletasks()
                editor.destroy()
            picker = TacoPicker(app, lambda snapshot, grams: None)
            picker.update_idletasks()
            picker.destroy()
            app.shutdown()
            return
        app.mainloop()
    except Exception as exc:
        logging.exception('Falha ao iniciar')
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('Diolino', f'Não foi possível iniciar: {exc}')
        root.destroy()
        raise
    finally:
        if instance:
            instance.close()


if __name__ == '__main__':
    main()
