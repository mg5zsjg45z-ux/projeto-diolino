"""App-owned, antialiased card outlines; native child controls stay accessible."""
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
from theme import BG, SURFACE, LINE


def configure_button_artwork(controller, style):
    """Nine-slice images keep button corners crisp at each display scale."""
    cache = getattr(controller, '_button_artwork', {})
    controller._button_artwork = cache
    styles = getattr(controller, '_button_elements', {})
    controller._button_elements = styles
    size = max(32, round(32 * controller.dpi_scale))
    radius = max(6, round(8 * controller.dpi_scale))
    border = max(1, round(controller.dpi_scale))
    for name in ('TButton', 'Accent.TButton', 'Week.TButton', 'WeekSelected.TButton'):
        colors = []
        for state in ('disabled', 'pressed', 'active', 'focus', ''):
            states = (state,) if state else ()
            fill = style.lookup(name, 'background', states) or controller.palette['surface']
            outline = controller.palette['ink'] if state == 'focus' else (style.lookup(name, 'bordercolor', states) or controller.palette['line'])
            colors.append((state, fill, outline))
        signature = (name, size, radius, border, controller.palette['bg'], tuple(colors))
        element = styles.get(signature)
        images = []
        for state, fill, outline in (() if element else colors):
            artwork = Image.new('RGBA', (size * 3, size * 3), controller.palette['bg'])
            draw = ImageDraw.Draw(artwork)
            draw.rounded_rectangle((1, 1, size * 3 - 2, size * 3 - 2), radius=radius * 3,
                                   fill=fill, outline=outline,
                                   width=border * 3 * (2 if state == 'focus' else 1))
            artwork = artwork.resize((size, size), Image.Resampling.LANCZOS)
            images.append(ImageTk.PhotoImage(artwork, master=controller.root))
        if element is None:
            element = f'Diolino{len(cache)}.border'
            style.element_create(element, 'image', images[-1],
                                 *[((state,), image) for state, image in zip(('disabled', 'pressed', 'active', 'focus'), images)],
                                 border=radius+2, padding=0, sticky='nsew')
            cache[element] = images
            styles[signature] = element
        style.layout(name, [(element, {'sticky':'nsew', 'children':[
            ('Button.padding', {'sticky':'nsew', 'children':[
                ('Button.label', {'sticky':'nsew'})]})]})])


class RoundedSurface(tk.Canvas):
    def __init__(self, parent, padding=22, radius=12):
        super().__init__(parent, bg=BG, highlightthickness=0, borderwidth=0, height=100)
        self.padding, self.radius = padding, radius
        self.body = tk.Frame(self, bg=SURFACE)
        self.background_item = self.create_image(0, 0, anchor='nw')
        self.window_item = self.create_window(padding, padding, window=self.body, anchor='nw')
        self._surface_key = None
        self.bind('<Configure>', self.layout_surface)
        self.body.bind('<Configure>', self.layout_surface)

    def layout_surface(self, event=None):
        controller = getattr(self._root(), 'appearance', None)
        factor = controller.dpi_scale if controller else self.winfo_fpixels('1i') / 96
        density = .8 if controller and controller.preferences['density'] == 'compact' else 1
        pad = max(12, round(self.padding * factor * density))
        width = max(1, self.winfo_width())
        inner_width = max(1, width - 2 * pad)
        if int(float(self.itemcget(self.window_item, 'width'))) != inner_width:
            self.itemconfigure(self.window_item, width=inner_width)
        self.coords(self.window_item, pad, pad)
        height = self.body.winfo_reqheight() + 2 * pad
        if int(self.cget('height')) != height:
            self.configure(height=height)
        self.refresh_surface()

    def refresh_surface(self):
        controller = getattr(self._root(), 'appearance', None)
        palette = controller.palette if controller else dict(bg=BG, surface=SURFACE, line=LINE)
        factor = controller.dpi_scale if controller else self.winfo_fpixels('1i') / 96
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        radius = min(round(self.radius * factor), width // 2, height // 2)
        border = max(1, round(factor))
        engraved = not controller or (not controller.accessible_palette and controller.preferences['ornaments'] == 'crafted')
        key = (width, height, radius, border, engraved, palette['bg'], palette['surface'], palette['line'])
        if key == self._surface_key:
            return
        self._surface_key = key
        self.configure(background=palette['bg'])
        self.body.configure(background=palette['surface'])
        # Supersample only the small corner tile, keeping long forms inexpensive.
        side = max(2, radius + border)
        tile = Image.new('RGB', (side * 2 * 3, side * 2 * 3), palette['bg'])
        draw = ImageDraw.Draw(tile)
        draw.rounded_rectangle((0, 0, tile.width - 1, tile.height - 1),
                               radius=radius * 3, fill=palette['surface'],
                               outline=palette['line'], width=border * 3)
        tile = tile.resize((side * 2, side * 2), Image.Resampling.LANCZOS)
        image = Image.new('RGB', (width, height), palette['surface'])
        edges = ImageDraw.Draw(image)
        edges.rectangle((0, 0, width - 1, height - 1), outline=palette['line'], width=border)
        for left, top, box in [(0, 0, (0, 0, side, side)),
                               (width-side, 0, (side, 0, side*2, side)),
                               (0, height-side, (0, side, side, side*2)),
                               (width-side, height-side, (side, side, side*2, side*2))]:
            image.paste(tile.crop(box), (left, top))
        if engraved and width > 100 and height > 80:
            inset, length = round(8 * factor), round(17 * factor)
            # Open corner strokes recall a notebook frame without bordering text.
            edges.line([(inset, inset+length), (inset, inset), (inset+length, inset)],
                       fill=palette['line'], width=border)
            edges.line([(width-inset-length-1, height-inset-1),
                        (width-inset-1, height-inset-1), (width-inset-1, height-inset-length-1)],
                       fill=palette['line'], width=border)
        self._surface_image = ImageTk.PhotoImage(image, master=self)
        self.itemconfigure(self.background_item, image=self._surface_image)


def card_body(parent, **options):
    """Return the content frame; its master is the pack/grid-managed surface."""
    return RoundedSurface(parent, **options).body
