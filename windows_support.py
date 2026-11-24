"""Native Windows notification-area icon and single-instance signal.

Uses the user's existing Windows notification settings; does not change them.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import os
import queue
import threading


class SingleInstance:
    def __init__(self, directory):
        self.owned = True
        self.mutex = self.event = None
        if os.name != 'nt':
            return
        kernel = C.WinDLL('kernel32', use_last_error=True)
        self.kernel = kernel
        kernel.CreateMutexW.argtypes = [C.c_void_p, W.BOOL, W.LPCWSTR]
        kernel.CreateMutexW.restype = W.HANDLE
        kernel.CreateEventW.argtypes = [C.c_void_p, W.BOOL, W.BOOL, W.LPCWSTR]
        kernel.CreateEventW.restype = W.HANDLE
        kernel.SetEvent.argtypes = [W.HANDLE]
        kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
        kernel.CloseHandle.argtypes = [W.HANDLE]
        name = 'Local\\Diolino-' + hashlib.sha256(str(directory.resolve()).casefold().encode()).hexdigest()[:24]
        self.mutex = kernel.CreateMutexW(None, False, name)
        if not self.mutex:
            raise OSError(C.get_last_error(), 'Não foi possível proteger a instância do aplicativo.')
        self.owned = C.get_last_error() != 183
        self.event = kernel.CreateEventW(None, False, False, name + '-show')
        if not self.owned:
            kernel.SetEvent(self.event)

    def requested(self):
        return bool(self.event and self.kernel.WaitForSingleObject(self.event, 0) == 0)

    def close(self):
        for handle in (self.event, self.mutex):
            if handle:
                self.kernel.CloseHandle(handle)


class Tray:
    def __init__(self):
        self.events = queue.Queue()
        self.ready = threading.Event()
        self.available = False
        self.hwnd = None
        if os.name == 'nt':
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            self.ready.wait(3)

    def run(self):
        try:
            self.user = u = C.WinDLL('user32', use_last_error=True)
            self.shell = s = C.WinDLL('shell32', use_last_error=True)
            kernel = C.WinDLL('kernel32', use_last_error=True)
            LRESULT = C.c_ssize_t
            CALLBACK = C.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
            class WNDCLASS(C.Structure):
                _fields_ = [('style', W.UINT), ('proc', CALLBACK), ('cls', C.c_int), ('win', C.c_int),
                            ('instance', W.HINSTANCE), ('icon', W.HICON), ('cursor', W.HANDLE),
                            ('brush', W.HBRUSH), ('menu', W.LPCWSTR), ('name', W.LPCWSTR)]
            class NID(C.Structure):
                _fields_ = [('cbSize', W.DWORD), ('hWnd', W.HWND), ('uID', W.UINT), ('uFlags', W.UINT),
                            ('uCallbackMessage', W.UINT), ('hIcon', W.HICON), ('szTip', W.WCHAR * 128),
                            ('dwState', W.DWORD), ('dwStateMask', W.DWORD), ('szInfo', W.WCHAR * 256),
                            ('uTimeout', W.UINT), ('szInfoTitle', W.WCHAR * 64), ('dwInfoFlags', W.DWORD),
                            ('guidItem', C.c_byte * 16), ('hBalloonIcon', W.HICON)]
            self.NID = NID
            kernel.GetModuleHandleW.argtypes = [W.LPCWSTR]
            kernel.GetModuleHandleW.restype = W.HMODULE
            u.RegisterClassW.argtypes = [C.POINTER(WNDCLASS)]
            u.CreateWindowExW.argtypes = [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, C.c_int, C.c_int, C.c_int, C.c_int, W.HWND, W.HMENU, W.HINSTANCE, C.c_void_p]
            u.CreateWindowExW.restype = W.HWND
            u.DefWindowProcW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
            u.DefWindowProcW.restype = LRESULT
            u.LoadIconW.argtypes = [W.HINSTANCE, C.c_void_p]
            u.LoadIconW.restype = W.HICON
            u.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
            u.DestroyWindow.argtypes = [W.HWND]
            u.CreatePopupMenu.restype = W.HMENU
            u.AppendMenuW.argtypes = [W.HMENU, W.UINT, C.c_size_t, W.LPCWSTR]
            u.TrackPopupMenu.argtypes = [W.HMENU, W.UINT, C.c_int, C.c_int, C.c_int, W.HWND, C.c_void_p]
            u.SetForegroundWindow.argtypes = [W.HWND]
            u.DestroyMenu.argtypes = [W.HMENU]
            u.GetMessageW.argtypes = [C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT]
            u.DispatchMessageW.argtypes = [C.POINTER(W.MSG)]
            u.DispatchMessageW.restype = LRESULT
            s.Shell_NotifyIconW.argtypes = [W.DWORD, C.POINTER(NID)]
            s.Shell_NotifyIconW.restype = W.BOOL
            taskbar_created = u.RegisterWindowMessageW('TaskbarCreated')
            def callback(hwnd, message, wp, lp):
                if message == taskbar_created and self.available:
                    s.Shell_NotifyIconW(0, C.byref(self.data))
                    return 0
                if message == 0x8001:
                    event = lp & 0xffff
                    if event in (0x202, 0x203, 0x405):
                        self.events.put('show')
                    elif event == 0x205:
                        menu = u.CreatePopupMenu()
                        u.AppendMenuW(menu, 0, 1, 'Abrir Diolino')
                        u.AppendMenuW(menu, 0, 2, 'Sair completamente')
                        point = W.POINT()
                        u.GetCursorPos(C.byref(point))
                        u.SetForegroundWindow(hwnd)
                        command = u.TrackPopupMenu(menu, 0x102, point.x, point.y, 0, hwnd, None)
                        u.DestroyMenu(menu)
                        if command in (1, 2):
                            self.events.put('show' if command == 1 else 'exit')
                    return 0
                if message == 0x10:
                    u.DestroyWindow(hwnd)
                    return 0
                if message == 0x2:
                    s.Shell_NotifyIconW(2, C.byref(self.data))
                    u.PostQuitMessage(0)
                    return 0
                return u.DefWindowProcW(hwnd, message, wp, lp)
            self.callback = CALLBACK(callback)
            instance = kernel.GetModuleHandleW(None)
            classname = f'DiolinoTray{os.getpid()}'
            wc = WNDCLASS()
            wc.proc, wc.instance, wc.name = self.callback, instance, classname
            if not u.RegisterClassW(C.byref(wc)):
                raise OSError('Registro da bandeja falhou.')
            self.hwnd = u.CreateWindowExW(0, classname, '', 0, 0, 0, 0, 0, None, None, instance, None)
            if not self.hwnd:
                raise OSError('Janela da bandeja indisponível.')
            self.data = NID()
            self.data.cbSize = C.sizeof(NID)
            self.data.hWnd, self.data.uID = self.hwnd, 1
            self.data.uFlags, self.data.uCallbackMessage = 1 | 2 | 4, 0x8001
            self.data.hIcon = u.LoadIconW(None, C.c_void_p(32512))
            self.data.szTip = 'Diolino — agenda e lembretes'
            self.available = bool(s.Shell_NotifyIconW(0, C.byref(self.data)))
            self.ready.set()
            msg = W.MSG()
            while u.GetMessageW(C.byref(msg), None, 0, 0) > 0:
                u.TranslateMessage(C.byref(msg))
                u.DispatchMessageW(C.byref(msg))
        except Exception:
            import logging
            logging.exception('Bandeja do Windows indisponível')
            self.ready.set()

    def notify(self, title, text):
        if not self.available:
            return False
        info = self.NID()
        info.cbSize, info.hWnd, info.uID = C.sizeof(info), self.hwnd, 1
        info.uFlags = 0x10
        info.szInfoTitle, info.szInfo = title[:63], text[:255]
        info.dwInfoFlags, info.uTimeout = 1, 15000
        return bool(self.shell.Shell_NotifyIconW(1, C.byref(info)))

    def close(self):
        if self.hwnd:
            self.user.PostMessageW(self.hwnd, 0x10, 0, 0)
            self.thread.join(timeout=2)
