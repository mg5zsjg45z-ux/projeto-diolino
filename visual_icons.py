"""Locally bundled Lucide outlines, tinted for every theme and display scale."""
from functools import lru_cache
from pathlib import Path
import tkinter as tk
from PIL import Image, ImageTk

ICONS = dict(notebook='notebook-pen', home='house', checklist='list-checks', planning='notebook-pen',
             health_overview='heart-pulse', training='dumbbell', studies='book-open',
             bible_library='book-open-text', agenda='calendar-days', data='database',
             printing='printer', appearance='palette')
DIRECTORY = Path(__file__).resolve().parent / 'assets/visual/lucide'


@lru_cache(maxsize=128)
def mask(name, size):
    with Image.open(DIRECTORY / (name + '.png')) as image:
        return image.getchannel('A').resize((size, size), Image.Resampling.LANCZOS)


class OutlineIcon(tk.Label):
    def __init__(self, parent, name, size=22, **options):
        super().__init__(parent, **options)
        self.icon_name, self.icon_size, self.icon_signature = name, size, None
        self.refresh_icon()

    def refresh_icon(self):
        controller = getattr(self._root(), 'appearance', None)
        factor = controller.dpi_scale * controller.scale if controller else self.winfo_fpixels('1i') / 96
        size = max(12, round(self.icon_size * factor))
        color = self.cget('foreground')
        signature = (self.icon_name, size, color)
        if signature == self.icon_signature:
            return
        self.icon_signature = signature
        image = Image.new('RGBA', (size, size), color)
        image.putalpha(mask(self.icon_name, size))
        self.icon_image = ImageTk.PhotoImage(image, master=self)
        self.configure(image=self.icon_image)
