"""Appearance editor: draft-only preview until the user chooses to apply."""
import tkinter as tk
from tkinter import ttk, messagebox
from appearance import CHOICES, DEFAULTS, DARK, LIGHT, PALETTES, save_preferences


class AppearanceViews:
    def render_appearance(self):
        self.heading('Configurações · Aparência e Temas', 'Configure tema, tipografia e espaçamento. Confira a prévia antes de aplicar.')
        panel = ttk.Frame(self.content)
        panel.pack(fill='x')
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)
        self.appearance_vars = {key: tk.StringVar(value=value) for key, value in self.appearance.preferences.items()}
        labels = {'theme': 'Tema', 'text_size': 'Tamanho do texto', 'density': 'Espaçamento',
                  'title_style': 'Estilo dos títulos', 'shadows': 'Sombra dos títulos',
                  'ornaments': 'Acabamento gráfico'}
        for index, (key, choices) in enumerate(CHOICES.items()):
            cell = ttk.Frame(panel, padding=(0, 0, 20, 16))
            cell.grid(row=index // 2, column=index % 2, sticky='ew')
            ttk.Label(cell, text=labels[key]).pack(anchor='w', pady=(0, 6))
            label = tk.StringVar(value=dict(choices)[self.appearance_vars[key].get()])
            combo = ttk.Combobox(cell, textvariable=label, values=[text for _, text in choices], state='readonly')
            combo.pack(fill='x')
            combo.bind('<<ComboboxSelected>>', lambda e, k=key, v=label, c=choices:
                       self.appearance_vars[k].set(next(code for code, text in c if text == v.get())))
            self.appearance_vars[key].trace_add('write', lambda *args, k=key, v=label, c=choices: v.set(dict(c)[self.appearance_vars[k].get()]))
        ttk.Label(self.content, text='PRÉVIA', style='Eyebrow.TLabel').pack(anchor='w', pady=(6, 10))
        self.appearance_preview = tk.Canvas(self.content, height=260, highlightthickness=0)
        self.appearance_preview._appearance_skip = True
        self.appearance_preview.pack(fill='x')
        self.appearance_preview.bind('<Configure>', lambda e: self.preview_appearance())
        for variable in self.appearance_vars.values():
            variable.trace_add('write', lambda *args: self.preview_appearance())
        self.preview_appearance()
        ttk.Label(self.content, text='O modo compacto reduz o espaço dos controles e das linhas das tabelas.\n'
                  'As escolhas ficam salvas neste PC. A aparência do Safari é ajustada no próprio navegador.',
                  style='Muted.TLabel', wraplength=900).pack(anchor='w', pady=14)
        actions = ttk.Frame(self.content)
        actions.pack(fill='x', pady=(6, 16))
        ttk.Button(actions, text='Salvar e aplicar', style='Accent.TButton', command=self.save_appearance).pack(side='left')
        ttk.Button(actions, text='Desfazer alterações', command=self.discard_appearance).pack(side='left', padx=8)
        ttk.Button(actions, text='Restaurar padrão', command=self.reset_appearance).pack(side='left')

    def preview_appearance(self):
        canvas = self.appearance_preview
        values = {key: variable.get() for key, variable in self.appearance_vars.items()}
        palette = self.appearance.accessible_palette or PALETTES[values['theme']]
        scale = {'standard': 1, 'medium': 1.1, 'large': 1.25}[values['text_size']]
        family = 'Georgia' if values['title_style'] == 'classic' else 'Segoe UI'
        gap = 34 if values['density'] == 'compact' else 44
        width = max(350, canvas.winfo_width())
        canvas.configure(bg=palette['bg'])
        canvas.delete('all')
        canvas.create_rectangle(1, 1, width - 1, 259, fill=palette['surface'], outline=palette['line'])
        if values['ornaments'] == 'crafted' and not self.appearance.accessible_palette:
            canvas.create_line(10, 38, 10, 10, 38, 10, fill=palette['line'])
            canvas.create_line(width-38, 249, width-10, 249, width-10, 221, fill=palette['line'])
        if values['shadows'] == 'subtle' and not self.appearance.accessible_palette:
            canvas.create_text(25, 23, text='Painel de controle', anchor='nw',
                               font=(family, round(24 * scale)), fill=palette['shadow'])
        canvas.create_text(24, 22, text='Painel de controle', anchor='nw',
                           font=(family, round(24 * scale)), fill=palette['ink'])
        canvas.create_text(24, 78, text='Status dos pilares diários', anchor='nw',
                           font=('Segoe UI', round(10 * scale)), fill=palette['muted'])
        for index, (symbol, text) in enumerate([('✓', 'Medicina'), ('✓', 'Exercício'), ('–', 'Estudo bíblico')]):
            y = 123 + index * gap
            canvas.create_text(24, y, text=symbol, anchor='w', font=('Segoe UI Semibold', round(12 * scale)),
                               fill=palette['ink'] if self.appearance.accessible_palette else
                               (('#80d2a7' if values['theme'] == 'dark' else '#237653') if index < 2 else palette['muted']))
            canvas.create_text(52, y, text=text, anchor='w', font=('Segoe UI', round(10 * scale)), fill=palette['ink'])

    def discard_appearance(self):
        for key, value in self.appearance.preferences.items():
            self.appearance_vars[key].set(value)

    def reset_appearance(self):
        for key, value in DEFAULTS.items():
            self.appearance_vars[key].set(value)

    def save_appearance(self):
        values = {key: variable.get() for key, variable in self.appearance_vars.items()}
        try:
            save_preferences(self.store.directory, values)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Não foi possível salvar a aparência', str(exc), parent=self)
            return
        self.appearance.activate(values)
        self.set_status('Aparência salva e aplicada neste PC.')
