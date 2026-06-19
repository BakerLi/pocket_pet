"""Spike B — detect other windows' top edges and draw them (the perch platforms).

Run:
    .venv/Scripts/python.exe spikes/spike_windows.py

What it proves
--------------
* ``enum_top_level_windows`` returns real, visible windows in z-order, with their
  *visual* bounds (DWM extended frame bounds, not the inflated GetWindowRect).
* A full-screen, CLICK-THROUGH overlay (WS_EX_TRANSPARENT) can draw a marker on
  each window's TOP edge — that edge is the platform the pet will perch on.
* If the red lines sit exactly on the visible top edge of each window (and move
  when you drag windows around), perching is geometrically feasible.

The overlay refreshes ~3x/sec. Press Esc to quit. Single primary monitor is
assumed for this spike (multi-monitor is a Phase-3 follow-up).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Window titles may contain chars the console codepage (e.g. cp950) can't encode.
# Don't let a debug print crash the spike.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pocket_pet.platform import winapi  # noqa: E402

winapi.set_dpi_awareness()

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QColor, QFont, QPainter, QPen  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402


class DebugOverlay(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.screen_w, self.screen_h = winapi.primary_screen_size()
        self.dpr = self.devicePixelRatioF() or 1.0
        # Size the overlay to cover the primary monitor (logical px for Qt).
        self.resize(round(self.screen_w / self.dpr), round(self.screen_h / self.dpr))

        self.hwnd = int(self.winId())
        self.windows: list[dict] = []

        self.show()  # need a realized HWND before SetWindowPos / style change
        winapi.move_window_physical(self.hwnd, 0, 0)
        winapi.set_click_through(self.hwnd, True)  # let clicks fall through to real windows

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(333)
        self._refresh()

    def _refresh(self):
        # Skip our own overlay so we don't draw a line across the whole screen.
        self.windows = winapi.enum_top_level_windows(skip_hwnds={self.hwnd})
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(QFont("Segoe UI", 8))

        for i, win in enumerate(self.windows):
            l, t, r, b = win["rect"]
            # physical -> Qt logical (overlay origin is screen (0,0))
            lx, ly, rx = l / self.dpr, t / self.dpr, r / self.dpr

            pen = QPen(QColor(255, 60, 60, 230))
            pen.setWidth(3)
            p.setPen(pen)
            p.drawLine(int(lx), int(ly), int(rx), int(ly))  # the perch platform

            label = f"[z{i}] {win['title'][:48]}"
            tx, ty = int(lx) + 4, int(ly) + 16
            p.fillRect(tx - 3, ty - 13, p.fontMetrics().horizontalAdvance(label) + 6, 17,
                       QColor(0, 0, 0, 150))
            p.setPen(QColor(255, 255, 255))
            p.drawText(tx, ty, label)

        # HUD
        hud = f"Spike B — {len(self.windows)} perch-able windows (dpr={self.dpr:.2f}). Esc to quit."
        p.fillRect(8, 8, p.fontMetrics().horizontalAdvance(hud) + 12, 22, QColor(0, 0, 0, 180))
        p.setPen(QColor(120, 255, 120))
        p.drawText(14, 23, hud)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            QApplication.quit()


def main():
    app = QApplication(sys.argv)
    overlay = DebugOverlay()  # noqa: F841
    # Also dump the detection to the console for a headless-style sanity check.
    wins = winapi.enum_top_level_windows(skip_hwnds={overlay.hwnd})
    print("=" * 70)
    print(f"Detected {len(wins)} perch-able windows (z-order, topmost first):")
    for i, w in enumerate(wins):
        l, t, r, b = w["rect"]
        print(f"  [z{i:2}] top-edge y={t:5} x=[{l:5}..{r:5}]  {w['title'][:50]}")
    print("Red lines on screen = top edge each window. Drag a window to watch it move.")
    print("Press Esc on the overlay to quit.")
    print("=" * 70)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
