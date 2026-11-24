"""Read Windows accessibility colors without changing system preferences."""
import ctypes
import os
from ctypes import wintypes


def high_contrast_palette():
    if os.name != 'nt':
        return None
    class HighContrast(ctypes.Structure):
        _fields_ = [('size', wintypes.UINT), ('flags', wintypes.DWORD),
                    ('scheme', wintypes.LPWSTR)]
    info = HighContrast()
    info.size = ctypes.sizeof(info)
    user = ctypes.windll.user32
    if not user.SystemParametersInfoW(0x0042, info.size, ctypes.byref(info), 0) or not info.flags & 1:
        return None
    def color(index):
        value = user.GetSysColor(index)
        return '#%02x%02x%02x' % (value & 255, (value >> 8) & 255, (value >> 16) & 255)
    bg, ink = color(5), color(8)
    return dict(bg=bg, surface=bg, ink=ink, muted=ink, line=ink, soft=bg,
                nav=ink, nav_text=bg, accent=ink, shadow=bg)
