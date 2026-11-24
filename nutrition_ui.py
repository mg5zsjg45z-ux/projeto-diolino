"""TACO browser and food editor integration, with no runtime network requests."""
import copy
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

from nutrition import catalogue, grams_value, nutrient_text, scale, MACROS, SOURCE_NAME, reference
from theme import BG, INK, MUTED


def number_text(value):
    return '' if value is None else f'{value:.6f}'.rstrip('0').rstrip('.').replace('.', ',')


class TacoPicker(tk.Toplevel):
    def __init__(self, parent, callback, snapshot=None, grams=100):
        super().__init__(parent)
        self.parent, self.callback = parent, callback
        self.catalogue = catalogue()
        self.snapshot = snapshot
        self.title('Tabela TACO • Projeto Diolino')
        self.geometry('1160x760')
        self.minsize(900, 620)
        self.configure(bg=BG)
        self.transient(parent)
        self.grab_set()
        self.protocol('WM_DELETE_WINDOW', self.cancel)
        self.bind('<Escape>', lambda _: self.cancel())
        shell = ttk.Frame(self, padding=24)
        shell.pack(fill='both', expand=True)
        header = ttk.Frame(shell)
        header.pack(fill='x')
        ttk.Label(header, text='Tabela TACO', style='Title.TLabel').pack(side='left')
        ttk.Button(header, text='Fonte oficial ↗', command=lambda: webbrowser.open(self.catalogue.metadata['page_url'])).pack(side='right')
        meta = self.catalogue.metadata
        ttk.Label(shell, text=f"NEPA/UNICAMP · {meta['edition']} ({meta['year']}) · 597 alimentos · consulta offline",
                  style='Muted.TLabel').pack(anchor='w', pady=(8, 16))
        filters = ttk.Frame(shell)
        filters.pack(fill='x', pady=(0, 14))
        ttk.Label(filters, text='Buscar alimento').grid(row=0, column=0, sticky='w', pady=(0, 5))
        ttk.Label(filters, text='Categoria').grid(row=0, column=1, sticky='w', padx=(14, 0), pady=(0, 5))
        self.query = tk.StringVar()
        self.category = tk.StringVar(value='Todas as categorias')
        search = ttk.Entry(filters, textvariable=self.query)
        search.grid(row=1, column=0, sticky='ew')
        categories = ttk.Combobox(filters, textvariable=self.category, state='readonly', width=35,
                                  values=['Todas as categorias', *self.catalogue.categories])
        categories.grid(row=1, column=1, sticky='ew', padx=(14, 0))
        filters.columnconfigure(0, weight=1)
        categories.bind('<<ComboboxSelected>>', lambda _: self.fill_foods())
        self.query.trace_add('write', lambda *_: self.fill_foods())
        body = ttk.Frame(shell)
        body.columnconfigure(0, weight=3, uniform='browser')
        body.columnconfigure(1, weight=2, uniform='browser')
        body.rowconfigure(0, weight=1)
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 16))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        self.count = ttk.Label(left, style='Muted.TLabel')
        self.count.grid(row=0, column=0, sticky='w', pady=(0, 7))
        self.foods_tree = ttk.Treeview(left, columns=('code', 'name', 'kcal'), show='headings', selectmode='browse')
        for key, title, width in [('code', 'Código', 62), ('name', 'Alimento / preparação', 330), ('kcal', 'kcal / 100 g', 112)]:
            self.foods_tree.heading(key, text=title)
            self.foods_tree.column(key, width=width, minwidth=width, stretch=key == 'name', anchor='w' if key == 'name' else 'center')
        self.foods_tree.grid(row=1, column=0, sticky='nsew')
        ybar = ttk.Scrollbar(left, command=self.foods_tree.yview)
        ybar.grid(row=1, column=1, sticky='ns')
        xbar = ttk.Scrollbar(left, orient='horizontal', command=self.foods_tree.xview)
        xbar.grid(row=2, column=0, sticky='ew')
        self.foods_tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.foods_tree.bind('<<TreeviewSelect>>', self.select_food)
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky='nsew')
        self.selected_name = ttk.Label(right, text='Selecione um alimento', font=('Segoe UI Semibold', 11), wraplength=360)
        self.selected_name.pack(anchor='w', fill='x', pady=(0, 12))
        right.bind('<Configure>', lambda e: self.selected_name.configure(wraplength=max(160, e.width)))
        quantity = ttk.Frame(right)
        quantity.pack(fill='x', pady=(0, 12))
        ttk.Label(quantity, text='Quantidade consumida (g)').pack(side='left')
        self.grams = tk.StringVar(value=str(grams).replace('.', ','))
        ttk.Entry(quantity, textvariable=self.grams, width=10).pack(side='right')
        self.grams.trace_add('write', lambda *_: self.fill_nutrients())
        nutrients = ttk.Frame(right)
        nutrients.pack(fill='both', expand=True)
        self.nutrients_tree = ttk.Treeview(nutrients, columns=('nutrient', 'basis', 'portion'), show='headings', selectmode='none')
        for key, title, width in [('nutrient', 'Nutriente (unidade)', 190), ('basis', '100 g', 108), ('portion', 'Sua porção', 108)]:
            self.nutrients_tree.heading(key, text=title)
            self.nutrients_tree.column(key, width=width, minwidth=width, stretch=key == 'nutrient')
        self.nutrients_tree.pack(side='left', fill='both', expand=True)
        bar = ttk.Scrollbar(nutrients, command=self.nutrients_tree.yview)
        bar.pack(side='right', fill='y')
        self.nutrients_tree.configure(yscrollcommand=bar.set)
        horizontal = ttk.Scrollbar(right, orient='horizontal', command=self.nutrients_tree.xview)
        horizontal.pack(fill='x')
        self.nutrients_tree.configure(xscrollcommand=horizontal.set)
        bottom = ttk.Frame(shell)
        bottom.pack(side='bottom', fill='x')
        self.message = ttk.Label(bottom, text='', style='Muted.TLabel', wraplength=1050)
        self.message.pack(anchor='w', pady=(12, 6))
        information = ttk.Label(bottom, text='Base: 100 g de parte comestível. Escolha cru/cozido e pese a porção; mL e medidas caseiras não são convertidos automaticamente.\nTraço, não aplicável, em reavaliação e campos ausentes são preservados, sem virar zero.',
                                style='Muted.TLabel', wraplength=1050)
        information.pack(anchor='w', pady=(0, 14))
        shell.bind('<Configure>', lambda e: (information.configure(wraplength=max(300, e.width - 48)),
                                             self.message.configure(wraplength=max(300, e.width - 48))))
        footer = ttk.Frame(bottom)
        footer.pack(fill='x')
        self.apply_button = ttk.Button(footer, text='Usar alimento e quantidade', style='Accent.TButton', command=self.apply)
        self.apply_button.pack(side='right')
        ttk.Button(footer, text='Cancelar', command=self.cancel).pack(side='right', padx=10)
        body.pack(fill='both', expand=True)
        self.fill_foods()
        if snapshot:
            code = str(snapshot['food']['code'])
            if self.foods_tree.exists(code):
                self.foods_tree.selection_set(code)
                self.foods_tree.see(code)
                self.select_food()
        self.fill_nutrients()
        search.focus_set()

    def fill_foods(self):
        selected = self.foods_tree.selection()
        self.foods_tree.delete(*self.foods_tree.get_children())
        category = None if self.category.get() == 'Todas as categorias' else self.category.get()
        matches = self.catalogue.search(self.query.get(), category)
        for food in matches:
            self.foods_tree.insert('', 'end', iid=str(food['code']), values=(food['code'], food['name'], nutrient_text(food['nutrients']['kcal'])))
        self.count.configure(text=f'{len(matches)} alimento(s) encontrado(s)')
        # Filtering never leaves an invisible previous selection active.
        self.snapshot = None
        if selected and self.foods_tree.exists(selected[0]):
            self.foods_tree.selection_set(selected[0])
            self.snapshot = self.catalogue.snapshot(int(selected[0]))
        self.fill_nutrients()

    def select_food(self, _=None):
        selected = self.foods_tree.selection()
        self.snapshot = self.catalogue.snapshot(int(selected[0])) if selected else None
        self.fill_nutrients()

    def fill_nutrients(self):
        self.nutrients_tree.delete(*self.nutrients_tree.get_children())
        self.apply_button.state(['disabled'])
        self.selected_name.configure(text=self.snapshot['food']['name'] if self.snapshot else 'Selecione um alimento')
        if not self.snapshot:
            self.message.configure(text='Busque pelo nome, sem precisar digitar acentos, e selecione a preparação desejada.')
            return
        try:
            grams = grams_value(self.grams.get())
        except ValueError as exc:
            self.message.configure(text=str(exc))
            return
        food = self.snapshot['food']
        for field in self.catalogue.fields:
            raw = food['nutrients'].get(field['key'])
            self.nutrients_tree.insert('', 'end', values=(f"{field['label']} ({field['unit']})", nutrient_text(raw), nutrient_text(raw, grams)))
        incomplete = [key for key, value in scale(food['nutrients'], grams).items() if key in MACROS and value is None]
        self.message.configure(text=(f'Porção: {number_text(grams)} g · {nutrient_text(food["nutrients"]["kcal"], grams)} kcal.' +
                                    (' Há nutrientes sem valor numérico; eles ficarão em aberto no registro.' if incomplete else '')))
        self.apply_button.state(['!disabled'])

    def apply(self):
        if self.snapshot is None:
            return
        try:
            grams = grams_value(self.grams.get())
        except ValueError as exc:
            messagebox.showerror('Quantidade inválida', str(exc), parent=self)
            return
        snapshot = copy.deepcopy(self.snapshot)
        self.cancel()
        self.callback(snapshot, grams)

    def cancel(self):
        self.destroy()
        if isinstance(self.parent, tk.Toplevel) and self.parent.winfo_exists():
            self.parent.grab_set()


