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
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QMenu, QMessageBox, QWidget

from ..config import (
    BUBBLE_SECONDS,
    CHATTER_INTERVAL,
    DT,
    EAT_DURATION,
    FOODS,
    FULL_REFUSE,
    HEART_COUNT,
    HEART_RISE,
    HYGIENE_DECAY_PER_POOP,
    HYGIENE_RECOVER,
    LOW_NEED,
    MEDICINE_HEAL,
    PET_REACT_SECONDS,
    SLEEP_REFUSE,
)
from ..core.pet import Pet
from ..core.state_machine import State
from ..platform import winapi
from ..sim import dialogue
from ..sim.growth import Stage
from ..sim.persistence import dev_mode_enabled, time_scale
from .food import FoodWindow
from .speech_bubble import SpeechBubble
from .sprite import ProceduralProvider
from .sprite_asset import AssetProvider
from .sprite_provider import SpriteContext
from .stats_panel import StatsPanel, _fmt_age

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
        self.setCursor(Qt.PointingHandCursor)  # hovering the pet => a hand to pet it

        self.pet = pet
        self.world = world
        # Use bundled art where present, else draw procedurally.
        self.sprite = AssetProvider(ProceduralProvider())
        self._anim = 0.0
        self._time_scale = time_scale()  # dev life-sim accelerator (1.0 = normal)

        # Interaction effects.
        self._food: FoodWindow | None = None      # at most one food in the air
        self._hearts: list[list[float]] = []      # [x, y, t, life] in window px
        self._heart_font = QFont("Segoe UI", 11)
        self._emoji_font = QFont("Segoe UI Emoji", 12)  # sick skull, etc.
        self._was_dead = False

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
        sim_dt = DT * self._time_scale
        self.pet.update(DT, self.world.platforms, sim_dt=sim_dt)
        winapi.move_window_physical(self.hwnd, self.pet.body.x, self.pet.body.y)

        # Death: freeze interactions, show a grave, mourn once.
        if self.pet.dead:
            if not self._was_dead:
                self._was_dead = True
                self._say(self.pet.death_flavour or "再見了…")
            b = self.pet.body
            self.bubble.place_above(b.x + b.width / 2.0, b.y)
            self.update()
            return
        if self._was_dead:  # revived
            self._was_dead = False

        # Drop a poop when digestion is ready.
        if self.pet.wants_poop:
            self.pet.wants_poop = False
            b = self.pet.body
            self.world.spawn_poop(b.x + b.width * 0.5 - 20, b.y + b.height - 40)

        # Hygiene: poops dirty the place; recovers once it's all cleaned.
        n = len(self.world.poops)
        h = self.pet.needs.hygiene
        h += (-HYGIENE_DECAY_PER_POOP * n if n else HYGIENE_RECOVER) * sim_dt
        self.pet.needs.hygiene = max(0.0, min(100.0, h))

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

        # Drift floating hearts upward and fade them out.
        if self._hearts:
            for hb in self._hearts:
                hb[1] -= HEART_RISE * DT
                hb[2] += DT
            self._hearts = [hb for hb in self._hearts if hb[2] < hb[3]]

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
        if self.pet.dead:
            self._draw_tombstone(p)
            return
        n = self.pet.needs
        sad = n.mood < LOW_NEED or n.fullness < LOW_NEED
        ctx = SpriteContext(
            w=self.width(), h=self.height(),
            state=self.pet.state, facing=self.pet.facing, t=self._anim,
            vy=self.pet.body.vy, sad=sad, stage=self.pet.stage,
            body_color=self._body_color, edge_color=self._edge_color,
            species_key=self.pet.identity.species.key,
        )
        self.sprite.draw(p, ctx)

        # Sick: tint the pet's pixels green (SourceAtop only paints over the
        # existing sprite, so transparent areas stay clear) + a sweat drop.
        if n.sick:
            p.save()
            p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            p.fillRect(self.rect(), QColor(120, 200, 120, 70))
            p.restore()
            w, h = self.width(), self.height()
            wob = math.sin(self._anim * 4.0) * w * 0.02
            p.setFont(self._emoji_font)
            p.drawText(int(w * 0.60 + wob), int(h * 0.32), "💀")

        # A stroking hand while the pet is being petted.
        if self.pet.state is State.PET:
            self.sprite.draw_petting_hand(p, self.width(), self.height(), self._anim)

        # Floating hearts.
        if self._hearts:
            p.setFont(self._heart_font)
            for hx, hy, ht, hlife in self._hearts:
                alpha = int(255 * max(0.0, 1.0 - ht / hlife))
                p.setPen(QColor(235, 90, 120, alpha))
                p.drawText(int(hx), int(hy), "♥")

    def _draw_tombstone(self, p: QPainter) -> None:
        w, h = self.width(), self.height()
        p.setRenderHint(QPainter.Antialiasing)
        sw, sh = w * 0.62, h * 0.72
        x, y = (w - sw) / 2, h - sh - 2
        p.setPen(QPen(QColor(90, 92, 100), max(1.5, w * 0.02)))
        p.setBrush(QColor(158, 160, 170))
        # headstone: rounded top via a rounded rect with generous radius
        p.drawRoundedRect(int(x), int(y), int(sw), int(sh), int(sw * 0.45), int(sw * 0.45))
        p.drawRect(int(x), int(y + sh * 0.4), int(sw), int(sh * 0.6))
        p.setPen(QColor(70, 72, 80))
        p.setFont(self._heart_font)
        p.drawText(int(x), int(y + sh * 0.42), int(sw), int(sh * 0.3),
                   Qt.AlignCenter, "R.I.P")

    def _epitaph(self) -> str:
        sp = self.pet.identity.species.name
        return (
            f"🪦 長眠於此的{sp}\n"
            f"享年 {_fmt_age(self.pet.death_age)}\n"
            f"死因:{self.pet.death_cause}\n\n"
            f"「{self.pet.death_flavour}」"
        )

    def _show_epitaph(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("🪦 墓誌銘")
        box.setText(self._epitaph())
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

    # --- interaction -----------------------------------------------------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.RightButton:
            self._show_menu(e.globalPosition().toPoint())
            return
        if e.button() != Qt.LeftButton:
            return
        if self.pet.dead:          # a grave: click to read the epitaph, no drag
            self._show_epitaph()
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
        if self.pet.dead or not (e.buttons() & Qt.LeftButton):
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
        if e.button() != Qt.LeftButton or self.pet.dead:
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

    def feed_random(self) -> None:
        """Drop a random food (used by the stats panel's feed button)."""
        self._drop_food(self.pet.brain.rng.choice(FOODS))

    def _drop_food(self, food) -> None:
        """Drop the chosen food from above; it lands on the pet and is eaten."""
        if self.pet.stage is Stage.EGG:
            self._say("還是顆蛋呢…")  # eggs don't eat
            return
        if self.pet.state is State.SLEEP:  # don't eat while asleep
            self._say("Zzz…")
            return
        if self.pet.needs.fullness >= FULL_REFUSE:  # too full -> refuse
            self._say(dialogue.pick(self.pet.needs, "refuse_full", self.pet.brain.rng))
            return
        if self._food is not None:  # one piece in the air at a time
            return
        _key, emoji, _name, fullness, mood_bonus = food
        self._food = FoodWindow(
            self.pet, emoji,
            on_eaten=lambda: self._consume(fullness, mood_bonus),
        )

    def _consume(self, fullness: float, mood_bonus: float) -> None:
        self._food = None
        if self.pet.state is State.SLEEP:  # fell asleep before it landed
            return
        self.pet.needs.feed(fullness, mood_bonus)
        self.pet.gain_from_food(fullness)
        self.pet.brain.start_reaction(State.EAT, EAT_DURATION)
        self._say(dialogue.pick(self.pet.needs, "feed", self.pet.brain.rng))

    def _medicine(self) -> None:
        """Give medicine; refuses if the pet isn't sick."""
        if self.pet.stage is Stage.EGG:
            return
        if not self.pet.needs.sick:
            self._say(dialogue.pick(self.pet.needs, "refuse_medicine", self.pet.brain.rng))
            return
        self.pet.needs.sick = False
        n = self.pet.needs
        n.health = min(100.0, n.health + MEDICINE_HEAL)
        self.pet.brain.start_reaction(State.EAT, EAT_DURATION)  # swallow the pill
        self._say(dialogue.pick(self.pet.needs, "medicine", self.pet.brain.rng))

    def _sleep(self) -> None:
        """Tell the pet to sleep; it refuses if it isn't tired enough."""
        if self.pet.stage is Stage.EGG:
            return
        if self.pet.needs.energy >= SLEEP_REFUSE:
            self._say(dialogue.pick(self.pet.needs, "refuse_sleep", self.pet.brain.rng))
            return
        if self.pet.body.on_ground and not self.pet.body.held:
            self.pet.brain.force_sleep()
            self._say("呼…晚安~")

    def _stroke(self) -> None:
        self.pet.needs.stroke()
        self.pet.brain.start_reaction(State.PET, PET_REACT_SECONDS)
        self._spawn_hearts()
        self._say(dialogue.pick(self.pet.needs, "pet", self.pet.brain.rng))

    def _spawn_hearts(self) -> None:
        rng = self.pet.brain.rng
        w, h = self.width(), self.height()
        for _ in range(HEART_COUNT):
            x = w * 0.5 + rng.uniform(-w * 0.25, w * 0.25)
            y = h * 0.45 + rng.uniform(-h * 0.05, h * 0.10)
            life = PET_REACT_SECONDS * rng.uniform(0.7, 1.1)
            self._hearts.append([x, y, 0.0, life])

    def _open_stats(self) -> None:
        if self._panel is None:
            self._panel = StatsPanel(self.pet, self)
        self._panel.show()
        self._panel.raise_()
        self._panel.activateWindow()

    def _show_menu(self, global_pos) -> None:
        menu = QMenu(self)
        if self.pet.dead:
            menu.addAction("🪦  墓誌銘", self._show_epitaph)
            if dev_mode_enabled():  # developer backdoor
                menu.addAction("🔧  復活", self.world.revive_pet)
            menu.addSeparator()
            menu.addAction("❌  結束", lambda: self.world.quit())
            menu.exec(global_pos)
            return
        feed_menu = menu.addMenu("🍽️  餵食")              # 餵食(多種食物)
        for food in FOODS:
            _key, emoji, name, _f, _m = food
            feed_menu.addAction(f"{emoji}  {name}", lambda f=food: self._drop_food(f))
        menu.addAction("🤚  摸摸", self._stroke)           # 摸摸
        menu.addAction("😴  睡覺", self._sleep)            # 睡覺(累了才睡)
        menu.addAction("💊  吃藥", self._medicine)         # 吃藥(生病才吃)
        menu.addAction("ℹ️  狀態", self._open_stats)       # 狀態面板
        menu.addSeparator()
        menu.addAction("❌  結束", lambda: self.world.quit())  # 結束
        menu.exec(global_pos)

    def shutdown(self) -> None:
        self.timer.stop()
        if self._food is not None:
            self._food.shutdown()
            self._food = None
        if self._panel is not None:
            self._panel.close()
        self.bubble.close()
        self.close()
