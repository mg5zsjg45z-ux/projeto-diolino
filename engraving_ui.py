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
        self.configure(background=palette['bg'])
        self.delete('all')
        width = max(30, self.winfo_width())
        self.create_line(0, 8, width, 8, fill=palette['line'])
        if controller and (controller.accessible_palette or controller.preferences['ornaments'] == 'plain'):
            return
        self.create_line(0, 5, 30, 5, 52, 6, 76, 5, smooth=True,
                         fill=palette['ink'], width=1, splinesteps=24)
        self.create_polygon(82, 4, 86, 8, 82, 12, 78, 8,
                            fill=palette['bg'], outline=palette['ink'])
        self.create_line(90, 11, 116, 11, fill=palette['line'])


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
