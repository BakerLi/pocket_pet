"""A small transparent speech bubble that floats above a pet for a few seconds.

It's a separate top-level window (the pet's own window is only sprite-sized) and
is click-through so it never steals interaction. Positioned in physical pixels,
like the pet, via Win32.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QPainter,
    QPen,
    QPolygon,
)
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget

from ..platform import winapi

_PAD = 10
_TAIL = 7
_MAX_W = 300  # logical px; longer lines wrap onto multiple rows


class SpeechBubble(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._text = ""
        self._font = QFont("Segoe UI", 9)
        self._dpr = QGuiApplication.primaryScreen().devicePixelRatio() or 1.0
        self.hwnd = int(self.winId())
        self._click_through_set = False

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    _WRAP = Qt.AlignCenter | Qt.TextWordWrap

    def say(self, text: str, seconds: float) -> None:
        fm = QFontMetrics(self._font)
        # Wrap long lines: measure the multi-row block within a max width.
        block = fm.boundingRect(0, 0, _MAX_W, 10000, self._WRAP, text)
        tw = max(24, min(_MAX_W, block.width()))
        w = tw + 2 * _PAD
        h = block.height() + 2 * _PAD + _TAIL
        self._text = text
        self.resize(int(w), int(h))
        self.show()
        if not self._click_through_set:
            winapi.set_click_through(self.hwnd, True)
            self._click_through_set = True
        self._timer.start(int(seconds * 1000))
        self.update()

    def place_above(self, center_x_phys: float, top_y_phys: float) -> None:
        """Center the bubble horizontally over the pet, sitting just above it."""
        if not self.isVisible():
            return
        phys_w = self.width() * self._dpr
        phys_h = self.height() * self._dpr
        x = max(0.0, center_x_phys - phys_w / 2.0)
        y = max(0.0, top_y_phys - phys_h - 4)
        winapi.move_window_physical(self.hwnd, x, y)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self._font)
        w, h = self.width(), self.height()
        body_h = h - _TAIL

        p.setPen(QPen(QColor(90, 90, 105), 1))
        p.setBrush(QColor(255, 255, 255, 238))
        p.drawRoundedRect(1, 1, w - 2, body_h - 2, 8, 8)

        cx = w // 2
        tail = QPolygon([
            QPoint(cx - _TAIL, body_h - 1),
            QPoint(cx + _TAIL, body_h - 1),
            QPoint(cx, h - 1),
        ])
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 238))
        p.drawPolygon(tail)

        p.setPen(QColor(40, 40, 55))
        p.drawText(
            _PAD, _PAD, w - 2 * _PAD, body_h - 2 * _PAD, self._WRAP, self._text
        )
