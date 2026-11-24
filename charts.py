"""Small offline charts with actual dates, units and hover values."""
import tkinter as tk
from datetime import date
from theme import INK, MUTED, LINE, SURFACE
from appearance import refresh_widget


def chart(parent, title, points, start, end, unit, color=INK, bars=False, height=240, fixed_max=None):
    canvas = tk.Canvas(parent, background=SURFACE, highlightbackground=LINE, highlightthickness=1, height=height)
    points = sorted((day, value) for day, value in points if value is not None)
    def draw(_=None):
        canvas.delete('all')
        width = max(canvas.winfo_width(), 320)
        left, right, top, bottom = 65, width - 25, 50, height - 44
        canvas.create_text(22, 25, anchor='w', text=title, fill=INK, font=('Segoe UI Semibold', 11))
        if not points:
            canvas.create_text(width / 2, height / 2, text='Sem registros neste período', fill=MUTED, font=('Segoe UI', 11))
            refresh_widget(canvas)
            return
        vals = [p[1] for p in points]
        pad = max((max(vals) - min(vals)) * .15, .5)
        low = 0 if bars else min(vals) - pad
        high = fixed_max if fixed_max is not None else max(vals) + pad
        if high <= low:
            high = low + 1
        span = max((end - start).days, 1)
        for i in range(4):
            y = top + i / 3 * (bottom - top)
            v = high - i / 3 * (high - low)
            canvas.create_line(left, y, right, y, fill='#eeeeee')
            canvas.create_text(left - 8, y, text=f'{v:.1f}'.replace('.', ','), anchor='e', fill=MUTED, font=('Segoe UI', 9))
        coords = []
        for day, value in points:
            x = left + (date.fromisoformat(day) - start).days / span * (right - left)
            y = bottom - (value - low) / (high - low) * (bottom - top)
            coords.extend((x, y))
        if not bars and len(coords) > 2:
            canvas.create_line(*coords, fill=color, width=2)
        for (day, value), x, y in zip(points, coords[::2], coords[1::2]):
            if bars:
                half = min(14, max(2, (right - left) / (span + 1) / 3))
                item = canvas.create_rectangle(x - half, min(y, bottom - 2), x + half, bottom, fill=color, outline='')
            else:
                item = canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline='white')
            text = f'{date.fromisoformat(day):%d/%m/%Y} · {value:g} {unit}'
            canvas.tag_bind(item, '<Enter>', lambda e, t=text: show_tip(t))
            canvas.tag_bind(item, '<Leave>', lambda e: canvas.delete('tip'))
        canvas.create_text(left, height - 22, text=start.strftime('%d/%m/%Y'), anchor='w', fill=MUTED)
        canvas.create_text(right, height - 22, text=end.strftime('%d/%m/%Y'), anchor='e', fill=MUTED)
        refresh_widget(canvas)
    def show_tip(text):
        canvas.delete('tip')
        canvas.create_rectangle(65, height - 40, max(canvas.winfo_width() - 25, 300), height - 3, fill='white', outline='', tags='tip')
        canvas.create_text(75, height - 20, text=text, anchor='w', fill=INK, tags='tip')
        refresh_widget(canvas)
    canvas.bind('<Configure>', draw)
    return canvas
