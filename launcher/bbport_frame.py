# SPDX-License-Identifier: GPL-2.0-or-later
"""The launcher's own title bar instead of Windows' caption, on a normal Windows window.

The window keeps its native frame, so moving, Aero Snap, the snap keys, resizing, the shadow, the
taskbar and Alt+Tab stay Windows' own. Only the caption goes: the window answers WM_NCCALCSIZE with
the client area reaching the window's top. The launcher draws the bar (Launcher.build_titlebar) and
the window tells Windows where it is (WM_NCHITTEST): HTCAPTION over the bar, HTTOP… over its top
edge, so Windows itself moves the window (with Snap), maximizes it on a double click, shows the
window menu on a right click and resizes it. The windows Tk puts over that area (its client window
and the bar) answer HTTRANSPARENT there, so Windows asks the frame window.

No Windows loop is ever started from a Tk callback: inside one, a Tk event handler would re-enter
Python without its thread state (tkinter), which ends the process.

When anything here fails, install() returns False and the launcher keeps Windows' caption."""
import ctypes
from ctypes import wintypes

WM_NCCALCSIZE, WM_NCHITTEST, WM_NCRBUTTONUP, WM_SYSCOMMAND = 0x0083, 0x0084, 0x00A5, 0x0112
SC_SIZE, SC_MOVE, SC_MAXIMIZE, SC_RESTORE = 0xF000, 0xF010, 0xF030, 0xF120
TPM_RETURNCMD = 0x0100
HTTRANSPARENT, HTCLIENT, HTCAPTION, HTTOP, HTTOPLEFT, HTTOPRIGHT = -1, 1, 2, 12, 13, 14
GWLP_WNDPROC = -4
SWP_FRAMECHANGED = 0x0001 | 0x0002 | 0x0004 | 0x0020  # no size, no move, no z-order, frame changed
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t)


class NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [('rgrc', wintypes.RECT * 3), ('lppos', ctypes.c_void_p)]


def _user32():
    user32 = ctypes.windll.user32
    user32.SetWindowLongPtrW.restype = ctypes.c_void_p
    user32.SetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_void_p)
    user32.CallWindowProcW.restype = ctypes.c_ssize_t
    user32.CallWindowProcW.argtypes = (ctypes.c_void_p, wintypes.HWND, wintypes.UINT, ctypes.c_size_t,
                                       ctypes.c_ssize_t)
    user32.GetSystemMenu.restype = wintypes.HMENU
    user32.TrackPopupMenu.argtypes = (wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                      wintypes.HWND, ctypes.c_void_p)
    user32.EnableMenuItem.argtypes = (wintypes.HMENU, wintypes.UINT, wintypes.UINT)
    user32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t)
    return user32


