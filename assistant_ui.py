"""Offline assistant window: editable drafts, explicit recording and save."""
from datetime import datetime
from pathlib import Path
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ai_assets import ready, install
from offline_ai import interpret, transcribe, Recorder, draft_error
from models import MODELS
from inputs import DateTimeInput


class AssistantWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title('Assistente offline · Diolino')
        self.geometry('1080x820')
        self.minsize(850, 640)
        self.queue = queue.Queue()
        self.busy = False
        self.recorder = None
        self.record_temp = None
        self.record_job = None
        self.drafts = []
        self.current = None
        self.fields = {}
        self.protocol('WM_DELETE_WINDOW', self.close)
        frame = ttk.Frame(self, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Falar ou escrever', font=('Georgia', 25)).pack(anchor='w')
        ttk.Label(frame, text='IA neste computador · Sem envio de áudio ou texto · Confira antes de salvar',
                  style='Muted.TLabel').pack(anchor='w', pady=(5, 14))
        controls = ttk.Frame(frame)
        controls.pack(fill='x')
        ttk.Label(controls, text='Data de referência').pack(side='left')
        self.reference = DateTimeInput(controls, 'date', app.day.get(), shortcuts=False)
        self.reference.pack(side='left', padx=8)
        ttk.Button(controls, text='Preparar / reparar IA offline', command=self.prepare).pack(side='right')
        self.ollama = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text='Usar Ollama (qwen2.5:7b)', variable=self.ollama).pack(side='left')
        self.text = tk.Text(frame, height=5, wrap='word', font=('Segoe UI', 11), relief='solid', borderwidth=1)
        self.text.pack(fill='x', pady=12)
        self.text.insert('1.0', '')
        actions = ttk.Frame(frame)
        actions.pack(fill='x')
        self.record_button = ttk.Button(actions, text='● Gravar áudio', command=self.toggle_record)
        self.record_button.pack(side='left')
        ttk.Button(actions, text='Importar áudio…', command=self.import_audio).pack(side='left', padx=8)
        ttk.Button(actions, text='Interpretar texto', style='Accent.TButton', command=self.analyze).pack(side='left')
        self.status = tk.StringVar(value='Pronto para uso offline.' if ready() else 'Prepare os componentes uma vez com internet (cerca de 2 GB).')
        ttk.Label(frame, textvariable=self.status, wraplength=990, style='Muted.TLabel').pack(anchor='w', pady=10)
        panes = ttk.Panedwindow(frame, orient='horizontal')
        panes.pack(fill='both', expand=True)
        left, right = ttk.Frame(panes), ttk.Frame(panes)
        panes.add(left, weight=2)
        panes.add(right, weight=3)
        ttk.Label(left, text='Registros sugeridos', font=('Segoe UI Semibold', 12)).pack(anchor='w')
        self.tree = ttk.Treeview(left, columns=('type', 'state'), show='headings', selectmode='browse', height=8)
        self.tree.heading('type', text='Registro')
        self.tree.heading('state', text='Revisão')
        self.tree.column('type', width=190)
        self.tree.column('state', width=115)
        self.tree.pack(fill='both', expand=True, pady=8)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        ttk.Button(left, text='Remover da prévia', command=self.remove).pack(anchor='w')
        canvas = tk.Canvas(right, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(fill='both', expand=True)
        self.form = ttk.Frame(canvas, padding=(16, 0, 8, 8))
        win = canvas.create_window((0, 0), window=self.form, anchor='nw')
        self.form.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(win, width=e.width))
        self.problem = tk.StringVar()
        ttk.Label(frame, textvariable=self.problem, wraplength=990).pack(anchor='w', pady=8)
        footer = ttk.Frame(frame)
        footer.pack(fill='x')
        ttk.Button(footer, text='Salvar registros revisados', style='Accent.TButton', command=self.save).pack(side='right')
        ttk.Button(footer, text='Aplicar correções à prévia', command=self.apply_fields).pack(side='right', padx=8)
        ttk.Label(footer, text='Não preenche dados ausentes por suposição.', style='Muted.TLabel').pack(side='left')
        self.poll_job = self.after(150, self.poll)

    def run(self, function, kind):
        if self.busy or self.recorder:
            return
        self.busy = True
        self.status.set('Processando neste PC… Pode levar alguns instantes.')
        def worker():
            try:
                self.queue.put((kind, function()))
            except Exception as exc:
                # Do not log audio, prompts or raw runtime response bodies.
                message = str(exc) if isinstance(exc, ValueError) else 'Não foi possível concluir. Confira os componentes offline e tente novamente.'
                self.queue.put(('error', message))
        threading.Thread(target=worker, daemon=True).start()

    def prepare(self):
        self.run(lambda: install(progress=lambda text: self.queue.put(('progress', text))), 'installed')

    def analyze(self):
        if self.busy or self.recorder:
            return
        if self.drafts and not messagebox.askyesno('Substituir prévia?', 'Gerar uma nova prévia e descartar as sugestões ainda não salvas?', parent=self):
            return
        text = self.text.get('1.0', 'end-1c')
        reference = self.reference.get()
        try:
            datetime.strptime(reference, '%Y-%m-%d')
        except ValueError:
            self.status.set('Informe uma data de referência válida.')
            return
        workouts = [{k: r[k] for k in ('id', 'date', 'name')} for r in self.app.store.rows('workout')[:30]]
        use_ollama = self.ollama.get()
        self.run(lambda: interpret(text, reference, workouts, ollama=use_ollama), 'drafts')

    def import_audio(self):
        if self.busy or self.recorder:
            return
        path = filedialog.askopenfilename(parent=self, title='Áudio com menos de 5 minutos',
                    filetypes=[('Áudio', '*.wav *.mp3 *.m4a *.ogg *.opus *.flac *.aac'), ('Todos', '*.*')])
        if path:
            self.run(lambda: transcribe(path), 'transcription')

    def toggle_record(self):
        if self.busy:
            return
        if self.recorder:
            if self.record_job:
                self.after_cancel(self.record_job)
                self.record_job = None
            path = Path(self.record_temp.name) / 'recording.wav'
            self.recorder.stop(path)
            self.recorder = None
            self.record_button.configure(text='● Gravar áudio')
            temp = self.record_temp
            self.record_temp = None
            def recognize():
                try:
                    return transcribe(path)
                finally:
                    temp.cleanup()
            self.run(recognize, 'transcription')
            return
        if not ready():
            self.status.set('Prepare os componentes offline antes de gravar.')
            return
        try:
            self.record_temp = tempfile.TemporaryDirectory(prefix='diolino-mic-')
            self.recorder = Recorder()
            self.recorder.start()
        except Exception:
            if self.recorder:
                self.recorder.stop()
            self.recorder = None
            if self.record_temp:
                self.record_temp.cleanup()
                self.record_temp = None
            self.status.set('Não foi possível abrir o microfone. Confira o dispositivo e a permissão de microfone do Windows.')
            return
        self.record_button.configure(text='■ Parar e transcrever')
        self.status.set('Gravando pelo microfone. Clique em Parar. Limite de 2 minutos.')
        self.record_job = self.after(120000, self.toggle_record)

    def poll(self):
        if self.poll_job:
            self.after_cancel(self.poll_job)
            self.poll_job = None
        try:
            while True:
                kind, value = self.queue.get_nowait()
                if kind == 'progress':
                    self.status.set(value)
                    continue
                self.busy = False
                if kind == 'error':
                    self.status.set(value)
                elif kind == 'installed':
                    self.status.set('IA offline pronta. Pode desconectar da internet para usar texto e áudio.')
                elif kind == 'transcription':
                    self.text.delete('1.0', 'end')
                    self.text.insert('1.0', value)
                    self.status.set('Transcrição concluída. Confira o texto e clique em Interpretar texto.')
                elif kind == 'drafts':
                    self.drafts, questions = value
                    self.current = None
                    self.clear_form()
                    self.refresh()
                    self.problem.set('Dúvidas: ' + ' • '.join(questions) if questions else 'Confira datas, quantidades, unidades e nomes antes de salvar.')
                    self.status.set(f'{len(self.drafts)} sugestão(ões). Nada foi gravado no banco.')
        except queue.Empty:
            pass
        self.poll_job = self.after(150, self.poll)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(self.drafts):
            error = draft_error(item)
            self.tree.insert('', 'end', iid=str(i), values=(MODELS[item['kind']][0], 'Completar' if error else 'Conferir'))

    def clear_form(self):
        for child in self.form.winfo_children():
            child.destroy()
        self.fields = {}

    def capture(self):
        if self.current is None or self.current >= len(self.drafts):
            return
        self.drafts[self.current]['values'] = {key: widget.get('1.0', 'end-1c') if isinstance(widget, tk.Text) else widget.get()
                                              for key, widget in self.fields.items()}

    def select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        index = int(selection[0])
        if index == self.current:
            return
        self.capture()
        self.current = index
        self.clear_form()
        item = self.drafts[index]
        ttk.Label(self.form, text=MODELS[item['kind']][0], font=('Georgia', 16)).pack(anchor='w')
        for field in MODELS[item['kind']][1]:
            ttk.Label(self.form, text=field.label + (' *' if field.required else '')).pack(anchor='w', pady=(8, 3))
            value = item['values'].get(field.key, '')
            if field.type in ('date', 'time', 'datetime'):
                widget = DateTimeInput(self.form, field.type, value, shortcuts=False)
            elif field.type == 'long':
                widget = tk.Text(self.form, height=3, wrap='word', font=('Segoe UI', 10))
                widget.insert('1.0', str(value))
            elif field.type == 'choice':
                widget = ttk.Combobox(self.form, values=field.choices, state='readonly')
                widget.set(str(value))
            else:
                widget = ttk.Entry(self.form)
                widget.insert(0, str(value))
            widget.pack(fill='x')
            self.fields[field.key] = widget
        self.status.set(draft_error(item) or 'Confira este registro. Campos vazios continuam sem informação.')

    def apply_fields(self):
        self.capture()
        if self.current is not None:
            self.status.set(draft_error(self.drafts[self.current]) or 'Correções aplicadas à prévia. Ainda não salvo.')
        self.current = None
        self.clear_form()
        self.refresh()

    def remove(self):
        selection = self.tree.selection()
        if selection:
            self.drafts.pop(int(selection[0]))
            self.current = None
            self.clear_form()
            self.refresh()

    def save(self):
        if self.busy or self.recorder:
            return
        self.capture()
        if not self.drafts:
            self.status.set('Não há registros para salvar.')
            return
        for index, item in enumerate(self.drafts, 1):
            error = draft_error(item)
            if error:
                self.status.set(f'Registro {index}: {error} Complete ou remova este item da prévia.')
                return
        saved = 0
        # Each confirmed record follows the normal Store validation/audit path.
        # Remove successful drafts immediately so retry cannot duplicate them.
        while self.drafts:
            item = self.drafts[0]
            try:
                self.app.store.save(item['kind'], item['values'])
            except Exception as exc:
                self.status.set(f'{saved} salvo(s). Corrija os restantes: {exc}')
                break
            self.drafts.pop(0)
            saved += 1
        else:
            self.status.set(f'{saved} registro(s) salvo(s) neste computador.')
            self.text.delete('1.0', 'end')
        self.current = None
        self.clear_form()
        self.refresh()
        self.app.sync_project()
        self.app.render()

    def close(self):
        if self.busy:
            self.status.set('Aguarde a operação terminar antes de fechar esta janela.')
            return
        if self.drafts and not messagebox.askyesno('Fechar prévia?', 'Descartar os registros sugeridos ainda não salvos?', parent=self):
            return
        if self.recorder:
            self.recorder.stop()
        if self.record_job:
            self.after_cancel(self.record_job)
        if self.record_temp:
            self.record_temp.cleanup()
        if self.poll_job:
            self.after_cancel(self.poll_job)
            self.poll_job = None
        self.destroy()


class OfflineAssistant:
    def open_assistant(self):
        window = getattr(self, 'assistant_window', None)
        if window is not None and window.winfo_exists():
            window.lift()
            return
        self.assistant_window = AssistantWindow(self)

    def render_assistant(self):
        ttk.Label(self.content, text='Assistente offline', style='Title.TLabel').pack(anchor='w')
        ttk.Label(self.content, text='Conte sua rotina por texto ou áudio. Revise os campos e salve os registros juntos.',
                  wraplength=900).pack(anchor='w', pady=16)
        ttk.Button(self.content, text='Falar ou escrever', style='Accent.TButton', command=self.open_assistant).pack(anchor='w')
        ttk.Label(self.content, text='Processamento local. Gravação somente ao clicar. Sem assinatura ou envio de dados.\n'
                  'Os componentes são baixados uma vez e ficam fora dos backups do banco.\n'
                  'Áudios importados: menos de 5 minutos. Microfone: até 2 minutos.\n'
                  'Áudio do iPhone precisa ser transferido ao PC; esta função não cria uma conexão remota.',
                  style='Muted.TLabel', wraplength=900).pack(anchor='w', pady=20)
