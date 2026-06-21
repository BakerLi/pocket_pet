"""Win32 / DWM / DPI helpers.

The whole point of this module is to give the rest of the app a clean,
*physical-pixel* view of the world:

* Where are the other top-level windows (so the pet can perch on their top
  edges)?  -> :func:`enum_top_level_windows`
* Where is the floor (taskbar-aware work area)?  -> :func:`primary_work_area`
* How do we position OUR window in that same physical-pixel space without
  fighting Qt's high-DPI scaling?  -> :func:`move_window_physical`

Coordinate model
----------------
Everything here is in **physical pixels** of the virtual desktop. We make the
process per-monitor-DPI-aware (:func:`set_dpi_awareness`, call it BEFORE
``QApplication``), then drive our window's position with ``SetWindowPos`` in
physical pixels — the exact same space ``GetWindowRect`` / DWM bounds report
for other windows. That sidesteps the messy Qt-logical <-> physical conversion
on mixed-DPI multi-monitor setups: we never convert when *positioning*; we only
convert when *painting inside* a Qt widget (divide by devicePixelRatio).
"""

from __future__ import annotations

import ctypes
import os
import winreg
from ctypes import wintypes

import win32api
import win32con
import win32event
import win32gui
import win32process
import winerror

# --- DWM attribute ids -----------------------------------------------------
DWMWA_EXTENDED_FRAME_BOUNDS = 9  # the *visual* rect, excluding Win10/11 invisible border
DWMWA_CLOAKED = 14              # nonzero => window is DWM-cloaked (a ghost; skip it)

_dwmapi = ctypes.WinDLL("dwmapi")


# --- DPI awareness ---------------------------------------------------------
def set_dpi_awareness() -> None:
    """Make this process per-monitor-v2 DPI aware. Call before QApplication.

    Falls back gracefully on older Windows. Without this, ``GetWindowRect``
    returns DPI-virtualized coordinates and the pet drifts on scaled displays.
    """
    user32 = ctypes.windll.user32
    # PER_MONITOR_AWARE_V2 context handle == -4
    try:
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError):
        pass
    try:  # Windows 8.1+: PROCESS_PER_MONITOR_DPI_AWARE == 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except (AttributeError, OSError):
        pass
    try:  # Vista+
        user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


# --- DWM queries -----------------------------------------------------------
def get_extended_frame_bounds(hwnd: int) -> tuple[int, int, int, int] | None:
    """Visual bounds (left, top, right, bottom) in physical px, or None on failure.

    Prefer this over ``GetWindowRect``: on Win10/11 ``GetWindowRect`` includes
    an invisible resize border (~7px), so the pet would appear to float beside
    or above the visible window edge.
    """
    rect = wintypes.RECT()
    res = _dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect),
        ctypes.sizeof(rect),
    )
    if res != 0:
        return None
    return (rect.left, rect.top, rect.right, rect.bottom)


def is_cloaked(hwnd: int) -> bool:
    """True if the window is DWM-cloaked (e.g. background UWP/store apps)."""
    val = wintypes.DWORD(0)
    res = _dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(DWMWA_CLOAKED),
        ctypes.byref(val),
        ctypes.sizeof(val),
    )
    return res == 0 and val.value != 0


# --- enumeration -----------------------------------------------------------
def enum_top_level_windows(skip_hwnds: set[int] | None = None) -> list[dict]:
    """Visible, non-minimized, non-cloaked, titled top-level windows.

    Returned **in z-order, topmost first** (EnumWindows guarantees this), so the
    first window covering a given point is the one actually visible there — which
    is exactly what we need to decide a valid perch platform.

    Each item: ``{"hwnd": int, "title": str, "rect": (l, t, r, b)}`` where rect
    is physical-pixel visual bounds.
    """
    skip = skip_hwnds or set()
    out: list[dict] = []

    def _cb(hwnd, _):
        if hwnd in skip:
            return True
        if not win32gui.IsWindowVisible(hwnd):
            return True
        if win32gui.IsIconic(hwnd):  # minimized
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        if is_cloaked(hwnd):
            return True
        # Skip pure tool windows (palettes etc.) — usually not perch targets.
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if ex_style & win32con.WS_EX_TOOLWINDOW:
            return True
        rect = get_extended_frame_bounds(hwnd) or win32gui.GetWindowRect(hwnd)
        l, t, r, b = rect
        if r - l <= 0 or b - t <= 0:
            return True
        out.append({"hwnd": hwnd, "title": title, "rect": rect})
        return True

    win32gui.EnumWindows(_cb, None)
    return out


