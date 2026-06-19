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


def _fmt_age(seconds: float) -> str:
    s = int(seconds)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    if h:
        return f"{h} 小時 {m} 分"
    if m:
        return f"{m} 分 {sec} 秒"
    return f"{sec} 秒"


class StatsPanel(QWidget):
    def __init__(self, pet):
        super().__init__(None, Qt.WindowStaysOnTopHint)
        self.pet = pet
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
        layout.addWidget(self._name)
        layout.addWidget(self._rarity)
        layout.addWidget(self._stage)

        self._bars: dict[str, QProgressBar] = {}
        for key, label in (("fullness", "飽食度"), ("mood", "心情"), ("energy", "精力")):
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
        feed.clicked.connect(lambda: pet.needs.feed())
        stroke.clicked.connect(lambda: pet.needs.stroke())
        btns.addWidget(feed)
        btns.addWidget(stroke)
        layout.addLayout(btns)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(200)
        self._refresh()

    def _refresh(self) -> None:
        n = self.pet.needs
        self._name.setText(self.pet.identity.display)
        self._stage.setText(f"階段：{self.pet.stage.label}（{_fmt_age(self.pet.age)}）")
        self._bars["fullness"].setValue(int(n.fullness))
        self._bars["mood"].setValue(int(n.mood))
        self._bars["energy"].setValue(int(n.energy))
