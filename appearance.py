"""Local desktop preferences and an idempotent adapter for classic Tk/ttk views."""
import json
import winreg
import os
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk, font as tkfont
from visual_accessibility import high_contrast_palette
from surface_ui import configure_button_artwork

DEFAULTS = dict(theme='light', text_size='standard', density='comfortable',
                title_style='classic', shadows='subtle', ornaments='crafted')
CHOICES = {
    'theme': [('light', 'Claro · Verde natural'), ('dark', 'Escuro Moderno'), ('auto', 'Automático · sistema'), ('minimal', 'Claro Minimalista'), ('blue', 'Azul Profissional'), ('green', 'Verde Natural'), ('vibrant', 'Colorido Vibrante'), ('pastel', 'Pastel Elegante'), ('purple', 'Roxo Contemporâneo'), ('sepia', 'Sépia Clássico')],
    'text_size': [('standard', 'Padrão · 100%'), ('medium', 'Maior · 110%'), ('large', 'Grande · 125%')],
    'density': [('comfortable', 'Confortável'), ('compact', 'Compacto')],
    'title_style': [('classic', 'Clássicos · Georgia'), ('modern', 'Modernos · Segoe UI')],
    'shadows': [('subtle', 'Sutil'), ('none', 'Sem sombra')],
    'ornaments': [('crafted', 'Gravura · detalhes finos'), ('plain', 'Discreto · sem ornamentos')],
}
LIGHT = dict(bg='#f4f7f6', surface='#ffffff', ink='#182c29', muted='#61716e', line='#d9e3e0',
             soft='#e9f2ef', nav='#183a35', nav_text='#d0e4df', accent='#17685a', shadow='#dce7e3')
DARK = dict(bg='#17181a', surface='#222326', ink='#eeeeef', muted='#b5b6bb', line='#414247',
            soft='#303136', nav='#101113', nav_text='#bfc0c4', accent='#eeeeef', shadow='#09090a')


PALETTES = {'light': LIGHT, 'dark': DARK, 'auto': LIGHT}
for code, colors in {
 'minimal': ('#f4f7fb','#ffffff','#172b46','#596b80','#ccd8e7','#e9f0fa','#142b49','#c6d7eb','#245fab','#dce3ed'),
 'blue': ('#edf3fa','#ffffff','#142c4c','#526a85','#becfe2','#dce8f6','#122c50','#c7d9ee','#1c5896','#d2dfed'),
 'green': ('#f2f3e9','#fffef8','#273b2c','#5a6c59','#ced7be','#e4ebd8','#263e32','#d0dfc7','#366548','#d9dfcf'),
 'vibrant': ('#f6f0ff','#ffffff','#2b2049','#695c7e','#d9c7ed','#eadcfc','#33204d','#ebd7ff','#7333b4','#dfd0ed'),
 'pastel': ('#f8f3f5','#fffafd','#423545','#776979','#e3d3df','#f0e3ed','#443546','#ecdae6','#885779','#e8dce5'),
 'purple': ('#f2eff9','#ffffff','#34224f','#6c5b80','#d3c7e4','#e6def3','#291b41','#dacbed','#69429d','#ddd4ea'),
 'sepia': ('#f3ebdd','#fff8e9','#493625','#79664e','#d6c4a8','#e9ddc8','#423124','#e4d2b5','#795738','#dfd0b8'),
}.items():
 PALETTES[code] = dict(zip(LIGHT, colors))

def system_theme():
    if os.name != 'nt':
        return 'light'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
            use_light = winreg.QueryValueEx(key, 'AppsUseLightTheme')[0]
            return 'light' if use_light else 'dark'
    except OSError:
        return 'light'


def normalize(preferences, strict=False):
    result = DEFAULTS.copy()
    if not isinstance(preferences, dict):
        if strict:
            raise ValueError('Preferências de aparência inválidas.')
        return result
    for key, choices in CHOICES.items():
        value = preferences.get(key, result[key])
        if value in [code for code, _ in choices]:
            result[key] = value
        elif strict:
            raise ValueError('Opção de aparência inválida: ' + key)
    return result


def load_preferences(directory):
    try:
        return normalize(json.loads((Path(directory) / 'appearance.json').read_text(encoding='utf-8')))
    except (OSError, ValueError, TypeError):
        return DEFAULTS.copy()


def save_preferences(directory, preferences):
    preferences = normalize(preferences, strict=True)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='appearance-', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(preferences, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, directory / 'appearance.json')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def refresh_widget(widget):
    """For views which create Canvas items or modal fields after their first map."""
    controller = getattr(widget._root(), 'appearance', None)
    if controller:
        controller.apply_tree(widget)


