"""Procedural placeholder sprite.

No art assets yet, so we draw the pet with QPainter primitives and animate it
analytically from an accumulating time value (no sprite sheet / frame indices).
Colours come from the pet's species; size/appearance vary by growth stage.
This is deliberately swappable: a real sprite-sheet animator can replace
:meth:`PetSprite.draw` behind the same call signature later.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen

from ..core.state_machine import State
from ..sim.growth import Stage

_DARK = QColor(35, 35, 48)
_CHEEK = QColor(255, 150, 170, 160)
_EGG = QColor(250, 246, 236)
_DEFAULT_BODY = QColor(120, 200, 255)
_DEFAULT_EDGE = QColor(70, 140, 200)


class PetSprite:
    def draw(
        self,
        p: QPainter,
        w: int,
        h: int,
        state: State,
        facing: int,
        t: float,
        vy: float = 0.0,
        sad: bool = False,
        stage: Stage = Stage.ADULT,
        body_color: QColor | None = None,
        edge_color: QColor | None = None,
    ) -> None:
        p.setRenderHint(QPainter.Antialiasing)
        body_c = body_color or _DEFAULT_BODY
        edge_c = edge_color or _DEFAULT_EDGE

        if stage is Stage.EGG:
            self._draw_egg(p, w, h, t, body_c, edge_c)
            return

        scale = stage.scale
        baby = stage is Stage.BABY

        # --- animation parameters per state ---------------------------------
        bob = 0.0          # vertical body offset
        squash = 0.0       # >0 = wider+flatter (landing), <0 = taller (falling)
        leg_swing = 0.0
        if state is State.WALK:
            bob = -abs(math.sin(t * 9.0)) * h * 0.05
            leg_swing = math.sin(t * 9.0) * w * 0.10
        elif state is State.IDLE:
            bob = math.sin(t * 2.2) * h * 0.012  # gentle breathing
        elif state is State.FALL:
            squash = -0.10                        # stretched while falling
        elif state is State.DRAG:
            squash = -0.06                        # dangling from the cursor
            bob = math.sin(t * 14.0) * h * 0.03   # wobble
        elif state is State.SLEEP:
            bob = math.sin(t * 1.4) * h * 0.02    # slow breathing
            squash = 0.04                         # slightly slumped

        cx = w / 2.0
        body_w = w * (0.80 + squash * -1.0) * 0.9 * scale
        body_h = h * (0.72 - squash) * 0.9 * scale
        top = h - body_h - 4 + bob

        # --- feet ----------------------------------------------------------
        p.setBrush(edge_c)
        p.setPen(Qt.NoPen)
        foot_w, foot_h = w * 0.18 * scale, h * 0.10 * scale
        fy = h - foot_h - 2
        p.drawEllipse(int(cx - body_w * 0.30 - leg_swing), int(fy), int(foot_w), int(foot_h))
        p.drawEllipse(int(cx + body_w * 0.30 - foot_w + leg_swing), int(fy), int(foot_w), int(foot_h))

        # --- body ----------------------------------------------------------
        p.setPen(Qt.NoPen)
        p.setBrush(edge_c)
        p.drawEllipse(int(cx - body_w / 2 - 1.5), int(top - 1.5), int(body_w + 3), int(body_h + 3))
        p.setBrush(body_c)
        p.drawEllipse(int(cx - body_w / 2), int(top), int(body_w), int(body_h))

        # --- face (shifts toward facing direction) -------------------------
        gaze = facing * w * 0.05
        eye_y = top + body_h * 0.40
        eye_dx = body_w * 0.20
        eye_r = max(2.0, w * 0.055) * (1.35 if baby else 1.0)  # babies have big eyes

        blink = state is State.IDLE and (t % 3.4) < 0.13
        closed = state is State.SLEEP or blink

        for sx in (-1, 1):
            ex = cx + sx * eye_dx + gaze
            if closed:
                p.setPen(QPen(_DARK, max(1.5, w * 0.02)))
                p.setBrush(Qt.NoBrush)
                p.drawLine(int(ex - eye_r), int(eye_y), int(ex + eye_r), int(eye_y))
            elif sad:  # droopy down-turned eyes
                p.setPen(QPen(_DARK, max(1.5, w * 0.022)))
                p.setBrush(Qt.NoBrush)
                p.drawArc(int(ex - eye_r), int(eye_y - eye_r), int(eye_r * 2), int(eye_r * 2),
                          200 * 16, 140 * 16)
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(_DARK)
                p.drawEllipse(int(ex - eye_r), int(eye_y - eye_r), int(eye_r * 2), int(eye_r * 2))

        # cheeks (skip when sad)
        if not sad:
            p.setPen(Qt.NoPen)
            p.setBrush(_CHEEK)
            ch = max(2.0, w * 0.04)
            for sx in (-1, 1):
                p.drawEllipse(int(cx + sx * eye_dx * 1.7 + gaze - ch), int(eye_y + eye_r),
                              int(ch * 2), int(ch * 1.6))

        # Zzz while sleeping
        if state is State.SLEEP:
            p.setPen(QPen(_DARK, max(1.0, w * 0.015)))
            p.setBrush(Qt.NoBrush)
            zf = (t % 2.0) / 2.0
            zx = cx + body_w * 0.45
            zy = top - h * 0.05 - zf * h * 0.18
            p.drawText(int(zx), int(zy), "z")

    def _draw_egg(self, p: QPainter, w: int, h: int, t: float, body_c: QColor, edge_c: QColor) -> None:
        """An unhatched egg: cream shell speckled with the species colour, wobbling."""
        sway = math.sin(t * 3.0) * w * 0.025
        ew, eh = w * 0.52, h * 0.66
        cx = w / 2.0 + sway
        top = h - eh - 3

        p.setPen(QPen(edge_c, max(1.5, w * 0.02)))
        p.setBrush(_EGG)
        p.drawEllipse(int(cx - ew / 2), int(top), int(ew), int(eh))

        # Speckles in the species colour.
        p.setPen(Qt.NoPen)
        p.setBrush(body_c)
        spots = [(-0.18, 0.30, 0.10), (0.20, 0.45, 0.08), (-0.05, 0.62, 0.07), (0.12, 0.20, 0.06)]
        for dx, dy, r in spots:
            rr = r * ew
            p.drawEllipse(int(cx + dx * ew - rr / 2), int(top + dy * eh - rr / 2), int(rr), int(rr))