_singleton_handle = None  # kept alive for the process lifetime once acquired


def acquire_single_instance(name: str = "PocketPet_SingleInstance") -> bool:
    """True if we're the first instance; False if another is already running.

    Uses a named mutex (per-session). On any failure we return True so a guard
    glitch never stops the pet from launching.
    """
    global _singleton_handle
    try:
        handle = win32event.CreateMutex(None, False, name)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            return False
        _singleton_handle = handle  # don't let it be GC'd / closed
        return True
    except Exception:
        return True


def active_window_info() -> dict | None:
    """The foreground window's ``{"hwnd", "title", "proc"}`` (proc = exe name,
    best-effort), or None if there's nothing useful to report.

    Used only by the opt-in "snark about what you're doing" feature; the caller
    is responsible for the privacy gate. Window titles can contain sensitive
    text, so nothing here is sent anywhere unless that feature is enabled.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return None
        proc = ""
        try:
            _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            h = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                False, pid,
            )
            try:
                proc = os.path.basename(win32process.GetModuleFileNameEx(h, 0))
            finally:
                win32api.CloseHandle(h)
        except Exception:
            proc = ""  # access denied (elevated app etc.) — title alone is fine
        return {"hwnd": hwnd, "title": title, "proc": proc}
    except Exception:
        return None


# --- screen geometry -------------------------------------------------------
def primary_screen_size() -> tuple[int, int]:
    """(width, height) of the primary monitor in physical px."""
    return (
        win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
        win32api.GetSystemMetrics(win32con.SM_CYSCREEN),
    )


def primary_work_area() -> tuple[int, int, int, int]:
    """Primary monitor work area (l, t, r, b) in physical px — excludes taskbar.

    The bottom of this rect is the pet's "floor" on the primary display.
    """
    info = win32api.GetMonitorInfo(
        win32api.MonitorFromPoint((0, 0), win32con.MONITOR_DEFAULTTOPRIMARY)
    )
    return info["Work"]


# --- positioning OUR window ------------------------------------------------
def move_window_physical(
    hwnd: int, x: float, y: float, w: int | None = None, h: int | None = None,
    topmost: bool = True,
) -> None:
    """Position a window in physical pixels, bypassing Qt's logical coords.

    Size is left untouched unless both ``w`` and ``h`` are given (let Qt own the
    size; we just move). ``topmost`` keeps the pet above normal windows.
    """
    insert_after = win32con.HWND_TOPMOST if topmost else win32con.HWND_NOTOPMOST
    flags = win32con.SWP_NOACTIVATE
    if w is None or h is None:
        flags |= win32con.SWP_NOSIZE
        w = h = 0
    win32gui.SetWindowPos(hwnd, insert_after, int(x), int(y), int(w), int(h), flags)


def device_id() -> str:
    """A stable per-machine+user identifier used to deterministically pick the
    pet's species (à la Claude's Buddy: same identity every time).

    Combines the Windows MachineGuid with the username. Falls back gracefully.
    """
    guid = "no-machine-guid"
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
    except OSError:
        pass
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return f"{user}@{guid}"


def set_click_through(hwnd: int, enabled: bool = True) -> None:
    """Add/remove WS_EX_TRANSPARENT so mouse clicks pass through the window.

    Needed only for a *full-screen* overlay (see spike_windows). The normal
    per-pet small window does NOT use this — it wants to receive its own clicks.
    """
    ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    ex |= win32con.WS_EX_LAYERED
    if enabled:
        ex |= win32con.WS_EX_TRANSPARENT
    else:
        ex &= ~win32con.WS_EX_TRANSPARENT
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)
