"""Automatic table sizing and readable, complete cell previews."""
import tkinter as tk
from tkinter import ttk, font

SHORT_LABELS = {
    'food_name': 'Alimento / bebida', 'quantity': 'Quantidade', 'unit': 'Unidade',
    'kcal': 'Energia (kcal)', 'protein_g': 'Proteínas (g)', 'carbs_g': 'Carboidratos (g)',
    'fat_g': 'Gorduras (g)', 'fiber_g': 'Fibras (g)', 'source': 'Fonte',
    'reference': 'Referência', 'brand': 'Marca / preparação',
}


def fit_columns(tree, fields):
    if not tree.winfo_exists():
        return
    body = font.Font(tree, font=ttk.Style(tree).lookup('Treeview', 'font') or ('Segoe UI', 10))
    heading = font.Font(tree, font=ttk.Style(tree).lookup('Treeview.Heading', 'font') or ('Segoe UI Semibold', 10))
    widths = {}
    for col in tree['columns']:
        head = tree.heading(col, 'text')
        minimum = max(60, heading.measure(head) + 32)
        content = max((body.measure(str(tree.set(item, col)).replace('\n', ' / ')) + 28
                       for item in tree.get_children()[:300]), default=minimum)
        widths[col] = max(minimum, min(content, 440))
    extra = max(0, tree.winfo_width() - sum(widths.values()) - 4)
    flexible = [f.key for f in fields if f.type in ('text', 'long')]
    for col in flexible:
        widths[col] += extra // max(1, len(flexible))
    for col, width in widths.items():
        field = next((f for f in fields if f.key == col), None)
        tree.column(col, width=int(width), minwidth=55, stretch=False,
                    anchor='e' if field and field.type in ('number', 'integer') else 'w')


class CellPreview:
    def __init__(self, tree):
        self.tree = tree
        self.job = self.popup = None
        self.cell = None
        tree.bind('<Motion>', self.motion, add='+')
        tree.bind('<Leave>', lambda _: self.hide(), add='+')
        tree.bind('<ButtonPress>', lambda _: self.hide(), add='+')
        tree.bind('<Destroy>', lambda _: self.hide(), add='+')

    def hide(self):
        if self.job:
            try: self.tree.after_cancel(self.job)
            except tk.TclError: pass
            self.job = None
        if self.popup:
            self.popup.destroy()
            self.popup = None
        self.cell = None

    def motion(self, event):
        cell = (self.tree.identify_row(event.y), self.tree.identify_column(event.x))
        if cell == self.cell:
            return
        self.hide()
        if not all(cell):
            return
        self.cell = cell
        value = str(self.tree.set(*cell))
        if value and value != '—':
            self.job = self.tree.after(600, lambda: self.show(value, event.x_root, event.y_root))

    def show(self, value, x, y):
        self.job = None
        if not self.tree.winfo_exists():
            return
        self.popup = tk.Toplevel(self.tree)
        self.popup.overrideredirect(True)
        self.popup.attributes('-topmost', True)
        tk.Label(self.popup, text=value, bg='#202020', fg='white', font=('Segoe UI', 10),
                 wraplength=520, justify='left', padx=14, pady=10).pack()
        self.popup.update_idletasks()
        x = min(x + 12, self.tree.winfo_screenwidth() - self.popup.winfo_reqwidth() - 12)
        y = min(y + 20, self.tree.winfo_screenheight() - self.popup.winfo_reqheight() - 40)
        self.popup.geometry(f'+{max(0,x)}+{max(0,y)}')