class FoodNutritionEditor:
    def build_nutrition_header(self, header, record):
        self.nutrition_snapshot = copy.deepcopy((record or {}).get('_nutrition'))
        self.nutrition_busy = False
        panel = ttk.Frame(header)
        panel.pack(fill='x', pady=(12, 0))
        ttk.Button(panel, text='Buscar alimento na TACO', style='Accent.TButton', command=self.choose_taco).pack(side='left')
        ttk.Button(panel, text='Preenchimento manual', command=self.unlink_taco).pack(side='left', padx=8)
        self.nutrition_status = ttk.Label(header, text='', style='Muted.TLabel', wraplength=690)
        self.nutrition_status.pack(anchor='w', pady=(10, 0))

    def finish_nutrition_form(self):
        self.vars['quantity'].trace_add('write', lambda *_: self.recalculate_taco())
        self.update_nutrition_controls()

    def choose_taco(self):
        TacoPicker(self, self.apply_taco, self.nutrition_snapshot,
                   self.vars['quantity'].get() if self.vars['quantity'].get() else 100)

    def apply_taco(self, snapshot, grams):
        self.nutrition_busy = True
        self.nutrition_snapshot = copy.deepcopy(snapshot)
        self.vars['food_name'].set(snapshot['food']['name'])
        self.vars['quantity'].set(number_text(grams))
        self.vars['unit'].set('g')
        self.vars['source'].set(SOURCE_NAME)
        self.vars['reference'].set(reference(snapshot))
        self.nutrition_busy = False
        self.recalculate_taco()
        self.update_nutrition_controls()

    def recalculate_taco(self):
        if self.nutrition_busy or not self.nutrition_snapshot:
            return
        try:
            grams = grams_value(self.vars['quantity'].get())
            totals = scale(self.nutrition_snapshot['food']['nutrients'], grams)
        except ValueError as exc:
            for key in MACROS:
                self.vars[key].set('')
            self.nutrition_status.configure(text=str(exc))
            return
        for key in MACROS:
            self.vars[key].set(number_text(totals[key]))
        self.nutrition_status.configure(text=f"TACO · código {self.nutrition_snapshot['food']['code']} · {number_text(grams)} g. A quantidade recalcula os nutrientes. Para alterar os valores, use Preenchimento manual.")

    def update_nutrition_controls(self):
        linked = bool(self.nutrition_snapshot)
        for key in ('food_name', 'unit', 'source', 'reference', *MACROS):
            self.field_widgets[key].configure(state='readonly' if linked or key in ('unit', 'source') else 'normal')
        if linked:
            self.nutrition_status.configure(text=f"Fonte salva: TACO · código {self.nutrition_snapshot['food']['code']} · {self.nutrition_snapshot['metadata']['edition']} ({self.nutrition_snapshot['metadata']['year']}). Valores da porção consumida.")
        else:
            self.nutrition_status.configure(text='Preenchimento manual. Ou selecione um alimento da TACO para calcular a porção em gramas.')

    def unlink_taco(self):
        if self.nutrition_snapshot:
            self.nutrition_snapshot = None
            self.vars['source'].set('Estimativa')
            self.vars['reference'].set('Valores inicialmente calculados pela TACO; alterados para preenchimento manual.')
        self.update_nutrition_controls()
