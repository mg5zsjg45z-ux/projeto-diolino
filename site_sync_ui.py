"""Windows controls for a per-device, revocable online connection."""
import copy
import json
import queue
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from site_sync import ConnectionVault, SiteClient, SITE_URL, SyncConflict, SyncError, synchronize, validate_connection
from storage import Store


class SiteSyncViews:
    def pause_site_for_restore(self):
        if getattr(self, 'site_sync_busy', False):
            self.site_sync_status.set('Aguarde a sincronização antes de restaurar um backup.')
            self.show_site_sync()
            return False
        if self.site_sync_config:
            self.site_sync_config['enabled'] = False
            self.site_sync_vault.save(self.site_sync_config)
        self.site_sync_pending = None
        self.site_sync_status.set('Sincronização automática pausada para restaurar o backup. Confira os dados antes de reativar.')
        return True

    def init_site_sync(self):
        self.site_sync_vault = ConnectionVault(self.store.directory)
        self.site_sync_queue = queue.Queue()
        self.site_sync_busy = False
        self.site_sync_stop = False
        self.site_sync_pending = None
        self.site_sync_next = time.monotonic()+5
        self.site_sync_failures = 0
        self.site_sync_status = tk.StringVar(value='Site não conectado. O uso offline continua disponível.')
        self.site_sync_window = None
        try:
            self.site_sync_config = self.site_sync_vault.load()
            if self.site_sync_config:
                self.site_sync_status.set('Conectado a '+self.site_sync_config.get('account', 'sua conta')+'. Aguardando sincronização.')
        except Exception:
            self.site_sync_config = {}
            self.site_sync_status.set('Não foi possível abrir a conexão protegida. Conecte novamente este PC.')
        self.site_sync_job = self.after(1000, self.poll_site_sync)

    def poll_site_sync(self):
        try:
            message = self.site_sync_queue.get_nowait()
        except queue.Empty:
            message = None
        if message:
            self.site_sync_busy = False
            self.site_sync_pending = message.get('conflict')
            if self.site_sync_pending:
                self.site_sync_status.set(f'{len(self.site_sync_pending.conflicts)} diferença(s) aguardam revisão. Nenhuma versão em conflito foi substituída.')
            elif message.get('error'):
                self.site_sync_failures += 1
                self.site_sync_status.set(message['error'])
            else:
                self.site_sync_failures = 0
                result = message['result']
                self.site_sync_status.set(time.strftime('%H:%M')+f" · Sincronizado: {result['received']} recebido(s), {result['sent']} enviado(s), {result['updated']} atualizado(s)." +
                                          (f" {result['blocked']} item(ns) bloqueado(s); exclusões não são propagadas." if result['blocked'] else ''))
                if result['backup'] or result['sent'] or result['updated']:
                    self.store.cache_epoch += 1
                    self.sync_project()
                    if not self.site_editing():
                        self.render()
            self.site_sync_next = time.monotonic()+min(900, 60*2**min(self.site_sync_failures, 4))
        if (not self.site_sync_stop and self.site_sync_config.get('enabled') and not self.site_sync_busy
                and not self.site_sync_pending and time.monotonic() >= self.site_sync_next):
            if not self.site_editing() and not getattr(self, 'cloud_busy', False):
                self.start_site_sync()
        self.site_sync_job = self.after(1000, self.poll_site_sync)

    def site_editing(self):
        return any(type(window).__name__ in ('Editor', 'NoteEditor') for window in self.winfo_children())

    def start_site_sync(self, overrides=None, expected_base=None, expected_revision=None):
        if self.site_sync_busy:
            return
        if not self.site_sync_config:
            self.show_site_sync()
            return
        if self.site_editing() or getattr(self, 'cloud_busy', False):
            self.site_sync_status.set('Feche os editores e aguarde a troca com o iCloud para sincronizar os registros.')
            return
        self.site_sync_busy = True
        self.site_sync_status.set('Conferindo e sincronizando com o site…')
        config, directory = copy.deepcopy(self.site_sync_config), self.store.directory
        def worker():
            store = None
            try:
                client = SiteClient(config)
                store = Store(directory)
                result = synchronize(store, client, config['device_id'], overrides, expected_base, expected_revision)
                self.site_sync_queue.put({'result': result})
            except SyncConflict as exc:
                self.site_sync_queue.put({'conflict': exc})
            except SyncError as exc:
                self.site_sync_queue.put({'error': str(exc)})
            except Exception:
                # Never log request bodies, credentials or remote exception details.
                self.site_sync_queue.put({'error': 'A sincronização não foi concluída. Os backups e as versões de cada lado foram preservados; tente novamente.'})
            finally:
                if store:
                    store.close()
        threading.Thread(target=worker, daemon=True).start()

    def show_site_sync(self):
        if self.site_sync_window and self.site_sync_window.winfo_exists():
            self.site_sync_window.lift()
            return
        win = tk.Toplevel(self); self.site_sync_window = win
        win.title('Site e sincronização • Diolino'); win.geometry('790x660'); win.minsize(680, 580)
        frame = ttk.Frame(win, padding=22); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Site e aplicativo Windows', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Conecte este PC uma vez. Depois, a troca funciona pela internet a cada minuto com o aplicativo aberto ou na bandeja, mesmo com o navegador fechado.', wraplength=710).pack(anchor='w', pady=12)
        ttk.Label(frame, textvariable=self.site_sync_status, wraplength=710, style='Muted.TLabel').pack(anchor='w', pady=10)
        actions = ttk.Frame(frame); actions.pack(fill='x', pady=10)
        ttk.Button(actions, text='1. Abrir site e gerar autorização', command=lambda: webbrowser.open(SITE_URL)).pack(side='left')
        ttk.Button(actions, text='2. Importar autorização…', command=self.import_site_connection).pack(side='left', padx=8)
        ttk.Label(frame, text='No site: Mais → Sincronização com o Windows → Gerar autorização. Importe o arquivo .diolinoconnect neste computador e apague a cópia baixada. Em outro PC, gere uma autorização própria.', wraplength=710).pack(anchor='w', pady=10)
        auto = tk.BooleanVar(value=bool(self.site_sync_config.get('enabled')))
        def configure_auto():
            if not self.site_sync_config:
                auto.set(False)
                self.site_sync_status.set('Importe primeiro a autorização deste computador.')
                return
            self.site_sync_config['enabled'] = auto.get()
            self.site_sync_vault.save(self.site_sync_config)
            self.site_sync_next = time.monotonic()
            self.site_sync_status.set('Troca automática ativada.' if auto.get() else 'Troca automática pausada. Uma operação já iniciada termina normalmente.')
        ttk.Checkbutton(frame, text='Sincronizar automaticamente pela internet', variable=auto, command=configure_auto).pack(anchor='w', pady=8)
        controls = ttk.Frame(frame); controls.pack(fill='x', pady=12)
        ttk.Button(controls, text='Sincronizar agora', command=self.start_site_sync).pack(side='left')
        ttk.Button(controls, text='Revisar diferenças', command=self.review_site_conflicts).pack(side='left', padx=8)
        ttk.Button(controls, text='Desconectar este PC', command=self.disconnect_site).pack(side='left')
        ttk.Label(frame, text='Inclui registros ativos de saúde, estudos, checagens, agenda, planos, etapas e anotações em texto simples. Mudanças em um lado passam automaticamente; alterações concorrentes exigem sua escolha.', wraplength=710).pack(anchor='w', pady=12)
        ttk.Label(frame, text='Não inclui cartões FSRS, anexos da Biblioteca, exclusões, formatação das notas, preferências, senhas ou um Pomodoro em andamento. Os bancos permanecem separados; a integração troca os registros compatíveis. O limite online é 1,8 MB.', wraplength=710, style='Muted.TLabel').pack(anchor='w', pady=10)
        ttk.Label(frame, text='As credenciais ficam protegidas pela conta do Windows, fora do banco e dos backups. Revogue a autorização também no site para impedir novos acessos. Sem internet, o uso local continua.', wraplength=710, style='Muted.TLabel').pack(anchor='w', pady=10)
        ttk.Button(frame, text='Fechar', command=win.destroy).pack(anchor='e', pady=12)

    def import_site_connection(self):
        if self.site_sync_busy:
            self.site_sync_status.set('Aguarde a operação atual antes de trocar a conexão.'); return
        path = filedialog.askopenfilename(parent=self.site_sync_window or self, title='Importar autorização do site', filetypes=[('Autorização Diolino', '*.diolinoconnect')])
        if not path:
            return
        try:
            if Path(path).stat().st_size > 20000:
                raise SyncError('Arquivo de autorização acima do limite.')
            config = validate_connection(json.loads(Path(path).read_text(encoding='utf-8-sig')))
            if not messagebox.askyesno('Conectar este computador', 'Conectar à conta '+config['account']+'?\n\nOs registros ativos deste PC e da conta, incluindo saúde e anotações, serão sincronizados pela internet. Diferenças dos dois lados exigirão sua revisão.', parent=self.site_sync_window or self):
                return
            config['enabled'] = True
            self.site_sync_vault.save(config)
            self.site_sync_config, self.site_sync_pending = config, None
            self.site_sync_failures = 0
            self.site_sync_status.set('Conexão protegida neste Windows. Apague o arquivo de autorização baixado após conferir a conexão.')
            if self.site_sync_window and self.site_sync_window.winfo_exists():
                self.site_sync_window.destroy()
            self.show_site_sync()
            self.start_site_sync()
        except SyncError as exc:
            messagebox.showerror('Conexão não concluída', str(exc), parent=self)
        except Exception:
            messagebox.showerror('Conexão não concluída', 'Não foi possível validar ou proteger a autorização. Gere outro arquivo no site.', parent=self)

    def disconnect_site(self):
        if self.site_sync_busy:
            self.site_sync_status.set('Aguarde a operação atual antes de desconectar.'); return
        self.site_sync_vault.disconnect()
        self.site_sync_config, self.site_sync_pending = {}, None
        self.site_sync_status.set('Desconectado neste PC. Os dados foram mantidos. Revogue também a autorização em Mais no site.')
        if self.site_sync_window and self.site_sync_window.winfo_exists():
            self.site_sync_window.destroy()
        self.show_site_sync()

    def review_site_conflicts(self):
        pending = self.site_sync_pending
        if not pending:
            self.site_sync_status.set('Não há diferenças pendentes. Use Sincronizar agora para conferir.'); return
        win = tk.Toplevel(self); win.title('Revisar diferenças do site • Diolino'); win.geometry('920x720')
        frame = ttk.Frame(win, padding=20); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Escolha a versão de cada diferença', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text='As duas versões ficam preservadas até sua escolha. Será feita nova conferência antes de aplicar e backup antes de alterar este PC.', wraplength=850).pack(anchor='w', pady=10)
        tree = ttk.Treeview(frame, columns=('kind', 'title', 'choice'), show='headings', height=6)
        for column, title, width in [('kind', 'Área', 120), ('title', 'Registro', 450), ('choice', 'Escolha', 200)]:
            tree.heading(column, text=title); tree.column(column, width=width)
        tree.pack(fill='x')
        conflicts = {item['choice_key']: item for item in pending.conflicts}; choices = {}
        for key, item in conflicts.items():
            row = item['local']; title = next((str(row[k]) for k in ('title', 'topic', 'name', 'date') if row.get(k)), key)
            tree.insert('', 'end', iid=key, values=(item['kind'], title, 'Escolha necessária'))
        text = tk.Text(frame, wrap='word', height=16); text.pack(fill='both', expand=True, pady=12)
        def details(event=None):
            if not tree.selection(): return
            item = conflicts[tree.selection()[0]]
            text.configure(state='normal'); text.delete('1.0', 'end')
            text.insert('end', 'NESTE PC\n'+json.dumps(item['local'], ensure_ascii=False, indent=2)+'\n\nNO SITE\n'+json.dumps(item['incoming'], ensure_ascii=False, indent=2)); text.configure(state='disabled')
        tree.bind('<<TreeviewSelect>>', details)
        actions = ttk.Frame(frame); actions.pack(fill='x')
        def choose(value):
            for key in tree.selection():
                choices[key] = value
                tree.set(key, 'choice', 'Usar site' if value == 'incoming' else 'Usar este PC')
            apply.configure(state='normal' if len(choices) == len(conflicts) else 'disabled')
        ttk.Button(actions, text='Usar este PC', command=lambda: choose('keep')).pack(side='left')
        ttk.Button(actions, text='Usar site', command=lambda: choose('incoming')).pack(side='left', padx=8)
        def confirm():
            if self.site_sync_busy: return
            win.destroy(); self.start_site_sync(choices, pending.base, pending.revision)
        apply = ttk.Button(actions, text='Confirmar escolhas e sincronizar', command=confirm, state='disabled'); apply.pack(side='right')
        ttk.Button(frame, text='Decidir depois', command=win.destroy).pack(anchor='e', pady=10)
        tree.selection_set(next(iter(conflicts))); details()
