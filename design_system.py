"""Shared visual tokens and reusable responsive controls for the desktop UI."""
from tkinter import ttk
from surface_ui import card_body

from theme import SPACE_SCALE as SPACE, RADIUS_SCALE as RADIUS, TYPE_SCALE as TYPE

SIDEBAR_BREAKPOINT = 1200
COMPACT_NAV = 168
FULL_NAV = 232

def navigation_width(width):
    return COMPACT_NAV if width < SIDEBAR_BREAKPOINT else FULL_NAV

def grid_columns(width, minimum=220, maximum=3):
    return max(1, min(maximum, width // minimum))

def adaptive_grid(parent, widgets, minimum=220, maximum=3):
    """Reflow existing widgets without destroying focus or data."""
    previous = None
    def layout(event=None):
        nonlocal previous
        controller = getattr(parent._root(), 'appearance', None)
        dpi = controller.dpi_scale if controller else 1
        density = controller.density_scale if controller else 1
        text_scale = controller.scale if controller else 1
        gap = max(2, round(SPACE[0] * dpi * density))
        columns = grid_columns(parent.winfo_width(), round(minimum * dpi * text_scale * density), maximum)
        geometry = (columns, gap)
        if geometry == previous:
            return
        previous = geometry
        for col in range(maximum):
            parent.columnconfigure(col, weight=int(col < columns), uniform='adaptive')
        for index, widget in enumerate(widgets):
            widget.grid(row=index//columns, column=index%columns,
                        sticky='nsew', padx=gap, pady=gap)
    parent.adaptive_layout = layout
    parent.bind('<Configure>', layout, add='+')
    layout()

def metric_card(parent, title, value, detail, progress=None):
    body = card_body(parent, padding=16)
    ttk.Label(body, text=title, style='SurfaceMuted.TLabel').pack(anchor='w')
    ttk.Label(body, text=value, style='Surface.TLabel',
              font=TYPE['metric']).pack(anchor='w', pady=(8, 4))
    if progress is not None:
        ttk.Progressbar(body, mode='determinate', maximum=100,
                        value=max(0,min(100,progress))).pack(fill='x',pady=(3,6))
    label = ttk.Label(body, text=detail, style='SurfaceMuted.TLabel', wraplength=180)
    label.pack(anchor='w', fill='x')
    body.bind('<Configure>', lambda e: label.configure(wraplength=max(80,e.width-8)), add='+')
    return body.master

def action_grid(parent, actions):
    frame = ttk.Frame(parent)
    frame.pack(fill='x', pady=(0, 12))
    buttons = [ttk.Button(frame, text=label, command=command) for label, command in actions]
    adaptive_grid(frame, buttons, minimum=190, maximum=3)
    return frame
