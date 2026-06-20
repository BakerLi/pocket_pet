"""Procedural sprite provider.

No art assets yet, so we draw the pet with QPainter primitives and animate it
analytically from an accumulating time value (no sprite sheet / frame indices).
Colours come from the pet's species; size/appearance vary by growth stage.
This is the default :class:`SpriteProvider`; an asset-backed one can drop in
behind the same interface later (see :mod:`sprite_provider`).
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygon

from ..core.state_machine import State
from ..sim.growth import Stage
from .sprite_provider import SpriteContext, SpriteProvider

_DARK = QColor(35, 35, 48)
_CHEEK = QColor(255, 150, 170, 160)
_EGG = QColor(250, 246, 236)
_DEFAULT_BODY = QColor(120, 200, 255)
_DEFAULT_EDGE = QColor(70, 140, 200)
_INNER = QColor(255, 175, 195)   # inner-ear / soft pink
_BEAK = QColor(255, 180, 60)     # bills & beaks
_WHITE = QColor(250, 250, 252)


class ProceduralProvider(SpriteProvider):
    """Draws the pet entirely with QPainter primitives (no art assets)."""

    def draw(self, p: QPainter, ctx: SpriteContext) -> None:
        # Unpack the context into the local names the drawing code below uses.
        w, h = ctx.w, ctx.h
        state, facing, t = ctx.state, ctx.facing, ctx.t
        vy, sad, stage = ctx.vy, ctx.sad, ctx.stage
        body_color, edge_color, species_key = (
            ctx.body_color, ctx.edge_color, ctx.species_key,
        )

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
        if state in (State.WALK, State.RUN):
            freq = 15.0 if state is State.RUN else 9.0
            amp = 0.08 if state is State.RUN else 0.05
            bob = -abs(math.sin(t * freq)) * h * amp
            leg_swing = math.sin(t * freq) * w * (0.14 if state is State.RUN else 0.10)
        elif state is State.LAND:
            squash = 0.18  # flattened on impact
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
        elif state is State.EAT:
            bob = abs(math.sin(t * 12.0)) * h * 0.03  # quick chewing nods
        elif state is State.PET:
            bob = math.sin(t * 5.0) * h * 0.02        # happy little wiggle
        elif state is State.CLIMB:
            leg_swing = math.sin(t * 10.0) * w * 0.09  # clambering limbs
            bob = math.sin(t * 10.0) * h * 0.015

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

        # --- species features behind the body (ears, horns, shell...) -------
        self._features(p, species_key, "back", cx, top, body_w, body_h,
                       facing, body_c, edge_c, w, h)

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
        happy = state is State.PET  # smiling, content eyes while being petted

        for sx in (-1, 1):
            ex = cx + sx * eye_dx + gaze
            if closed:
                p.setPen(QPen(_DARK, max(1.5, w * 0.02)))
                p.setBrush(Qt.NoBrush)
                p.drawLine(int(ex - eye_r), int(eye_y), int(ex + eye_r), int(eye_y))
            elif happy:  # upturned, smiling eyes (∩ ∩)
                p.setPen(QPen(_DARK, max(1.5, w * 0.022)))
                p.setBrush(Qt.NoBrush)
                p.drawArc(int(ex - eye_r), int(eye_y - eye_r * 0.5), int(eye_r * 2), int(eye_r * 2),
                          20 * 16, 140 * 16)
            elif sad:  # droopy down-turned eyes
                p.setPen(QPen(_DARK, max(1.5, w * 0.022)))
                p.setBrush(Qt.NoBrush)
                p.drawArc(int(ex - eye_r), int(eye_y - eye_r), int(eye_r * 2), int(eye_r * 2),
                          200 * 16, 140 * 16)
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(_DARK)
                p.drawEllipse(int(ex - eye_r), int(eye_y - eye_r), int(eye_r * 2), int(eye_r * 2))

        # Open, chewing mouth while eating.
        if state is State.EAT:
            chew = 0.5 + 0.5 * abs(math.sin(t * 12.0))
            mw = w * 0.14
            mh = h * 0.07 * chew + 1.0
            my = eye_y + eye_r * 2.0
            p.setPen(Qt.NoPen)
            p.setBrush(_DARK)
            p.drawEllipse(int(cx + gaze - mw / 2), int(my), int(mw), int(mh))

        # cheeks (skip when sad)
        if not sad:
            p.setPen(Qt.NoPen)
            p.setBrush(_CHEEK)
            ch = max(2.0, w * 0.04)
            for sx in (-1, 1):
                p.drawEllipse(int(cx + sx * eye_dx * 1.7 + gaze - ch), int(eye_y + eye_r),
                              int(ch * 2), int(ch * 1.6))

        # --- species features in front of the body (beak, belly, cap...) ----
        self._features(p, species_key, "front", cx, top, body_w, body_h,
                       facing, body_c, edge_c, w, h)

        # Zzz while sleeping
        if state is State.SLEEP:
            p.setPen(QPen(_DARK, max(1.0, w * 0.015)))
            p.setBrush(Qt.NoBrush)
            zf = (t % 2.0) / 2.0
            zx = cx + body_w * 0.45
            zy = top - h * 0.05 - zf * h * 0.18
            p.drawText(int(zx), int(zy), "z")

    # --- per-species procedural features --------------------------------
    def _features(self, p, key, layer, cx, top, bw, bh, facing,
                  body_c, edge_c, w, h):
        """Draw species-specific bits so each species reads distinctly.

        ``layer`` is "back" (behind the body: ears, horns, shells) or "front"
        (over the face: beaks, bellies, caps). Geometry is relative to the body
        ellipse (centre ``cx``, top ``top``, size ``bw`` x ``bh``).
        """
        pen = QPen(edge_c, max(1.0, w * 0.013))

        def ell(x, y, ew, eh, brush, outline=True):
            p.setPen(pen if outline else Qt.NoPen)
            p.setBrush(brush)
            p.drawEllipse(int(x), int(y), int(ew), int(eh))

        def tri(pts, brush, outline=True):
            p.setPen(pen if outline else Qt.NoPen)
            p.setBrush(brush)
            p.drawPolygon(QPolygon([QPoint(int(a), int(b)) for a, b in pts]))

        mid_y = top + bh * 0.5
        bcx = cx  # body centre x

        if layer == "back":
            if key == "rabbit":
                ew, eh = bw * 0.16, bh * 0.78
                for sx in (-1, 1):
                    ex = bcx + sx * bw * 0.20 - ew / 2
                    ell(ex, top - eh * 0.78, ew, eh, body_c)
                    ell(ex + ew * 0.28, top - eh * 0.66, ew * 0.44, eh * 0.62, _INNER, False)
            elif key in ("cat", "capybara"):
                size = bw * 0.30 if key == "cat" else bw * 0.20
                for sx in (-1, 1):
                    bx = bcx + sx * bw * 0.30
                    tri([(bx - size / 2, top + bh * 0.12),
                         (bx + size / 2, top + bh * 0.12),
                         (bx + sx * size * 0.15, top - bh * 0.22)], body_c)
            elif key == "owl":
                for sx in (-1, 1):
                    bx = bcx + sx * bw * 0.34
                    tri([(bx - bw * 0.10, top + bh * 0.08),
                         (bx + bw * 0.10, top + bh * 0.08),
                         (bx, top - bh * 0.16)], body_c)
            elif key == "dragon":
                for sx in (-1, 1):  # horns
                    bx = bcx + sx * bw * 0.26
                    tri([(bx - bw * 0.07, top + bh * 0.05),
                         (bx + bw * 0.07, top + bh * 0.05),
                         (bx + sx * bw * 0.12, top - bh * 0.28)], edge_c)
                for sx in (-1, 1):  # wings
                    bx = bcx + sx * bw * 0.5
                    tri([(bx, mid_y - bh * 0.2),
                         (bx + sx * bw * 0.42, mid_y - bh * 0.05),
                         (bx + sx * bw * 0.30, mid_y + bh * 0.32)], edge_c)
            elif key == "turtle":  # shell hump on top
                ell(bcx - bw * 0.42, top - bh * 0.18, bw * 0.84, bh * 0.55, edge_c)
            elif key == "snail":  # spiral shell on the back
                sx0 = bcx + bw * 0.18
                ell(sx0 - bw * 0.30, mid_y - bh * 0.30, bw * 0.6, bh * 0.6, edge_c)
                ell(sx0 - bw * 0.16, mid_y - bh * 0.16, bw * 0.32, bh * 0.32, body_c, False)
            elif key == "robot":  # antenna
                p.setPen(QPen(edge_c, max(1.5, w * 0.02)))
                p.drawLine(int(bcx), int(top), int(bcx), int(top - bh * 0.3))
                ell(bcx - bw * 0.06, top - bh * 0.42, bw * 0.12, bh * 0.12, _INNER)
            elif key == "mushroom":  # cap dome behind/over the top
                ell(bcx - bw * 0.58, top - bh * 0.30, bw * 1.16, bh * 0.8, edge_c)
            elif key in ("duck", "goose", "penguin"):  # tuft
                tri([(bcx - bw * 0.08, top + bh * 0.02),
                     (bcx + bw * 0.08, top + bh * 0.02),
                     (bcx + bw * 0.02, top - bh * 0.22)], edge_c)
            return

        # ---- front layer ----
        if key == "mushroom":  # white spots on the cap
            for dx, dy in ((-0.26, -0.05), (0.20, -0.10), (0.0, -0.22)):
                ell(bcx + dx * bw, top - bh * 0.12 + dy * bh, bw * 0.16, bh * 0.13, _WHITE, False)
        elif key == "penguin":  # white belly + flippers + beak
            ell(bcx - bw * 0.26, top + bh * 0.30, bw * 0.52, bh * 0.62, _WHITE, False)
            for sx in (-1, 1):
                ell(bcx + sx * bw * 0.46 - bw * 0.08, mid_y - bh * 0.1, bw * 0.16, bh * 0.42, edge_c)
            tri([(bcx, mid_y - bh * 0.05), (bcx + bw * 0.18 * facing, mid_y),
                 (bcx, mid_y + bh * 0.08)], _BEAK)
        elif key == "duck":  # wide flat bill
            ell(bcx + facing * bw * 0.06, mid_y - bh * 0.02, bw * 0.34, bh * 0.18, _BEAK)
        elif key == "goose":  # slim beak
            tri([(bcx, mid_y - bh * 0.08), (bcx + facing * bw * 0.32, mid_y),
                 (bcx, mid_y + bh * 0.04)], _BEAK)
        elif key == "owl":  # small triangular beak
            tri([(bcx - bw * 0.06, mid_y), (bcx + bw * 0.06, mid_y),
                 (bcx, mid_y + bh * 0.16)], _BEAK)
        elif key == "cactus":  # spikes + flower
            p.setPen(QPen(edge_c, max(1.0, w * 0.012)))
            for ang in range(0, 360, 45):
                a = math.radians(ang)
                ox, oy = math.cos(a) * bw * 0.5, math.sin(a) * bh * 0.5
                p.drawLine(int(bcx + ox), int(mid_y + oy),
                           int(bcx + ox * 1.18), int(mid_y + oy * 1.18))
            ell(bcx - bw * 0.10, top - bh * 0.04, bw * 0.2, bh * 0.16, _INNER, False)
        elif key == "blob":  # glossy highlight
            ell(bcx - bw * 0.28, top + bh * 0.12, bw * 0.18, bh * 0.16, _WHITE, False)
        elif key == "ghost":  # scalloped wavy hem
            n = 4
            for i in range(n):
                bx = bcx - bw * 0.5 + bw * (i + 0.5) / n
                ell(bx - bw / n * 0.5, top + bh * 0.82, bw / n, bh * 0.3, body_c, False)
        elif key == "octopus":  # little tentacle bumps along the bottom
            n = 4
            for i in range(n):
                bx = bcx - bw * 0.42 + bw * 0.84 * i / (n - 1)
                ell(bx - bw * 0.10, top + bh * 0.82, bw * 0.2, bh * 0.28, body_c)
        elif key == "chonk":  # extra chubby cheeks
            for sx in (-1, 1):
                ell(bcx + sx * bw * 0.42 - bw * 0.12, mid_y + bh * 0.02, bw * 0.24, bh * 0.3, body_c)
        elif key == "robot":  # chest panel
            p.setPen(pen)
            p.setBrush(_INNER)
            p.drawRect(int(bcx - bw * 0.16), int(mid_y + bh * 0.05), int(bw * 0.32), int(bh * 0.22))
        elif key == "axolotl":  # external gills (frills) on the sides of the head
            for sx in (-1, 1):
                for k in range(3):
                    bx = bcx + sx * bw * 0.42
                    by = top + bh * 0.18 + k * bh * 0.14
                    ell(bx - bw * 0.05, by, bw * 0.18, bh * 0.1, _INNER)

    def draw_petting_hand(self, p: QPainter, w: int, h: int, t: float) -> None:
        """A little hand stroking the pet's head, sliding side to side."""
        p.setRenderHint(QPainter.Antialiasing)
        sway = math.sin(t * 6.0) * w * 0.12
        cx = w / 2.0 + sway
        cy = h * 0.16                      # hovers above the head
        palm_w, palm_h = w * 0.34, h * 0.24

        skin = QColor(247, 213, 180)
        edge = QColor(196, 156, 120)
        p.setPen(QPen(edge, max(1.0, w * 0.012)))
        p.setBrush(skin)
        # palm
        p.drawEllipse(int(cx - palm_w / 2), int(cy), int(palm_w), int(palm_h))
        # fingers
        fw = palm_w * 0.20
        for i in range(4):
            fx = cx - palm_w * 0.36 + i * palm_w * 0.24
            p.drawEllipse(int(fx - fw / 2), int(cy - palm_h * 0.32),
                          int(fw), int(palm_h * 0.7))

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
