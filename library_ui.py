"""Native Bible reader links and local print/export workspace."""
import tkinter as tk
import webbrowser
from datetime import date, timedelta
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
from uuid import uuid4
from bible_library import BOOKS, VERSIONS, passage, reading_plan
from print_documents import build_report, build_template, TEMPLATES
from inputs import DateTimeInput
from models import MODELS


class LibraryViews:
    def render_bible_library(self):
        self.heading('Biblioteca bíblica', 'Selecione a versão e a referência. A leitura abre no navegador; os registros de estudo ficam neste PC.')
        panel = ttk.Frame(self.content)
        panel.pack(fill='x')
        self.bible_version = tk.StringVar(value='NAA')
        self.bible_book = tk.StringVar(value='João')
        self.bible_chapter = tk.StringVar(value='1')
        for label, variable, options in [('Versão', self.bible_version, list(VERSIONS)),
                                          ('Livro', self.bible_book, [r[0] for r in BOOKS])]:
            ttk.Label(panel, text=label).pack(anchor='w', pady=(10, 4))
            combo = ttk.Combobox(panel, textvariable=variable, values=options, state='readonly')
            combo.pack(fill='x')
            if label == 'Livro': combo.bind('<<ComboboxSelected>>', self.update_bible_chapters)
        ttk.Label(panel, text='Capítulo').pack(anchor='w', pady=(10, 4))
        self.bible_chapters = ttk.Combobox(panel, textvariable=self.bible_chapter, values=list(range(1, 22)), state='readonly', width=8)
        self.bible_chapters.pack(anchor='w')
        actions = ttk.Frame(self.content)
        actions.pack(fill='x', pady=18)
        ttk.Button(actions, text='Abrir capítulo online', style='Accent.TButton', command=self.open_bible).pack(side='left')
        ttk.Button(actions, text='Registrar estudo', command=self.record_bible).pack(side='left', padx=8)
        ttk.Button(actions, text='Imprimir ficha de estudo', command=self.print_bible_sheet).pack(side='left')
        ttk.Label(self.content, text='Consulta em outra versão', font=('Segoe UI Semibold', 12)).pack(anchor='w', pady=(14, 8))
        compare = ttk.Frame(self.content)
        compare.pack(fill='x')
        self.bible_compare = tk.StringVar(value='NVI')
        ttk.Combobox(compare, textvariable=self.bible_compare, values=list(VERSIONS), state='readonly', width=14).pack(side='left')
        ttk.Button(compare, text='Abrir a mesma referência', command=lambda: self.open_bible(self.bible_compare.get())).pack(side='left', padx=8)
        ttk.Label(self.content, text='Planos de leitura', font=('Segoe UI Semibold', 12)).pack(anchor='w', pady=(26, 8))
        ttk.Label(self.content, text='Um capítulo por dia a partir da data de referência. As etapas ficam disponíveis em Planos para checagem.',
                  style='Muted.TLabel', wraplength=900).pack(anchor='w')
        row = ttk.Frame(self.content)
        row.pack(fill='x', pady=12)
        for book, count in [('João', 21), ('Provérbios', 31)]:
            ttk.Button(row, text=f'Criar plano: {book} · {count} dias', command=lambda b=book: self.create_reading_plan(b)).pack(side='left', padx=(0, 8))
        ttk.Label(self.content, text='Versões disponíveis', font=('Segoe UI Semibold', 12)).pack(anchor='w', pady=(20, 8))
        for code, (name, _) in VERSIONS.items():
            ttk.Label(self.content, text=f'{code} · {name}', style='Muted.TLabel').pack(anchor='w', pady=2)
        ttk.Label(self.content, text='Leitores: YouVersion / Bible.com e Bíblia Online (ACF). A leitura requer internet. '
                  'O Diolino não armazena cópias dessas traduções nem sincroniza contas dos leitores. Abrir um capítulo não confirma o pilar bíblico.',
                  style='Muted.TLabel', wraplength=900).pack(anchor='w', pady=20)
        ttk.Button(self.content, text='Consultar meus registros bíblicos', command=lambda: self.navigate('bible')).pack(anchor='w')

    def update_bible_chapters(self, event=None):
        count = next(row[2] for row in BOOKS if row[0] == self.bible_book.get())
        self.bible_chapters.configure(values=list(range(1, count + 1)))
        self.bible_chapter.set('1')

    def selected_passage(self, version=None):
        return passage(version or self.bible_version.get(), self.bible_book.get(), self.bible_chapter.get())

    def open_bible(self, version=None):
        try:
            selected = self.selected_passage(version)
            if not webbrowser.open(selected['url']):
                raise OSError('Não foi possível abrir o navegador padrão.')
        except (ValueError, OSError) as exc:
            messagebox.showerror('Leitura bíblica', str(exc), parent=self)

    def record_bible(self):
        from app import Editor
        selected = self.selected_passage()
        Editor(self, 'bible', {'date': self.day.get(), 'passage': selected['reference'],
                             'notes': 'Leitor: ' + selected['url']})

    def create_reading_plan(self, book):
        try:
            reading_plan(self.store, book, self.bible_version.get(), self.day.get())
            self.navigate('planning')
            self.set_status('Plano de leitura criado. Registre os estudos após realizar a leitura.')
        except ValueError as exc:
            messagebox.showerror('Plano de leitura', str(exc), parent=self)

    def print_bible_sheet(self):
        self.open_print_document(build_template(self.store, 'biblical', self.day.get(), reference=self.selected_passage()['reference']))

    def render_printing(self):
        self.heading('Relatórios e impressão', 'Selecione os dados ou um modelo. A prévia abre no navegador e permite imprimir ou salvar como PDF.')
        ttk.Label(self.content, text='RELATÓRIOS / TODAS AS ÁREAS', style='Eyebrow.TLabel').pack(anchor='w', pady=(0, 12))
        dates = ttk.Frame(self.content)
        dates.pack(fill='x')
        selected = date.fromisoformat(self.day.get())
        for text, key, value in [('Início', 'report_start', selected.replace(day=1).isoformat()), ('Fim', 'report_end', self.day.get())]:
            cell = ttk.Frame(dates)
            cell.pack(side='left', padx=(0, 24))
            ttk.Label(cell, text=text).pack(anchor='w')
            widget = DateTimeInput(cell, 'date', value, shortcuts=False)
            widget.pack(anchor='w')
            setattr(self, key, widget)
        ttk.Label(self.content, text='Áreas incluídas', font=('Segoe UI Semibold', 11)).pack(anchor='w', pady=(18, 8))
        areas = ttk.Frame(self.content)
        areas.pack(fill='x')
        self.report_kinds = {kind: tk.BooleanVar(value=True) for kind in MODELS}
        for index, (kind, (label, _)) in enumerate(MODELS.items()):
            ttk.Checkbutton(areas, text=label, variable=self.report_kinds[kind]).grid(row=index // 3, column=index % 3, sticky='w', padx=(0, 22), pady=4)
        selection = ttk.Frame(self.content)
        selection.pack(fill='x', pady=10)
        for text, value in [('Selecionar todas', True), ('Limpar seleção', False)]:
            ttk.Button(selection, text=text, command=lambda v=value: [var.set(v) for var in self.report_kinds.values()]).pack(side='left', padx=(0, 8))
        self.report_notes = tk.BooleanVar(value=True)
        self.report_summary = tk.BooleanVar(value=True)
        self.report_empty = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.content, text='Incluir anotações, reflexões e campos detalhados', variable=self.report_notes).pack(anchor='w', pady=4)
        ttk.Checkbutton(self.content, text='Incluir resumo diário dos pilares e sono', variable=self.report_summary).pack(anchor='w', pady=4)
        ttk.Checkbutton(self.content, text='Incluir seções de áreas sem registros', variable=self.report_empty).pack(anchor='w', pady=4)
        ttk.Label(self.content, text='O período filtra registros datados. Perfil, planos sem datas e etapas sem prazo são incluídos quando selecionados. '
                  'Relatórios incluem somente registros ativos. Período máximo: 366 dias.', style='Muted.TLabel', wraplength=900).pack(anchor='w', pady=8)
        actions = ttk.Frame(self.content)
        actions.pack(fill='x', pady=10)
        ttk.Button(actions, text='Visualizar relatório / Imprimir', style='Accent.TButton', command=self.generate_report).pack(side='left')
        ttk.Button(actions, text='Salvar relatório em arquivo…', command=lambda: self.generate_report(True)).pack(side='left', padx=8)
        ttk.Separator(self.content).pack(fill='x', pady=20)
        ttk.Label(self.content, text='PLANNERS / MODELOS A4', style='Eyebrow.TLabel').pack(anchor='w')
        ttk.Label(self.content, text='Usam a data de referência no topo do aplicativo. Semana de segunda a domingo; mês completo.',
                  style='Muted.TLabel', wraplength=900).pack(anchor='w', pady=8)
        self.print_template = tk.StringVar(value=TEMPLATES['daily'])
        ttk.Combobox(self.content, textvariable=self.print_template, values=list(TEMPLATES.values()), state='readonly').pack(fill='x', pady=8)
        self.print_filled = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.content, text='Incluir registros existentes (agenda, etapas e confirmações, conforme o modelo)', variable=self.print_filled).pack(anchor='w', pady=6)
        ttk.Label(self.content, text='Diário: pilares, prioridades, agenda, hábitos e notas. Semanal: programação dos sete dias. '
                  'Mensal: calendário, objetivos e checagem de hábitos. Caderno integrado: semana + sete dias + fichas de estudo médico e bíblico + plano de ação.',
                  style='Muted.TLabel', wraplength=900).pack(anchor='w', pady=10)
        actions = ttk.Frame(self.content)
        actions.pack(fill='x', pady=10)
        ttk.Button(actions, text='Visualizar modelo / Imprimir', style='Accent.TButton', command=self.generate_template).pack(side='left')
        ttk.Button(actions, text='Salvar modelo em arquivo…', command=lambda: self.generate_template(True)).pack(side='left', padx=8)
        ttk.Label(self.content, text='Formato A4, retrato, preto e branco. Na janela de impressão, escolha sua impressora ou Salvar como PDF. '
                  'Os documentos são cópias locais; marcações feitas no papel não alteram o aplicativo.', style='Muted.TLabel', wraplength=900).pack(anchor='w', pady=14)

    def generate_report(self, save_as=False):
        try:
            html = build_report(self.store, self.report_start.get(), self.report_end.get(),
                                [kind for kind, variable in self.report_kinds.items() if variable.get()],
                                self.report_notes.get(), self.report_summary.get(), self.report_empty.get())
            return self.open_print_document(html, save_as)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Relatório', str(exc), parent=self)

    def generate_template(self, save_as=False):
        try:
            kind = next(key for key, label in TEMPLATES.items() if label == self.print_template.get())
            return self.open_print_document(build_template(self.store, kind, self.day.get(), self.print_filled.get()), save_as)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Modelo de impressão', str(exc), parent=self)

    def open_print_document(self, html, save_as=False):
        if save_as:
            destination = filedialog.asksaveasfilename(parent=self, title='Salvar documento para impressão',
                initialfile='Diolino-' + self.day.get() + '.html', defaultextension='.html', filetypes=[('Documento para impressão', '*.html')])
            if not destination:
                return None
            path = Path(destination)
        else:
            folder = self.store.directory / 'impressos'
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / ('Diolino-' + self.day.get() + '-' + uuid4().hex[:10] + '.html')
        path.write_text(html, encoding='utf-8')
        opened = webbrowser.open(path.resolve().as_uri())
        self.set_status(('Prévia aberta. Use Imprimir / Salvar PDF. ' if opened else 'Arquivo salvo. Abra no navegador: ') + str(path))
        return path