class Frame:
    """The caption removed from one window. `hwnd` is its frame (Tk's wrapper, root.wm_frame());
    `covers` the windows Tk puts over the bar (the toplevel's client window, the bar)."""

    def __init__(self, hwnd, covers):
        self.hwnd, self.covers = hwnd, list(covers)
        self.user32 = _user32()
        self.procs, self.olds = {}, {}
        self.bar, self.buttons, self.edge, self.corner = 32, 138, 5, 10  # physical pixels, set by the launcher

    def thickness(self):
        """The resize frame Windows keeps off screen around a maximized window."""
        u = self.user32
        try:
            dpi = u.GetDpiForWindow(self.hwnd)
            return u.GetSystemMetricsForDpi(33, dpi) + u.GetSystemMetricsForDpi(92, dpi)  # SM_CYSIZEFRAME, PADDEDBORDER
        except AttributeError:  # before Windows 10 1607
            return u.GetSystemMetrics(33) + u.GetSystemMetrics(92)

    def hit(self, lparam):
        """What a screen point (WM_NCHITTEST's lParam) is on: HTCAPTION, HTTOP…, or HTCLIENT."""
        u = self.user32
        x, y = ctypes.c_short(lparam & 0xFFFF).value, ctypes.c_short((lparam >> 16) & 0xFFFF).value
        origin = wintypes.POINT(0, 0)
        u.ClientToScreen(self.hwnd, ctypes.byref(origin))
        rect = wintypes.RECT()
        u.GetClientRect(self.hwnd, ctypes.byref(rect))
        rx, ry, width = x - origin.x, y - origin.y, rect.right
        if not 0 <= ry < self.bar or not 0 <= rx < width:
            return HTCLIENT
        if ry < self.edge and not u.IsZoomed(self.hwnd):
            return HTTOPLEFT if rx < self.corner else HTTOPRIGHT if rx >= width - self.corner else HTTOP
        return HTCAPTION if rx < width - self.buttons else HTCLIENT

    def wndproc(self, hwnd, msg, wparam, lparam):
        u, old = self.user32, self.olds.get(hwnd)
        try:
            if hwnd == self.hwnd:
                if msg == WM_NCCALCSIZE and wparam:
                    params = NCCALCSIZE_PARAMS.from_address(lparam)
                    top = params.rgrc[0].top
                    result = u.CallWindowProcW(old, hwnd, msg, wparam, lparam)  # the sides and the bottom
                    params.rgrc[0].top = top + (self.thickness() if u.IsZoomed(hwnd) else 0)  # no caption
                    return result
                if msg == WM_NCHITTEST:
                    result = u.CallWindowProcW(old, hwnd, msg, wparam, lparam)
                    return self.hit(lparam) if result == HTCLIENT else result
                if msg == WM_NCRBUTTONUP and wparam == HTCAPTION:  # Tk does not pass it on to Windows
                    self.window_menu(ctypes.c_short(lparam & 0xFFFF).value, ctypes.c_short((lparam >> 16) & 0xFFFF).value)
                    return 0
            elif msg == WM_NCHITTEST and self.hit(lparam) != HTCLIENT:
                return HTTRANSPARENT  # Tk's window over the bar: let the frame window answer
        except Exception:  # never leave a message unanswered
            pass
        return u.CallWindowProcW(old, hwnd, msg, wparam, lparam)

    def window_menu(self, x, y):
        """The window's menu at a screen point, its items as the state allows (from the window
        procedure, never from a Tk callback)."""
        u = self.user32
        menu = u.GetSystemMenu(self.hwnd, False)
        if not menu:
            return
        zoomed = bool(u.IsZoomed(self.hwnd))
        for item, on in ((SC_RESTORE, zoomed), (SC_MAXIMIZE, not zoomed), (SC_MOVE, not zoomed),
                         (SC_SIZE, not zoomed)):
            u.EnableMenuItem(menu, item, 0 if on else 1)  # MF_BYCOMMAND | MF_ENABLED or MF_GRAYED
        command = u.TrackPopupMenu(menu, TPM_RETURNCMD, x, y, 0, self.hwnd, None)
        if command:
            u.PostMessageW(self.hwnd, WM_SYSCOMMAND, command, 0)

    def install(self):
        try:
            for hwnd in [self.hwnd] + self.covers:
                proc = WNDPROC(self.wndproc)  # kept: Windows calls it for as long as the window lives
                old = self.user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, ctypes.cast(proc, ctypes.c_void_p))
                if not old:
                    self.uninstall()
                    return False
                self.procs[hwnd], self.olds[hwnd] = proc, old
            self.user32.SetWindowPos(self.hwnd, 0, 0, 0, 0, 0, SWP_FRAMECHANGED)
            return True
        except (AttributeError, OSError, ValueError):
            self.uninstall()
            return False

    def uninstall(self):
        """Tk's own window procedures back (after a failed install)."""
        for hwnd, old in list(self.olds.items()):
            try:
                self.user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, old)
            except (OSError, ValueError):
                pass
        self.olds.clear()
