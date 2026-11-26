"""Shared monochrome palette for the desktop interface."""
VERSION = '2.0.0'
BG = '#f4f7f6'
SURFACE = '#ffffff'
INK = '#182c29'
MUTED = '#526561'
LINE = '#d9e3e0'
SOFT = '#e9f2ef'
NAV = '#183a35'
NAV_TEXT = '#d0e4df'
ACCENT = '#17685a'
TITLE_FONT = ('Segoe UI Semibold', 25)
BODY_FONT = ('Segoe UI', 10)

SPACE_SCALE = (4, 8, 12, 16, 24, 32)
RADIUS_SCALE = (8, 12, 16)
TEXT_SCALE = {'standard': 1, 'medium': 1.1, 'large': 1.25}
DENSITY_SCALE = {'comfortable': 1, 'compact': .8}
TYPE_SCALE = {
    'body': BODY_FONT,
    'label': ('Segoe UI Semibold', 10),
    'section': ('Segoe UI Semibold', 13),
    'title': TITLE_FONT,
    'metric': ('Segoe UI Semibold', 20),
}

def blend(base, tint, amount):
    channels = (round(int(base[i:i+2], 16) * (1 - amount)
                      + int(tint[i:i+2], 16) * amount) for i in (1, 3, 5))
    return '#%02x%02x%02x' % tuple(channels)