class AppearanceController:
    STYLES = ('.', 'TFrame', 'Surface.TFrame', 'TLabel', 'Muted.TLabel', 'Surface.TLabel',
              'SurfaceMuted.TLabel', 'Title.TLabel', 'Eyebrow.TLabel', 'TButton', 'Accent.TButton',
              'TEntry', 'TCombobox', 'TSpinbox', 'Treeview', 'Treeview.Heading', 'TCheckbutton',
              'Surface.TCheckbutton', 'Horizontal.TProgressbar', 'Vertical.TScrollbar',
              'Horizontal.TScrollbar', 'TSeparator', 'Week.TButton', 'WeekSelected.TButton')
    COLORS = ('background', 'foreground', 'activebackground', 'activeforeground', 'disabledforeground',
              'insertbackground', 'selectbackground', 'selectforeground', 'highlightbackground',
              'highlightcolor', 'readonlybackground', 'disabledbackground')

    def __init__(self, root, preferences):
        self.root = root
        self.preferences = normalize(preferences)
        self.style_base = None
        self.accessible_palette = high_contrast_palette()
        root.bind_all('<Map>', self.on_map, add='+')
        root.bind_all('<FocusIn>', self.refresh_accessibility, add='+')

    def refresh_accessibility(self, event=None):
        palette = high_contrast_palette()
        if palette != self.accessible_palette:
            self.accessible_palette = palette
            self.configure_styles()
            self.apply_tree()
            preview = getattr(self.root, 'appearance_preview', None)
            if preview is not None and preview.winfo_exists():
                self.root.preview_appearance()

    @property
    def palette(self):
        if self.accessible_palette:
            return self.accessible_palette
        theme = system_theme() if self.preferences['theme'] == 'auto' else self.preferences['theme']
        return PALETTES[theme]

    @property
    def dpi_scale(self):
        return max(.75, float(self.root.winfo_fpixels('1i')) / 96)

    @property
    def scale(self):
        return {'standard': 1, 'medium': 1.1, 'large': 1.25}[self.preferences['text_size']]

    def canonical(self, color):
        try:
            return '#%02x%02x%02x' % tuple(value // 257 for value in self.root.winfo_rgb(color))
        except tk.TclError:
            return color

    def color(self, value):
        if self.accessible_palette and value:
            try:
                rgb = self.root.winfo_rgb(value)
                brightness = (rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722) / 257
                return self.palette['surface' if brightness >= 150 else 'ink']
            except tk.TclError:
                return value
        if self.palette is LIGHT or not value:
            return value
        value = self.canonical(value)
        mapping = {original: self.palette[key] for key, original in LIGHT.items()}
        if self.palette is not DARK:
            return mapping.get(value, value)
        mapping.update({'#000000': DARK['ink'], '#f0f0f0': DARK['soft'], '#eeeeee': DARK['line'],
                        '#e6e6e6': '#3d3e44', '#999999': '#85868b', '#b8b8b8': '#67686e',
                        '#dedede': '#47484c', '#080808': '#c5c6ca', '#3c3c3c': '#d6d7db',
                        '#e5e5e5': '#3d3e44', '#b0b0b0': '#73747b', '#d9d9d9': '#4d4e54',
                        '#bdbdbd': '#68696e', '#a0a0a0': '#7b7c82', '#888888': '#a2a3a8',
                        '#237653': '#80d2a7', '#e9f4ed': '#173b2b', '#b84f48': '#f3a59d',
                        '#faeeeb': '#472a29', '#f0f0ed': '#34353a', '#8b8b84': '#c0c1ba'})
        return mapping.get(value, value)

    def font(self, original):
        data = tkfont.Font(root=self.root, font=original).actual()
        family = data['family']
        if family == 'Georgia' and self.preferences['title_style'] == 'modern':
            family = 'Segoe UI'
        # Preserve icon / monospace families; scale from the original every time.
        size = round(data['size'] * self.scale)
        flags = [data['weight'], data['slant']]
        if data['underline']:
            flags.append('underline')
        if data['overstrike']:
            flags.append('overstrike')
        return (family, size, *flags)

    def padding(self, original):
        values = self.root.tk.splitlist(original) if isinstance(original, str) else original
        if not isinstance(values, (list, tuple)):
            values = (values,)
        factor = (.7 if self.preferences['density'] == 'compact' else 1) * self.dpi_scale
        return tuple(round(float(str(value)) * factor) for value in values)

    def configure_styles(self):
        style = ttk.Style(self.root)
        if self.style_base is None:
            self.style_base = {name: (style.configure(name) or {}, style.map(name)) for name in self.STYLES}
        for name, (configuration, states) in self.style_base.items():
            result = dict(configuration)
            for key, value in configuration.items():
                if key == 'font':
                    result[key] = self.font(value)
                elif key == 'padding':
                    result[key] = self.padding(value)
                elif key == 'rowheight':
                    factor = .8 if self.preferences['density'] == 'compact' else 1
                    font = self.font(configuration.get('font', ('Segoe UI', 10)))
                    line = tkfont.Font(root=self.root, font=font).metrics('linespace')
                    result[key] = max(round(float(value) * factor * self.scale * self.dpi_scale),
                                      line + round(10 * self.dpi_scale))
                elif 'color' in key or key in ('background', 'foreground', 'fieldbackground', 'selectbackground', 'selectforeground'):
                    result[key] = self.color(value)
            if result:
                style.configure(name, **result)
            for key, entries in states.items():
                style.map(name, **{key: [(*entry[:-1], self.color(entry[-1])) for entry in entries]})
        palette = self.palette
        if self.palette is DARK and not self.accessible_palette:
            style.map('WeekSelected.TButton',
                      background=[('active', '#d6d7db'), ('!active', palette['surface'])],
                      foreground=[('active', '#111111'), ('!active', '#111111')])
        elif self.palette is LIGHT and not self.accessible_palette:
            style.map('WeekSelected.TButton',
                      background=[('active', '#333333'), ('!active', '#333333')],
                      foreground=[('active', '#ffffff'), ('!active', '#ffffff')])
        for key, color in [('background', 'surface'), ('foreground', 'ink'),
                           ('selectBackground', 'ink'), ('selectForeground', 'surface')]:
            self.root.option_add('*TCombobox*Listbox.' + key, palette[color])
        self.root.option_add('*TCombobox*Listbox.font', self.font(('Segoe UI', 10)))
        configure_button_artwork(self, style)

    @staticmethod
    def original(widget, key, current):
        cache = getattr(widget, '_appearance_originals', None)
        if cache is None:
            widget._appearance_originals = cache = {}
        # A view may change a nav color or recreate an item between applications.
        previous = cache.get(key)
        if previous is None or str(current) != str(previous[1]):
            cache[key] = [current, current]
        return cache[key][0]

    def remember(self, widget, key, value):
        widget._appearance_originals[key][1] = value

    def apply_widget(self, widget):
        if getattr(widget, '_appearance_skip', False):
            return
        options = widget.keys()
        original_bg = None
        if 'background' in options:
            original_bg = self.original(widget, 'background', widget.cget('background'))
        for key in self.COLORS:
            if key not in options:
                continue
            original = self.original(widget, key, widget.cget(key))
            value = self.color(original)
            # Resolve system aliases to app-owned roles even in light mode.
            # Disabling Windows visual effects must not select a system palette.
            if str(original).lower().startswith('system'):
                role = ('surface' if isinstance(widget, tk.Text) else 'bg') if key in ('background', 'activebackground') else 'ink'
                if key == 'selectbackground': role = 'ink'
                elif key == 'selectforeground': role = 'surface'
                elif key in ('highlightbackground', 'disabledbackground'): role = 'line'
                elif key == 'disabledforeground': role = 'muted'
                value = self.palette[role]
            if isinstance(widget, tk.Text) and self.palette is DARK:
                if key == 'selectbackground':
                    value = self.palette['ink']
                elif key == 'selectforeground':
                    value = self.palette['surface']
            if (key in ('foreground', 'activeforeground') and self.palette is DARK and not self.accessible_palette
                    and self.canonical(original) == '#ffffff' and self.canonical(original_bg or '') == LIGHT['nav']):
                value = self.palette['ink']
            widget.configure(**{key: value})
            self.remember(widget, key, widget.cget(key))
        if 'font' in options and widget.cget('font'):
            original = self.original(widget, 'font', widget.cget('font'))
            widget.configure(font=self.font(original))
            self.remember(widget, 'font', widget.cget('font'))
        if not isinstance(widget, ttk.Widget):
            for key in ('padx', 'pady'):
                if key in options:
                    original = self.original(widget, key, widget.cget(key))
                    widget.configure(**{key: self.padding(original)[0]})
                    self.remember(widget, key, widget.cget(key))
        if isinstance(widget, tk.Canvas):
            items = widget.find_all()
            cache = getattr(widget, '_appearance_originals', {})
            live_items = set(items)
            for cached_key in list(cache):
                if isinstance(cached_key, tuple) and cached_key[0] not in live_items:
                    del cache[cached_key]
            for item in items:
                item_options = widget.itemconfigure(item)
                for key in ('fill', 'outline', 'font'):
                    if key not in item_options:
                        continue
                    cache_key = (item, key)
                    original = self.original(widget, cache_key, widget.itemcget(item, key))
                    if not original:
                        continue
                    value = self.font(original) if key == 'font' else self.color(original)
                    widget.itemconfigure(item, **{key: value})
                    self.remember(widget, cache_key, widget.itemcget(item, key))
            if widget.find_withtag('shadow') and widget.find_withtag('title'):
                widget.itemconfigure('shadow', state='hidden' if self.preferences['shadows'] == 'none' or self.accessible_palette else 'normal')
                bounds = widget.bbox('all')
                if bounds:
                    widget.configure(height=bounds[3] + 3)

    def apply_tree(self, widget=None):
        widget = widget or self.root
        # Combobox popdowns are Tcl-only windows; Tk sends their path as a string.
        if not isinstance(widget, tk.Misc) or not widget.winfo_exists() or getattr(widget, '_appearance_skip', False):
            return
        self.apply_widget(widget)
        for child in widget.winfo_children():
            self.apply_tree(child)
        if hasattr(widget, 'layout_surface'):
            widget.layout_surface()
        elif hasattr(widget, 'refresh_surface'):
            widget.refresh_surface()
        if hasattr(widget, 'refresh_icon'):
            widget.refresh_icon()

    def on_map(self, event):
        self.apply_tree(event.widget)

    def activate(self, preferences):
        self.preferences = normalize(preferences, strict=True)
        self.configure_styles()
        self.apply_tree()
