"""Spike A — transparent, always-on-top per-pet window + gravity, in physical px.

Run:
    .venv/Scripts/python.exe spikes/spike_overlay.py

What it proves
--------------
* A frameless, translucent, top-most ``Qt.Tool`` window renders a sprite with no
  background and no taskbar entry.
* Driving position with ``SetWindowPos`` in PHYSICAL pixels keeps the pet exactly
  where the physics says, regardless of display scaling. The window title bar
  (printed to console) shows Qt's logical geometry vs the physical rect so you
  can see the DPI factor and confirm they agree.
* Gravity + floor (taskbar-aware) + wall bounce.
* The "small window = the sprite" approach: only the pet's box intercepts the
  mouse. Try clicking desktop icons / other windows AROUND the pet — they work
  normally. Click the pet -> console logs it. Right-click the pet -> quit.

This is a throwaway spike; production code will live under src/pocket_pet/.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Window titles may contain chars the console codepage (e.g. cp950) can't encode.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

# Allow running straight from the repo without installing.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pocket_pet.platform import winapi  # noqa: E402

# DPI awareness MUST be set before QApplication is constructed.
winapi.set_dpi_awareness()

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QColor, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

SIZE_PX = 96          # sprite box, physical pixels
GRAVITY = 2000.0      # px / s^2
WALK_SPEED = 180.0    # px / s
BOUNCE = 0.55         # vertical velocity retained on floor hit
REST_VY = 90.0        # below this |vy| at the floor, the pet stops bouncing


class Pet(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.screen_w, self.screen_h = winapi.primary_screen_size()
        self.floor = winapi.primary_work_area()[3]  # work-area bottom (above taskbar)

        # Physics state, all in physical px.
        self.x = self.screen_w * 0.4
        self.y = 80.0
        self.vx = WALK_SPEED
        self.vy = 0.0
        self.on_ground = False
        self._reported = False

        # Qt owns the size in logical px; we only ever *move* via Win32.
        dpr = self.devicePixelRatioF() or 1.0
        logical = max(1, round(SIZE_PX / dpr))
        self.resize(logical, logical)

        self.hwnd = int(self.winId())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)  # ~60 fps
        self.dt = 0.016

    # --- physics ---------------------------------------------------------
    def _tick(self):
        if not self.on_ground:
            self.vy += GRAVITY * self.dt
        self.x += self.vx * self.dt
        self.y += self.vy * self.dt

        # Walls.
        if self.x <= 0:
            self.x = 0
            self.vx = abs(self.vx)
        elif self.x + SIZE_PX >= self.screen_w:
            self.x = self.screen_w - SIZE_PX
            self.vx = -abs(self.vx)

        # Floor.
        floor_y = self.floor - SIZE_PX
        if self.y >= floor_y:
            self.y = floor_y
            if self.vy > REST_VY:
                self.vy = -self.vy * BOUNCE  # bounce
                self.on_ground = False
            else:
                self.vy = 0.0
                self.on_ground = True
        else:
            self.on_ground = False

        winapi.move_window_physical(self.hwnd, self.x, self.y)
        self._report_once()

    def _report_once(self):
        """Print Qt-logical vs physical geometry once it settles — DPI sanity check."""
        if self._reported or not self.on_ground:
            return
        self._reported = True
        import win32gui

        l, t, r, b = win32gui.GetWindowRect(self.hwnd)
        g = self.geometry()
        print(
            "[DPI check] devicePixelRatio=%.3f | physics(px)=(%.0f,%.0f) "
            "| Win32 GetWindowRect=(%d,%d,%d,%d) size=%dx%d "
            "| Qt logical geometry=%dx%d @ (%d,%d)"
            % (
                self.devicePixelRatioF(), self.x, self.y,
                l, t, r, b, r - l, b - t,
                g.width(), g.height(), g.x(), g.y(),
            )
        )
        print("[DPI check] Win32 size should be ~%dx%d physical px." % (SIZE_PX, SIZE_PX))

    # --- drawing ---------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        # body
        p.setBrush(QColor(120, 200, 255))
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, w - 4, h - 4)
        # eyes (look in walking direction)
        p.setBrush(QColor(30, 30, 40))
        ox = 4 if self.vx >= 0 else -4
        p.drawEllipse(int(w * 0.32) + ox, int(h * 0.36), max(3, w // 10), max(3, h // 10))
        p.drawEllipse(int(w * 0.56) + ox, int(h * 0.36), max(3, w // 10), max(3, h // 10))

    # --- interaction -----------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            print("[interaction] right-click -> quit")
            QApplication.quit()
            return
        print("[interaction] pet clicked at global", e.globalPosition().toPoint())
        # little hop
        self.vy = -700.0
        self.on_ground = False


def main():
    app = QApplication(sys.argv)
    pet = Pet()
    pet.show()
    print("=" * 70)
    print("Spike A running. The pet bounces along the floor (above the taskbar).")
    print("  * Click the pet      -> it hops + logs the event")
    print("  * Right-click the pet-> quit")
    print("  * Click around it    -> desktop/other windows still work (click-through")
    print("    is automatic because the window is only the size of the sprite).")
    print("=" * 70)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
