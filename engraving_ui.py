"""Small engraved-paper accents drawn by the app, with no system visual effects."""
import tkinter as tk
from theme import BG, INK, LINE, SURFACE


class EngravedRule(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, height=18, bg=BG, highlightthickness=0)
        self.bind('<Configure>', lambda event: self.refresh_surface())

    def refresh_surface(self):
        controller = getattr(self._root(), 'appearance', None)
        palette = controller.palette if controller else dict(bg=BG, ink=INK, line=LINE)
        dpi = controller.dpi_scale if controller else self.winfo_fpixels('1i') / 96
        density = controller.density_scale if controller else 1
        height = max(1, round(16 * dpi * density))
        if int(self.cget('height')) != height:
            self.configure(height=height)
        self.configure(background=palette['bg'])
        self.delete('all')
        width = self.winfo_width()
        center = height // 2
        stroke = max(1, round(dpi))
        self.create_line(0, center, width, center, fill=palette['line'], width=stroke)
        if controller and (controller.accessible_palette or controller.preferences['ornaments'] == 'plain'):
            return
        if width >= 96 * dpi:
            x, radius = round(28 * dpi), round(3 * dpi)
            self.create_polygon(x-radius, center, x, center-radius, x+radius, center,
                                x, center+radius, fill=palette['ink'])


class Monogram(tk.Canvas):
    def __init__(self, parent, background, foreground):
        super().__init__(parent, width=44, height=44, bg=background, highlightthickness=0)
        self.create_oval(3, 3, 41, 41, outline=foreground, width=1)
        self.create_arc(6, 6, 38, 38, start=35, extent=280, style='arc', outline=foreground)
        self.create_text(22, 21, text='D', font=('Georgia', 19), fill=foreground)
        self.create_line(19, 35, 25, 35, fill=foreground)

    def refresh_surface(self):
        controller = getattr(self._root(), 'appearance', None)
        hidden = controller and (controller.accessible_palette or controller.preferences['ornaments'] == 'plain')
        self.configure(height=1 if hidden else 44)
        self.itemconfigure('all', state='hidden' if hidden else 'normal')
