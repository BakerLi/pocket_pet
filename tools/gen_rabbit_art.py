"""Generate the rabbit's sprite-sheet art into assets/sprites/rabbit/.

This is a DEV TOOL, not part of the app. It renders polished, multi-frame
PNG sprite sheets with QPainter (shading, blinking, a hop cycle, etc.) so the
rabbit looks nicer + smoother than the inline procedural drawing, and to prove
the asset pipeline with real files. Hand-drawn PNGs of the same names can
replace these anytime.

Run:  .venv/Scripts/python.exe tools/gen_rabbit_art.py
Output: assets/sprites/rabbit/<state>.png (+ <state>.json frame metadata)
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication

S = 192  # frame size (2x the 96px box for crisp downscaling)

BODY = QColor(252, 244, 246)
BODY_HI = QColor(255, 255, 255)
EDGE = QColor(206, 174, 184)
INNER = QColor(255, 178, 196)
DARK = QColor(54, 48, 60)
NOSE = QColor(232, 140, 160)
BLUSH = QColor(255, 168, 186, 150)
TAIL = QColor(255, 255, 255)


def _ear(p, base_x, base_y, length, width, angle_deg, tilt_color=INNER):
    """One ear rooted at (base_x, base_y), leaning by angle (deg, +=outward)."""
    p.save()
    p.translate(base_x, base_y)
    p.rotate(angle_deg)
    p.setPen(QPen(EDGE, S * 0.012))
    p.setBrush(BODY)
    p.drawRoundedRect(QRectF(-width / 2, -length, width, length), width * 0.5, width * 0.5)
    p.setPen(Qt.NoPen)
    p.setBrush(tilt_color)
    iw, il = width * 0.5, length * 0.72
    p.drawRoundedRect(QRectF(-iw / 2, -length + width * 0.35, iw, il), iw * 0.5, iw * 0.5)
    p.restore()


def draw_rabbit(p, *, eye="open", ear_l=-8.0, ear_r=8.0, ear_len=1.0,
                squash=0.0, bob=0.0, mouth=0.0, blush=True, zzz=0,
                lean=0.0, foot=0.0, climb=False):
    """Draw one rabbit frame (S x S). Feet near the bottom, centred + lean."""
    p.setRenderHint(QPainter.Antialiasing)
    cx = S * 0.5 + lean
    bw = S * 0.50 * (1.0 + squash)
    bh = S * 0.56 * (1.0 - squash)
    feet_y = S * 0.90
    top = feet_y - bh + bob

    # tail (behind, lower-right)
    p.setPen(QPen(EDGE, S * 0.01))
    p.setBrush(TAIL)
    p.drawEllipse(QRectF(cx + bw * 0.30, feet_y - bh * 0.28, bw * 0.24, bw * 0.24))

    # ears (behind the head)
    ear_len_px = bh * 0.85 * ear_len
    _ear(p, cx - bw * 0.20, top + bh * 0.14, ear_len_px, bw * 0.20, ear_l)
    _ear(p, cx + bw * 0.20, top + bh * 0.14, ear_len_px, bw * 0.20, ear_r)

    # feet
    p.setPen(QPen(EDGE, S * 0.012))
    p.setBrush(BODY)
    fw, fh = bw * 0.40, bh * 0.18
    p.drawEllipse(QRectF(cx - bw * 0.34 - foot, feet_y - fh * 0.5, fw, fh))
    p.drawEllipse(QRectF(cx + bw * 0.34 - fw + foot, feet_y - fh * 0.5, fw, fh))

    # body with soft shading
    grad = QRadialGradient(cx - bw * 0.18, top + bh * 0.30, bw * 0.95)
    grad.setColorAt(0.0, BODY_HI)
    grad.setColorAt(1.0, BODY)
    p.setPen(QPen(EDGE, S * 0.016))
    p.setBrush(grad)
    p.drawEllipse(QRectF(cx - bw / 2, top, bw, bh))

    # --- face ---
    eye_y = top + bh * 0.46
    eye_dx = bw * 0.22
    eye_r = bw * 0.115
    if eye == "open":
        for sx in (-1, 1):
            ex = cx + sx * eye_dx
            p.setPen(Qt.NoPen)
            p.setBrush(DARK)
            p.drawEllipse(QRectF(ex - eye_r, eye_y - eye_r, eye_r * 2, eye_r * 2))
            p.setBrush(BODY_HI)  # highlight
            p.drawEllipse(QRectF(ex - eye_r * 0.2, eye_y - eye_r * 0.55,
                                 eye_r * 0.7, eye_r * 0.7))
    elif eye in ("blink", "closed"):
        p.setPen(QPen(DARK, S * 0.018))
        for sx in (-1, 1):
            ex = cx + sx * eye_dx
            p.drawArc(QRectF(ex - eye_r, eye_y - eye_r, eye_r * 2, eye_r * 2),
                      200 * 16, 140 * 16)
    elif eye == "happy":
        p.setPen(QPen(DARK, S * 0.02))
        for sx in (-1, 1):
            ex = cx + sx * eye_dx
            p.drawArc(QRectF(ex - eye_r, eye_y - eye_r * 0.5, eye_r * 2, eye_r * 2),
                      20 * 16, 140 * 16)
    elif eye == "sad":
        p.setPen(QPen(DARK, S * 0.02))
        for sx in (-1, 1):
            ex = cx + sx * eye_dx
            p.drawArc(QRectF(ex - eye_r, eye_y - eye_r, eye_r * 2, eye_r * 2),
                      200 * 16, 140 * 16)
    elif eye == "wide":
        for sx in (-1, 1):
            ex = cx + sx * eye_dx
            p.setPen(QPen(DARK, S * 0.01))
            p.setBrush(BODY_HI)
            p.drawEllipse(QRectF(ex - eye_r * 1.1, eye_y - eye_r * 1.1, eye_r * 2.2, eye_r * 2.2))
            p.setPen(Qt.NoPen)
            p.setBrush(DARK)
            p.drawEllipse(QRectF(ex - eye_r * 0.6, eye_y - eye_r * 0.5, eye_r * 1.2, eye_r * 1.2))

    # nose
    p.setPen(Qt.NoPen)
    p.setBrush(NOSE)
    nr = bw * 0.05
    p.drawEllipse(QRectF(cx - nr, eye_y + eye_r * 1.3, nr * 2, nr * 1.6))

    # mouth (open while eating)
    if mouth > 0.01:
        p.setBrush(DARK)
        mw = bw * 0.16
        mh = bh * 0.10 * mouth + 2
        p.drawEllipse(QRectF(cx - mw / 2, eye_y + eye_r * 2.0, mw, mh))

    # blush
    if blush:
        p.setBrush(BLUSH)
        ch = bw * 0.09
        for sx in (-1, 1):
            p.drawEllipse(QRectF(cx + sx * eye_dx * 1.7 - ch, eye_y + eye_r * 0.7, ch * 2, ch * 1.5))

    # Zzz
    if zzz:
        p.setPen(QPen(DARK, S * 0.012))
        f = S * 0.05
        for i in range(zzz):
            p.setFont(p.font())
            p.drawText(int(cx + bw * 0.45 + i * f * 0.6),
                       int(top - i * f * 1.1), "z")


def render_sheet(frames_poses, fps, out_dir, name):
    n = len(frames_poses)
    img = QImage(S * n, S, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    for i, pose in enumerate(frames_poses):
        p.save()
        p.translate(S * i, 0)
        p.setClipRect(QRectF(0, 0, S, S))
        draw_rabbit(p, **pose)
        p.restore()
    p.end()
    img.save(str(out_dir / f"{name}.png"))
    (out_dir / f"{name}.json").write_text(
        json.dumps({"frames": n, "fps": fps}), encoding="utf-8"
    )
    print(f"  {name}: {n} frames @ {fps}fps -> {name}.png")


def main():
    app = QApplication(sys.argv)
    out = Path(__file__).resolve().parents[1] / "assets" / "sprites" / "rabbit"
    out.mkdir(parents=True, exist_ok=True)
    print("Generating rabbit art ->", out)

    # idle: gentle breathe + a blink
    idle = []
    for i in range(4):
        b = math.sin(i / 4 * 2 * math.pi) * S * 0.012
        idle.append(dict(eye="blink" if i == 3 else "open", bob=b,
                         ear_l=-8 + i, ear_r=8 - i))
    render_sheet(idle, 3, out, "idle")

    # walk: a 6-frame hop cycle
    walk = []
    for i in range(6):
        ph = i / 6
        hop = -abs(math.sin(ph * math.pi)) * S * 0.10
        sq = 0.10 if i in (0, 3) else -0.05
        walk.append(dict(eye="open", bob=hop, squash=sq,
                         foot=math.sin(ph * 2 * math.pi) * S * 0.05,
                         ear_l=-8 - hop * 0.5, ear_r=8 + hop * 0.5))
    render_sheet(walk, 12, out, "walk")

    # fall: stretched, ears up, wide eyes
    fall = [dict(eye="wide", squash=-0.16, ear_l=-2, ear_r=2, blush=False, bob=d)
            for d in (-S * 0.01, S * 0.01)]
    render_sheet(fall, 6, out, "fall")

    # drag: dangling wobble
    drag = [dict(eye="open", squash=-0.10, ear_l=-20 + w, ear_r=20 - w,
                 lean=w, blush=False)
            for w in (-S * 0.02, S * 0.02)]
    render_sheet(drag, 6, out, "drag")

    # sleep: closed eyes, slow breathe, Zzz
    sleep = [dict(eye="closed", squash=0.06, bob=b, zzz=z, blush=False,
                  ear_l=10, ear_r=-10)
             for b, z in ((0.0, 1), (S * 0.012, 2))]
    render_sheet(sleep, 2, out, "sleep")

    # eat: chewing
    eat = []
    for i in range(4):
        m = 0.5 + 0.5 * abs(math.sin(i / 4 * 2 * math.pi))
        eat.append(dict(eye="open", mouth=m, bob=abs(math.sin(i)) * S * 0.01))
    render_sheet(eat, 10, out, "eat")

    # pet: happy wiggle
    pet = [dict(eye="happy", lean=w, ear_l=-14, ear_r=14)
           for w in (-S * 0.02, S * 0.02)]
    render_sheet(pet, 4, out, "pet")

    # climb: clambering, ears up, limbs alternate
    climb = []
    for i in range(4):
        ph = i / 4
        climb.append(dict(eye="open", climb=True, squash=-0.04,
                          foot=math.sin(ph * 2 * math.pi) * S * 0.06,
                          ear_l=-4, ear_r=4, blush=False))
    render_sheet(climb, 10, out, "climb")

    print("Done.")


if __name__ == "__main__":
    main()
