"""Transparent, always-on-top window hosting one pet.

The window is only as big as the sprite (see DESIGN 1.1): it receives the pet's
own mouse events while everything around it stays click-through automatically.
Position is driven in PHYSICAL pixels via Win32 so it never fights Qt's
high-DPI scaling.

Interaction (Phase 2):
* Left-drag  -> grab the pet; release with velocity to throw it (then gravity).
* Left-click -> a little hop.
* Right-click-> context menu (greet / add / release / quit).
"""

from __future__ import annotations

import math
import time

import win32api
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter
from PySide6.QtWidgets import QMenu, QWidget

from ..config import BUBBLE_SECONDS, CHATTER_INTERVAL, DT, LOW_NEED
from ..core.pet import Pet
from ..platform import winapi
from ..sim import dialogue
from ..sim.growth import Stage
from .speech_bubble import SpeechBubble
from .sprite import PetSprite
from .stats_panel import StatsPanel

_DRAG_THRESHOLD = 4      # physical px of movement before a press counts as a drag
_MAX_THROW = 2600.0      # px/s cap on release velocity
_HOP_VELOCITY = -680.0   # upward kick on a plain click


class PetWindow(QWidget):
    def __init__(self, pet: Pet, world):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Pocket Pet")

        self.pet = pet
        self.world = world
        self.sprite = PetSprite()
        self._anim = 0.0

        self.bubble = SpeechBubble()
        self._chatter_t = self.pet.brain.rng.uniform(*CHATTER_INTERVAL)
        self._last_stage = self.pet.stage
        self._panel: StatsPanel | None = None
        self._body_color, self._edge_color = self._palette()

        # Drag/throw bookkeeping (all in physical px).
        self._grab_dx = 0.0
        self._grab_dy = 0.0
        self._press_xy = (0, 0)
        self._moved = False
        self._vel = (0.0, 0.0)
        self._last_pos = (0, 0)
        self._last_t = 0.0

        # Size the Qt window so logical * dpr == the sprite's physical size.
        dpr = QGuiApplication.primaryScreen().devicePixelRatio() or 1.0
        logical = max(1, round(pet.body.width / dpr))
        self.resize(logical, logical)

        self.hwnd = int(self.winId())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(int(1000 * DT))

    # --- loop ------------------------------------------------------------
    def _tick(self) -> None:
        self._anim += DT
        self.pet.update(DT, self.world.platforms)
        winapi.move_window_physical(self.hwnd, self.pet.body.x, self.pet.body.y)

        # Ambient chatter.
        self._chatter_t -= DT
        if self._chatter_t <= 0:
            self._chatter_t = self.pet.brain.rng.uniform(*CHATTER_INTERVAL)
            self._say(dialogue.pick(self.pet.needs, None, self.pet.brain.rng))

        # Growth milestones.
        if self.pet.stage is not self._last_stage:
            if self._last_stage is Stage.EGG:
                self._say("✨ 孵化了!")
            elif self.pet.stage is Stage.ADULT:
                self._say("我長大了!")
            self._last_stage = self.pet.stage

        # Keep the bubble hovering above the pet.
        b = self.pet.body
        self.bubble.place_above(b.x + b.width / 2.0, b.y)

        self.update()

    def _palette(self) -> tuple[QColor, QColor]:
        ident = self.pet.identity
        br, bg, bb = ident.species.body
        if ident.shiny:  # shiny: brighter body, gold trim
            return (
                QColor(min(255, br + 35), min(255, bg + 35), min(255, bb + 35)),
                QColor(240, 205, 90),
            )
        er, eg, eb = ident.species.edge
        return QColor(br, bg, bb), QColor(er, eg, eb)

    def _say(self, line: str | None) -> None:
        if line:
            self.bubble.say(line, BUBBLE_SECONDS)
            b = self.pet.body
            self.bubble.place_above(b.x + b.width / 2.0, b.y)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        n = self.pet.needs
        sad = n.mood < LOW_NEED or n.fullness < LOW_NEED
        self.sprite.draw(
            p, self.width(), self.height(),
            self.pet.state, self.pet.facing, self._anim, self.pet.body.vy, sad,
            self.pet.stage, self._body_color, self._edge_color,
        )

    # --- interaction -----------------------------------------------------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.RightButton:
            self._show_menu(e.globalPosition().toPoint())
            return
        if e.button() != Qt.LeftButton:
            return
        cx, cy = win32api.GetCursorPos()  # physical px
        self._grab_dx = cx - self.pet.body.x
        self._grab_dy = cy - self.pet.body.y
        self._press_xy = (cx, cy)
        self._moved = False
        self._vel = (0.0, 0.0)
        self._last_pos = (cx, cy)
        self._last_t = time.perf_counter()
        self.pet.body.held = True
        self.grabMouse()  # keep receiving moves even when the cursor outruns the window

    def mouseMoveEvent(self, e) -> None:
        if not (e.buttons() & Qt.LeftButton):
            return
        cx, cy = win32api.GetCursorPos()
        if not self._moved and math.hypot(cx - self._press_xy[0], cy - self._press_xy[1]) > _DRAG_THRESHOLD:
            self._moved = True

        # Follow the cursor, keeping the grab offset.
        self.pet.body.x = cx - self._grab_dx
        self.pet.body.y = cy - self._grab_dy
        winapi.move_window_physical(self.hwnd, self.pet.body.x, self.pet.body.y)

        # Track a smoothed throw velocity.
        now = time.perf_counter()
        dt = now - self._last_t
        if dt > 1e-4:
            ivx = (cx - self._last_pos[0]) / dt
            ivy = (cy - self._last_pos[1]) / dt
            self._vel = (0.5 * self._vel[0] + 0.5 * ivx, 0.5 * self._vel[1] + 0.5 * ivy)
            self._last_pos = (cx, cy)
            self._last_t = now

    def mouseReleaseEvent(self, e) -> None:
        if e.button() != Qt.LeftButton:
            return
        self.releaseMouse()
        self.pet.body.held = False
        if self._moved:
            vx, vy = self._vel
            speed = math.hypot(vx, vy)
            if speed > _MAX_THROW:
                scale = _MAX_THROW / speed
                vx, vy = vx * scale, vy * scale
            self.pet.body.vx, self.pet.body.vy = vx, vy
        else:
            self._greet()  # plain click

    def _greet(self) -> None:
        self._hop()
        self._say(dialogue.pick(self.pet.needs, "greet", self.pet.brain.rng))

    def _hop(self) -> None:
        self.pet.body.vy = _HOP_VELOCITY
        self.pet.body.on_ground = False

    def _feed(self) -> None:
        self.pet.needs.feed()
        self._say(dialogue.pick(self.pet.needs, "feed", self.pet.brain.rng))

    def _stroke(self) -> None:
        self.pet.needs.stroke()
        self._say(dialogue.pick(self.pet.needs, "pet", self.pet.brain.rng))

    def _open_stats(self) -> None:
        if self._panel is None:
            self._panel = StatsPanel(self.pet)
        self._panel.show()
        self._panel.raise_()
        self._panel.activateWindow()

    def _show_menu(self, global_pos) -> None:
        menu = QMenu(self)
        menu.addAction("🍖  餵食", self._feed)             # 餵食
        menu.addAction("🤚  摸摸", self._stroke)           # 摸摸
        menu.addAction("ℹ️  狀態", self._open_stats)       # 狀態面板
        menu.addSeparator()
        menu.addAction("➕  再生一隻", lambda: self.world.spawn())     # 再生一隻
        menu.addAction("🐾  放生這隻", lambda: self.world.remove(self))  # 放生這隻
        menu.addSeparator()
        menu.addAction("❌  結束", lambda: self.world.quit())  # 結束
        menu.exec(global_pos)

    def shutdown(self) -> None:
        self.timer.stop()
        if self._panel is not None:
            self._panel.close()
        self.bubble.close()
        self.close()
