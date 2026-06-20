"""A poop the pet leaves behind. Clean it by clicking it.

Like the pet, it's a small transparent top-level window driven in physical
pixels. It reuses the core physics step so it rests on the desktop floor OR a
window's top edge, and **falls when that window moves or closes** — it never
gets stranded mid-air. Left-clicking it cleans it up.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

from ..config import DT, POOP_SIZE
from ..core.physics import Body, step
from ..platform import winapi


class PoopWindow(QWidget):
    def __init__(self, world, x: float, y: float):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.world = world
        self.body = Body(x=x, y=y, width=POOP_SIZE, height=POOP_SIZE)

        dpr = QGuiApplication.primaryScreen().devicePixelRatio() or 1.0
        logical = max(1, round(POOP_SIZE / dpr))
        self.resize(logical, logical)
        self._font = QFont("Segoe UI Emoji", int(logical * 0.7))

        self.hwnd = int(self.winId())
        self.show()
        winapi.move_window_physical(self.hwnd, self.body.x, self.body.y)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(int(1000 * DT))

    def _tick(self) -> None:
        # Fall / rest on the floor or a window top; drop if that window leaves.
        step(self.body, self.world.bounds, DT, self.world.platforms)
        winapi.move_window_physical(self.hwnd, self.body.x, self.body.y)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self.world.clean_poop(self)  # click to clean

    def shutdown(self) -> None:
        self.timer.stop()
        self.close()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self._font)
        p.drawText(self.rect(), Qt.AlignCenter, "💩")
