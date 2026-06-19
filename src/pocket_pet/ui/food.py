"""A piece of food that drops from above onto the pet.

Like the speech bubble, it's its own tiny transparent, click-through top-level
window positioned in physical pixels. It tracks the pet's horizontal position as
it falls, and when it reaches the pet it fires ``on_eaten`` and closes — the
pet (in :mod:`pet_window`) then plays its eating animation and gains fullness.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

from ..config import DT, FOOD_GRAVITY, FOOD_SIZE
from ..core.pet import Pet
from ..platform import winapi


class FoodWindow(QWidget):
    def __init__(self, pet: Pet, emoji: str, on_eaten):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.pet = pet
        self.emoji = emoji
        self._on_eaten = on_eaten
        self._eaten = False

        self._dpr = QGuiApplication.primaryScreen().devicePixelRatio() or 1.0
        logical = max(1, round(FOOD_SIZE / self._dpr))
        self.resize(logical, logical)
        self._font = QFont("Segoe UI Emoji", int(logical * 0.62))

        # Start above the pet, a bit up the screen, and fall toward it.
        b = pet.body
        self._x = b.x + b.width / 2.0 - FOOD_SIZE / 2.0
        self._y = max(0.0, b.y - 300.0)
        self._vy = 0.0

        self.hwnd = int(self.winId())
        self.show()
        winapi.set_click_through(self.hwnd, True)  # never steal the pet's clicks
        winapi.move_window_physical(self.hwnd, self._x, self._y)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(int(1000 * DT))

    def _tick(self) -> None:
        b = self.pet.body
        # Home in on the pet's current x so it lands on the pet even if it walks.
        target_x = b.x + b.width / 2.0 - FOOD_SIZE / 2.0
        self._x += (target_x - self._x) * 0.18

        self._vy += FOOD_GRAVITY * DT
        self._y += self._vy * DT

        # Reached the pet's face -> it's eaten.
        if self._y + FOOD_SIZE >= b.y + b.height * 0.45:
            self._eat()
            return

        winapi.move_window_physical(self.hwnd, self._x, self._y)
        self.update()

    def _eat(self) -> None:
        if self._eaten:
            return
        self._eaten = True
        self.timer.stop()
        if self._on_eaten is not None:
            self._on_eaten()
        self.close()

    def shutdown(self) -> None:
        self.timer.stop()
        self.close()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self._font)
        p.drawText(self.rect(), Qt.AlignCenter, self.emoji)
