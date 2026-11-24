"""Opt-in connection workflow. Secrets are entered only in the local app."""
import copy
from datetime import datetime
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from cloud_calendar import PrivateSettings, ICloudTransport, CalendarError, sync_calendar, APPLE_HELP, connection_error_message
from storage import Store

IPHONE_GUIDE = '''Calendário iCloud e alarmes no iPhone (iOS 26.6)

1. Conexão do calendário
Na sua Conta Apple (account.apple.com), gere uma senha específica de app chamada
Projeto Diolino. Digite a Conta Apple e essa senha nos campos locais deste aplicativo.
Use Conectar e listar calendários. Selecione Projeto Diolino ou crie esse calendário
com o botão correspondente. Clique em Ativar sincronização.

No iPhone, confira se Calendários do iCloud está habilitado e se Projeto Diolino
aparece na lista do app Calendário. O aviso de evento é uma notificação de calendário.
Ele não cria automaticamente um alarme do app Relógio.

2. Alarmes do Relógio: configuração necessária no próprio iPhone
Este programa de Windows não controla diretamente o Relógio do iPhone. Prepare um
atalho pessoal chamado Alarmes Diolino no app Atalhos do iPhone:

• Buscar eventos do calendário Projeto Diolino cujo início esteja entre agora e o
  fim de hoje. Filtre para eventos com hora definida, não eventos de dia inteiro.
• Obter os alarmes existentes. Manter uma lista dos nomes para evitar duplicação.
• Repetir para cada evento: obter título e data de início. Formatar a data como
  dd/MM/yyyy HH:mm. Montar o nome “Diolino | data e hora | título”.
• Se não houver alarme com esse nome, usar a ação de criar alarme do Relógio,
  com a hora do evento, esse nome e sem repetição semanal.
• Executar uma vez e conferir os horários e o som no app Relógio.

No app Atalhos, crie uma automação pessoal por Hora do dia para executar esse
atalho diariamente, por exemplo às 00:05. Execute novamente depois de alterar
compromissos do dia. Mudanças no calendário só chegam aos alarmes quando o atalho
é executado; um alarme de horário antigo precisa ser desativado no Relógio.
Alarmes de dias anteriores com prefixo Diolino podem ser desativados manualmente.
Não remova ou altere seus alarmes pessoais de outros nomes.

O roteiro acima precisa ser criado e conferido no seu aparelho. Nenhum atalho foi
instalado no iPhone por este programa. A disposição e os nomes das ações podem
variar com o idioma do iOS. AlarmKit permite criar alarmes por um app iOS próprio,
mas não é uma conexão remota do Windows com os alarmes do app Relógio.

3. Alcance da sincronização
O PC sincroniza a Agenda em dois sentidos com o calendário escolhido, a cada
5 minutos enquanto o aplicativo estiver aberto (inclusive na bandeja).
Datas são interpretadas em America/Fortaleza. Itens sem hora viram dia inteiro;
eventos com hora e sem duração informada usam 30 minutos. O botão Notificar
adiciona um aviso de calendário no horário do evento.

Recorrências sem convidados são importadas como ocorrências para consulta, de um ano
atrás até dois anos à frente, com atualização automática do período. Edite-as na Apple.
Convites não são importados. Se um item mudar no PC e no iCloud, a sincronização para esse item até
você escolher a versão. Remoções viram cancelamentos, preservando o histórico.
Registros de saúde, alimentos, medicamentos e estudos não são sincronizados.

Referências oficiais
https://support.apple.com/pt-br/102654
https://support.apple.com/guide/shortcuts/apd932ff833f/ios
https://developer.apple.com/documentation/alarmkit
'''


