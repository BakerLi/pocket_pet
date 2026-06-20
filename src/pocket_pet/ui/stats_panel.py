"""A small stats window: species, rarity, growth stage, age, and need bars."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import SLEEP_WANT


def _fmt_age(seconds: float) -> str:
    s = int(seconds)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    if h:
        return f"{h} 小時 {m} 分"
    if m:
        return f"{m} 分 {sec} 秒"
    return f"{sec} 秒"


class StatsPanel(QWidget):
    def __init__(self, pet, window=None):
        super().__init__(None, Qt.WindowStaysOnTopHint)
        self.pet = pet
        self.window_ref = window  # PetWindow, for the real feed/pet interactions
        self.setWindowTitle("🐾 寵物狀態")
        self.setMinimumWidth(260)

        layout = QVBoxLayout(self)

        ident = pet.identity
        self._name = QLabel()
        self._name.setStyleSheet("font-size: 16px; font-weight: bold;")
        r, g, b = ident.rarity.color
        self._rarity = QLabel(f"稀有度：{ident.rarity.label}")
        self._rarity.setStyleSheet(f"color: rgb({r},{g},{b}); font-weight: bold;")
        self._stage = QLabel()
        self._weight = QLabel()
        self._status = QLabel()  # sleepy / (later) sick hints
        self._status.setStyleSheet("color: rgb(110,120,200);")
        layout.addWidget(self._name)
        layout.addWidget(self._rarity)
        layout.addWidget(self._stage)
        layout.addWidget(self._weight)
        layout.addWidget(self._status)

        self._bars: dict[str, QProgressBar] = {}
        for key, label in (
            ("fullness", "飽食度"), ("mood", "心情"), ("energy", "精力"),
            ("health", "健康"), ("hygiene", "清潔度"),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(True)
            row.addWidget(bar)
            layout.addLayout(row)
            self._bars[key] = bar

        btns = QHBoxLayout()
        feed = QPushButton("🍖 餵食")
        stroke = QPushButton("🤚 摸摸")
        sleep = QPushButton("😴 睡覺")
        med = QPushButton("💊 吃藥")
        feed.clicked.connect(self._feed)
        stroke.clicked.connect(self._stroke)
        sleep.clicked.connect(self._sleep)
        med.clicked.connect(self._medicine)
        for btn in (feed, stroke, sleep, med):
            btns.addWidget(btn)
        layout.addLayout(btns)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(200)
        self._refresh()

    def _feed(self) -> None:
        # Use the full interaction (food drops in, pet eats) when we have the
        # pet window; fall back to a direct top-up if opened standalone.
        if self.window_ref is not None:
            self.window_ref.feed_random()
        else:
            self.pet.needs.feed()
        self._refresh()

    def _stroke(self) -> None:
        if self.window_ref is not None:
            self.window_ref._stroke()
        else:
            self.pet.needs.stroke()
        self._refresh()

    def _sleep(self) -> None:
        if self.window_ref is not None:
            self.window_ref._sleep()
        self._refresh()

    def _medicine(self) -> None:
        if self.window_ref is not None:
            self.window_ref._medicine()
        self._refresh()

    def _refresh(self) -> None:
        n = self.pet.needs
        self._name.setText(self.pet.identity.display)
        self._stage.setText(f"階段：{self.pet.stage.label}（{_fmt_age(self.pet.age)}）")
        self._weight.setText(f"體重：{self.pet.weight:.2f} kg")
        for key in ("fullness", "mood", "energy", "health", "hygiene"):
            self._bars[key].setValue(int(getattr(n, key)))
        hints = []
        if n.sick:
            hints.append("🤒 生病")
        if n.energy < SLEEP_WANT:
            hints.append("💤 想睡")
        self._status.setText("　".join(hints))
