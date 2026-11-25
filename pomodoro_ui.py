"""Single modeless Pomodoro window; timers live on the app, not on a page."""
import tkinter as tk
from tkinter import ttk, messagebox
from pomodoro import Pomodoro
from theme import BG
from appearance import refresh_widget


class PomodoroViews:
    def init_pomodoro(self):
        self.pomodoro = Pomodoro(self.store)
        self.pomodoro_window = None
        self.pomodoro_ticks = 0
        self.pomodoro_job = self.after(1000, self.poll_pomodoro)
        self.bind('<Destroy>', self.cancel_pomodoro_job, add='+')

    def cancel_pomodoro_job(self, event=None):
        if (event is None or event.widget is self) and self.pomodoro_job:
            self.after_cancel(self.pomodoro_job)
            self.pomodoro_job = None

    def poll_pomodoro(self):
        try:
            event = self.pomodoro.tick()
            self.pomodoro_ticks += 1
            if self.pomodoro_ticks % 10 == 0 and self.pomodoro.state['running']:
                self.pomodoro.persist()
            if event == 'finished':
                self.bell()
                text = ('Foco concluído. Abra o Pomodoro para confirmar o registro.'
                        if self.pomodoro.state['pending'] else 'Pausa concluída. O próximo foco aguarda você.')
                if self.tray:
                    self.tray.notify('Pomodoro', text)
                self.status.set(text)
                self.show_pomodoro()
            elif event == 'interrupted':
                self.status.set('Pomodoro pausado após uma interrupção. Retome quando estiver pronto.')
            self.refresh_pomodoro()
        except Exception as exc:
            self.pomodoro.state['running'] = False
            self.status.set(f'Pomodoro pausado: {exc}')
        self.pomodoro_job = self.after(1000, self.poll_pomodoro)

    def show_pomodoro(self):
        if self.pomodoro_window and self.pomodoro_window.winfo_exists():
            self.pomodoro_window.deiconify()
            self.pomodoro_window.lift()
            self.refresh_pomodoro()
            return
        win = self.pomodoro_window = tk.Toplevel(self)
        win.title('Pomodoro • Diolino')
        win.geometry('590x720')
        win.minsize(550, 690)
        win.configure(bg=BG)
        win.protocol('WM_DELETE_WINDOW', win.withdraw)
        body = ttk.Frame(win, padding=24)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Pomodoro', style='Title.TLabel').pack(anchor='w')
        ttk.Label(body, text='Foco e descanso em ciclos. Cada etapa começa quando você decidir.',
                  wraplength=520).pack(anchor='w', pady=(6, 16))
        self.pomo_phase = tk.StringVar()
        self.pomo_time = tk.StringVar()
        self.pomo_info = tk.StringVar()
        ttk.Label(body, textvariable=self.pomo_phase).pack()
        ttk.Label(body, textvariable=self.pomo_time, font=('Georgia', 48)).pack(pady=6)
        ttk.Label(body, textvariable=self.pomo_info, wraplength=510, justify='center').pack(pady=(0, 12))
        form = ttk.Frame(body)
        form.pack(fill='x')
        session = self.pomodoro.state['session'] or {}
        self.pomo_kind = tk.StringVar(value='Bíblia' if session.get('kind') == 'bible' else 'Medicina')
        self.pomo_topic = tk.StringVar(value=session.get('topic', ''))
        ttk.Label(form, text='Área').grid(row=0, column=0, sticky='w')
        area = ttk.Combobox(form, textvariable=self.pomo_kind, values=['Medicina', 'Bíblia'], state='readonly', width=15)
        area.grid(row=1, column=0, sticky='ew', padx=(0, 12))
        ttk.Label(form, text='Tema ou passagem bíblica').grid(row=0, column=1, sticky='w')
        topic = ttk.Entry(form, textvariable=self.pomo_topic)
        topic.grid(row=1, column=1, sticky='ew')
        form.columnconfigure(1, weight=1)
        self.pomo_fields = [area, topic]
        self.pomo_format = tk.StringVar(value=session.get('format', 'Leitura'))
        ttk.Label(form, text='Formato do estudo médico').grid(row=2, column=0, columnspan=2, sticky='w', pady=(10, 0))
        study_format = ttk.Combobox(form, textvariable=self.pomo_format,
                                   values=['Leitura', 'Vídeo', 'Leitura e vídeo'], state='readonly')
        study_format.grid(row=3, column=0, columnspan=2, sticky='ew')
        self.pomo_fields.append(study_format)
        settings = ttk.Frame(body)
        settings.pack(fill='x', pady=16)
        self.pomo_durations = []
        for col, (key, title) in enumerate([('focus', 'Foco (min)'), ('short', 'Pausa (min)'), ('long', 'Pausa longa (min)')]):
            ttk.Label(settings, text=title).grid(row=0, column=col, sticky='w')
            value = tk.StringVar(value=str(self.pomodoro.state[key]))
            field = ttk.Spinbox(settings, from_=1, to=180, textvariable=value, width=12)
            field.grid(row=1, column=col, sticky='ew', padx=(0, 8))
            settings.columnconfigure(col, weight=1)
            self.pomo_durations.append(value)
            self.pomo_fields.append(field)
        self.pomo_free = tk.BooleanVar(value=self.pomodoro.state['flowtime'])
        self.pomo_mode = ttk.Checkbutton(settings, text='Flowtime (encerrar foco manualmente)',
                                         variable=self.pomo_free)
        self.pomo_mode.grid(row=2, column=0, columnspan=3, sticky='w')
        actions = ttk.Frame(body)
        actions.pack(fill='x')
        self.pomo_start = ttk.Button(actions, text='Iniciar foco', style='Accent.TButton', command=lambda: self.pomo_action('start'))
        self.pomo_start.pack(side='left')
        self.pomo_pause = ttk.Button(actions, text='Pausar', command=lambda: self.pomo_action('pause'))
        self.pomo_pause.pack(side='left', padx=8)
        self.pomo_finish = ttk.Button(actions, text='Encerrar foco', command=lambda: self.pomo_action('finish'))
        self.pomo_finish.pack(side='left')
        confirmation = ttk.Frame(body)
        confirmation.pack(fill='x', pady=12)
        self.pomo_save = ttk.Button(confirmation, text='Confirmar e salvar estudo', command=lambda: self.pomo_action('save'))
        self.pomo_save.pack(side='left')
        self.pomo_discard = ttk.Button(confirmation, text='Descartar sessão', command=lambda: self.pomo_action('discard'))
        self.pomo_discard.pack(side='left', padx=8)
        self.pomo_skip = ttk.Button(body, text='Pular descanso', command=lambda: self.pomo_action('skip'))
        self.pomo_skip.pack(anchor='w')
        ttk.Label(body, text='Pausa longa a cada 4 focos completos. Descansos não contam como estudo.\n'
                  'Fechar esta janela mantém o relógio ativo. Sair do aplicativo pausa a sessão.\n'
                  'A sessão usa a data real de início, independentemente do dia consultado.',
                  style='Muted.TLabel', wraplength=520).pack(anchor='w', pady=(16, 0))
        refresh_widget(win)
        self.refresh_pomodoro()

    def refresh_pomodoro(self):
        if not self.pomodoro_window or not self.pomodoro_window.winfo_exists():
            return
        s = self.pomodoro.state
        self.pomo_phase.set({'focus': 'Foco', 'short': 'Descanso', 'long': 'Descanso longo'}[s['phase']])
        seconds = int(s['elapsed']) if s['flowtime'] and s['phase'] == 'focus' else self.pomodoro.remaining
        self.pomo_time.set(f'{seconds // 60:02d}:{seconds % 60:02d}')
        mode = 'Aguardando confirmação' if s['pending'] else 'Em andamento' if s['running'] else 'Pronto para iniciar ou retomar'
        self.pomo_info.set(f'{mode} · {s["cycles"]} foco(s) completo(s)\n'
                           f'Tempo de foco desta sessão: {s["elapsed"] / 60:.1f} min' if s['phase'] == 'focus'
                           else f'{mode} · Descanso não será registrado como estudo')
        locked = bool(s['session'] or s['elapsed'] or s['running'] or s['pending'])
        self.pomo_mode.configure(state='disabled' if locked or s['phase'] != 'focus' else 'normal')
        for index, field in enumerate(self.pomo_fields):
            field.configure(state='disabled' if locked else 'readonly' if index in (0, 2) else 'normal')
        self.pomo_start.configure(text='Retomar' if s['elapsed'] else 'Iniciar foco' if s['phase'] == 'focus' else 'Iniciar descanso',
                                  state='disabled' if s['running'] or s['pending'] else 'normal')
        self.pomo_pause.configure(state='normal' if s['running'] else 'disabled')
        self.pomo_finish.configure(state='normal' if s['phase'] == 'focus' and s['session'] and not s['pending'] else 'disabled')
        for button in (self.pomo_save, self.pomo_discard):
            button.configure(state='normal' if s['pending'] else 'disabled')
        self.pomo_skip.configure(state='normal' if s['phase'] != 'focus' else 'disabled')

    def pomo_action(self, action):
        try:
            timer = self.pomodoro
            if action == 'start':
                if not timer.state['elapsed'] and not timer.state['session']:
                    timer.configure(*(value.get() for value in self.pomo_durations), flowtime=self.pomo_free.get())
                timer.start('study' if self.pomo_kind.get() == 'Medicina' else 'bible', self.pomo_topic.get(),
                            study_format=self.pomo_format.get())
            elif action == 'pause':
                timer.pause()
            elif action == 'finish':
                timer.finish_early()
            elif action in ('save', 'discard'):
                if action == 'discard' and not messagebox.askyesno('Descartar sessão', 'Descartar este foco sem criar um registro de estudo?', parent=self.pomodoro_window):
                    return
                timer.resolve(action == 'save')
                if action == 'save':
                    self.set_status('Estudo do Pomodoro salvo. O tempo de descanso não foi incluído.')
                    self.render()
            elif action == 'skip':
                timer.skip_break()
            self.refresh_pomodoro()
        except Exception as exc:
            messagebox.showerror('Pomodoro', str(exc), parent=self.pomodoro_window)

    def stop_pomodoro(self):
        self.pomodoro.pause()
        self.cancel_pomodoro_job()
