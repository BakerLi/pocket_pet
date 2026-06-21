"""System tray icon — the app's reliable home (pet windows have no taskbar entry).

Provides the canonical way to quit the app.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QActionGroup, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..sim import ai
from ..sim.persistence import dev_mode_enabled


def _set_personality(world, key: str) -> None:
    """Switch persona and clear the live pet's pooled lines so the new voice
    kicks in on the next chatter (instead of waiting out the old batch)."""
    ai.set_personality(key)
    win = getattr(world, "pet_window", None)
    if win is not None and getattr(win, "_ai", None) is not None:
        win._ai.reset()


def _build_ai_menu(menu: QMenu, world) -> None:
    """Add the '🤖 AI 嘴砲' submenu (enable toggle + personality picker)."""
    ai_menu = menu.addMenu("🤖  AI 嘴砲")

    toggle = ai_menu.addAction("啟用")
    toggle.setCheckable(True)
    toggle.setChecked(ai.is_enabled())
    toggle.toggled.connect(ai.set_enabled)

    peek = ai_menu.addAction("👀  偷看視窗吐槽")  # privacy-sensitive, default off
    peek.setCheckable(True)
    peek.setChecked(ai.window_snark_enabled())
    peek.setToolTip("會讀取目前視窗標題拿去生成吐槽,僅在你開啟時運作")
    peek.toggled.connect(ai.set_window_snark)

    muse = ai_menu.addAction("🌌  哲學murmur")  # occasional philosophical musings
    muse.setCheckable(True)
    muse.setChecked(ai.philosophy_enabled())
    muse.setToolTip("每隔幾分鐘冒出一句結合時間/節日/天氣/視窗/回憶的哲學感慨")
    muse.toggled.connect(ai.set_philosophy)

    weather = ai_menu.addAction("🌦️  天氣素材")  # privacy-sensitive, default off
    weather.setCheckable(True)
    weather.setChecked(ai.weather_enabled())
    weather.setToolTip("用 wttr.in 抓當地天氣(會把大概位置/IP 送到第三方),每小時一次")
    weather.toggled.connect(ai.set_weather)

    ai_menu.addSeparator()
    header = ai_menu.addAction("個性")     # non-clickable section label
    header.setEnabled(False)

    group = QActionGroup(ai_menu)
    group.setExclusive(True)
    current = ai.personality()
    for key, label in ai.personalities():
        act = ai_menu.addAction(label)
        act.setCheckable(True)
        act.setChecked(key == current)
        group.addAction(act)
        act.triggered.connect(lambda _checked=False, k=key: _set_personality(world, k))
    ai_menu._group = group       # prevent GC of the action group
    menu._ai_menu = ai_menu      # prevent GC of the submenu itself


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
    if ai.has_key():  # Gemini-powered snark controls (only if a key is present)
        _build_ai_menu(menu, world)
    if dev_mode_enabled():  # developer backdoor to revive a dead pet
        menu.addAction("🔧  復活寵物", lambda: world.revive_pet())
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