class CloudIntegration:
    def init_cloud(self):
        self.cloud_vault = PrivateSettings(self.store.directory)
        self.cloud_busy = False
        self.cloud_queue = queue.Queue()
        self.cloud_last = 0
        self.cloud_choices = {}
        self.cloud_pending = None
        self.cloud_status_text = 'Não conectado. Configure sua conta para começar.'
        try:
            self.cloud_config = self.cloud_vault.load()
        except Exception:
            self.cloud_config = {}
            self.cloud_status_text = 'A conexão salva não pôde ser lida nesta conta do Windows. Conecte novamente.'

    def render_icloud(self):
        self.heading('iCloud e iPhone', 'Sua Agenda no calendário escolhido do iCloud. Configure a conexão diretamente neste computador.')
        ttk.Label(self.content, text='Apenas itens da Agenda são sincronizados. Os registros de saúde permanecem neste PC.', style='Muted.TLabel', wraplength=900).pack(anchor='w', pady=(0, 16))
        form = ttk.Frame(self.content)
        form.pack(fill='x')
        candidate = self.cloud_pending or self.cloud_config
        same_account = not self.cloud_pending or self.cloud_pending.get('username') == self.cloud_config.get('username')
        self.cloud_username = tk.StringVar(value=candidate.get('username', ''))
        self.cloud_password = tk.StringVar()
        ttk.Label(form, text='Conta Apple (e-mail)').grid(row=0, column=0, sticky='w')
        ttk.Label(form, text='Senha específica de app').grid(row=0, column=1, sticky='w', padx=(16, 0))
        ttk.Entry(form, textvariable=self.cloud_username).grid(row=1, column=0, sticky='ew', pady=(5, 14))
        ttk.Entry(form, textvariable=self.cloud_password, show='•').grid(row=1, column=1, sticky='ew', padx=(16, 0), pady=(5, 14))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        ttk.Label(self.content, text='Use a senha específica gerada na Conta Apple. A senha é protegida para sua conta do Windows e não entra nos backups ou no resumo do chat.', style='Muted.TLabel', wraplength=900).pack(anchor='w', pady=(0, 12))
        controls = ttk.Frame(self.content)
        controls.pack(fill='x', pady=(0, 18))
        ttk.Button(controls, text='Como gerar a senha ↗', command=lambda: webbrowser.open(APPLE_HELP)).pack(side='left')
        ttk.Button(controls, text='Conectar e listar calendários', style='Accent.TButton', command=lambda: self.cloud_connect('list')).pack(side='left', padx=8)
        ttk.Button(controls, text='Criar calendário Projeto Diolino', command=lambda: self.cloud_connect('create')).pack(side='left')
        ttk.Label(self.content, text='Calendário para sincronizar').pack(anchor='w')
        self.cloud_selected = tk.StringVar(value=self.cloud_config.get('calendar_name', '') if same_account else '')
        self.cloud_calendar_combo = ttk.Combobox(self.content, textvariable=self.cloud_selected, state='readonly', values=[])
        self.cloud_calendar_combo.pack(fill='x', pady=(5, 12))
        if self.cloud_config.get('calendar_url') and same_account:
            name = self.cloud_config['calendar_name']
            self.cloud_choices[name] = self.cloud_config['calendar_url']
        self.cloud_calendar_combo.configure(values=list(self.cloud_choices))
        self.cloud_auto = tk.BooleanVar(value=self.cloud_config.get('auto', True))
        ttk.Checkbutton(self.content, text='Sincronizar automaticamente a cada 5 minutos enquanto o aplicativo estiver aberto', variable=self.cloud_auto).pack(anchor='w', pady=(0, 14))
        buttons = ttk.Frame(self.content)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='Ativar sincronização', style='Accent.TButton', command=self.cloud_enable).pack(side='left')
        ttk.Button(buttons, text='Sincronizar agora', command=lambda: self.cloud_start('sync')).pack(side='left', padx=8)
        ttk.Button(buttons, text='Desconectar', command=self.cloud_disconnect).pack(side='left')
        self.cloud_status_label = ttk.Label(self.content, text=self.cloud_status_text, style='Muted.TLabel', wraplength=900)
        self.cloud_status_label.pack(anchor='w', pady=(14, 12))
        if self.cloud_config.get('last_success'):
            ttk.Label(self.content, text='Última sincronização concluída: ' + self.cloud_config['last_success'], style='Muted.TLabel').pack(anchor='w', pady=(0, 10))
        ttk.Separator(self.content).pack(fill='x', pady=(10, 18))
        ttk.Label(self.content, text='Alarme do Relógio no iPhone', font=('Georgia', 18)).pack(anchor='w')
        ttk.Label(self.content, text='O aviso do Calendário e o alarme do Relógio são recursos separados. Para o Relógio, configure o atalho pessoal no iPhone usando o roteiro abaixo.', wraplength=900, style='Muted.TLabel').pack(anchor='w', pady=(8, 12))
        ttk.Button(self.content, text='Abrir roteiro para iPhone · iOS 26.6', command=self.show_iphone_guide).pack(anchor='w')
        self.render_calendar_conflicts()

    def cloud_message(self, text):
        self.cloud_status_text = text
        widget = getattr(self, 'cloud_status_label', None)
        if widget and widget.winfo_exists():
            widget.configure(text=text)

    def cloud_connect(self, kind):
        if self.cloud_busy:
            return
        username = self.cloud_username.get().strip()
        password = self.cloud_password.get().strip()
        if not password and username == self.cloud_config.get('username'):
            password = self.cloud_config.get('password', '')
        if not username or not password:
            self.cloud_message('Informe a Conta Apple e a senha específica de app nos campos acima.')
            return
        self.cloud_password.set('')
        self.cloud_start(kind, dict(username=username, password=password))

    def cloud_enable(self):
        if self.cloud_busy:
            return
        url = self.cloud_choices.get(self.cloud_selected.get())
        config = self.cloud_pending or self.cloud_config
        if not url or not config.get('password'):
            self.cloud_message('Conecte, liste os calendários e selecione o calendário desejado primeiro.')
            return
        self.cloud_config = dict(config, calendar_url=url, calendar_name=self.cloud_selected.get(),
                                 enabled=True, auto=self.cloud_auto.get())
        try:
            self.cloud_vault.save(self.cloud_config)
        except Exception:
            self.cloud_config['enabled'] = False
            self.cloud_message('Não foi possível proteger a conexão nesta conta do Windows.')
            return
        self.cloud_start('sync')

    def cloud_start(self, kind, credentials=None):
        if self.cloud_busy:
            return
        config = copy.deepcopy(credentials or self.cloud_config)
        if kind == 'sync' and not config.get('enabled'):
            self.cloud_message('A conexão ainda não foi ativada.')
            return
        self.cloud_busy = True
        self.cloud_last = time.monotonic()
        self.cloud_message('Sincronizando…' if kind == 'sync' else 'Conectando ao iCloud…')
        directory = self.store.directory
        def worker():
            transport = store = None
            try:
                transport = ICloudTransport(config['username'], config['password'], config.get('calendar_url'))
                if kind == 'sync':
                    store = Store(directory)
                    result = sync_calendar(store, transport, config['calendar_url'])
                elif kind == 'create':
                    result = [transport.create_calendar()]
                else:
                    result = transport.calendars()
                self.cloud_queue.put(dict(kind=kind, result=result, credentials=config))
            except Exception as exc:
                # Never persist remote exception bodies, passwords or auth headers.
                text = connection_error_message(exc)
                self.cloud_queue.put(dict(kind=kind, error=text))
            finally:
                if store:
                    store.close()
                if transport:
                    transport.close()
        threading.Thread(target=worker, daemon=True).start()
        self.after(200, self.cloud_poll)

    def cloud_poll(self):
        try:
            message = self.cloud_queue.get_nowait()
        except queue.Empty:
            self.after(200, self.cloud_poll)
            return
        self.cloud_busy = False
        if 'error' in message:
            self.cloud_message(message['error'])
            return
        if message['kind'] == 'sync':
            report = message['result']
            self.cloud_config['last_success'] = datetime.now().strftime('%d/%m/%Y %H:%M')
            try:
                self.cloud_vault.save(self.cloud_config)
            except Exception:
                self.cloud_message('Agenda sincronizada. Não foi possível salvar a data da conexão.')
                return
            self.cloud_message(f"iCloud: {report['sent']} enviado(s), {report['received']} recebido(s), {report['conflicts']} conflito(s). Convites/itens não compatíveis: {report['unsupported']}.")
            if self.page in ('agenda', 'icloud', 'home'):
                self.render()
        else:
            self.cloud_pending = message['credentials']
            self.cloud_choices = {}
            for index, item in enumerate(message['result'], 1):
                name = item['name']
                if name in self.cloud_choices:
                    name += f' ({index})'
                self.cloud_choices[name] = item['url']
            self.cloud_message('Conta verificada. Selecione o calendário e clique em Ativar sincronização.')
            if self.page == 'icloud':
                self.render()
                if 'Projeto Diolino' in self.cloud_choices:
                    self.cloud_selected.set('Projeto Diolino')

    def check_cloud_schedule(self):
        if self.native and self.cloud_config.get('enabled') and self.cloud_config.get('auto') and not self.cloud_busy and time.monotonic() - self.cloud_last >= 300:
            self.cloud_start('sync')

    def cloud_disconnect(self):
        if self.cloud_busy:
            self.cloud_message('Aguarde a operação em andamento antes de desconectar.')
            return
        self.cloud_vault.disconnect()
        self.cloud_config = {}
        self.cloud_pending = None
        self.cloud_choices = {}
        self.cloud_message('Desconectado. Os itens já enviados permanecem no calendário Apple.')
        self.render()

    def render_calendar_conflicts(self):
        conflicts = self.store.conn.execute('SELECT l.uid,l.calendar_key,l.conflict,a.title FROM calendar_links l JOIN agenda a ON a.id=l.agenda_id WHERE l.conflict IS NOT NULL AND l.calendar_key=?',
                                            (self.cloud_config.get('calendar_url', ''),)).fetchall()
        if not conflicts:
            return
        ttk.Label(self.content, text='Conflitos da Agenda', font=('Georgia', 18)).pack(anchor='w', pady=(22, 10))
        for row in conflicts:
            panel = ttk.Frame(self.content, padding=(0, 8))
            panel.pack(fill='x')
            ttk.Label(panel, text=row['title'], font=('Segoe UI Semibold', 11), wraplength=850).pack(anchor='w')
            ttk.Label(panel, text=row['conflict'], style='Muted.TLabel', wraplength=850).pack(anchor='w', pady=5)
            if 'Recorrência ou convite' in row['conflict']:
                continue
            buttons = ttk.Frame(panel)
            buttons.pack(anchor='w')
            for value, text in [('local', 'Manter versão do PC'), ('remote', 'Usar versão do iCloud')]:
                ttk.Button(buttons, text=text, command=lambda uid=row['uid'], key=row['calendar_key'], choice=value: self.resolve_cloud(uid, key, choice)).pack(side='left', padx=(0, 8))

    def resolve_cloud(self, uid, calendar_key, choice):
        if self.cloud_busy:
            return
        with self.store.conn:
            self.store.conn.execute('UPDATE calendar_links SET resolution=? WHERE calendar_key=? AND uid=?', (choice, calendar_key, uid))
        self.cloud_start('sync')

    def show_iphone_guide(self):
        window = tk.Toplevel(self)
        window.title('Calendário e alarmes · iPhone')
        window.geometry('850x700')
        frame = ttk.Frame(window, padding=18)
        frame.pack(fill='both', expand=True)
        text = tk.Text(frame, wrap='word', font=('Segoe UI', 11), padx=18, pady=18)
        bar = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y')
        text.pack(fill='both', expand=True)
        text.insert('1.0', IPHONE_GUIDE)
        text.configure(state='disabled')
        ttk.Button(frame, text='Copiar roteiro', command=lambda: (self.clipboard_clear(), self.clipboard_append(IPHONE_GUIDE))).pack(anchor='e', pady=(12, 0))
