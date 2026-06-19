"""System tray icon — the app's reliable home (pet windows have no taskbar entry).

Provides the canonical way to quit the app.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def _make_icon() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(120, 200, 255))
    p.drawEllipse(6, 6, 52, 52)
    p.setBrush(QColor(35, 35, 48))
    p.drawEllipse(22, 26, 8, 8)
    p.drawEllipse(36, 26, 8, 8)
    p.end()
    return QIcon(pm)


def build_tray(world) -> QSystemTrayIcon:
    """Create and show the tray icon wired to the world. Caller must keep a ref."""
    tray = QSystemTrayIcon(_make_icon())
    tray.setToolTip("Pocket Pet")

    menu = QMenu()
    menu.addAction("🏠  把寵物找回來", lambda: world.recall_pet())  # 🏠 找回跑掉的寵物
    menu.addSeparator()
    menu.addAction("❌  結束", lambda: world.quit())              # ❌ 結束
    tray.setContextMenu(menu)
    tray._menu = menu  # prevent GC of the menu

    # Double-click the tray icon to recall the pet too.
    tray.activated.connect(
        lambda reason: world.recall_pet()
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick
        else None
    )
    tray.show()
    return tray
