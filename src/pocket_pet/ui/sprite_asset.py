"""Asset-backed sprite provider with procedural fallback.

Looks for per-species art under ``assets/sprites/<species>/`` and draws it;
wherever a species/state/stage has no art it delegates to a fallback provider
(the procedural one). This lets art land **incrementally** — drop in
``rabbit/walk.png`` and only the rabbit's walk uses it; everything else keeps
drawing procedurally.

Asset layout (all optional)::

    assets/sprites/<species_key>/<state>.png            # adult / default
    assets/sprites/<species_key>/<state>_baby.png       # stage override
    assets/sprites/<species_key>/<state>_egg.png
    assets/sprites/<species_key>/<state>.json           # {"frames": N, "fps": F}

A PNG with no JSON is a single static frame. With ``frames`` > 1 it's a
horizontal sprite sheet (N frames of equal width laid left-to-right), looped at
``fps``. ``<state>`` is the :class:`State` value (idle/walk/fall/...). Left-
facing is drawn by mirroring, so art only needs to face right.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QPixmap

from ..core.state_machine import State
from ..sim.growth import Stage
from .sprite_provider import SpriteContext, SpriteProvider

_STAGE_SUFFIX = {Stage.EGG: "egg", Stage.BABY: "baby", Stage.ADULT: ""}


def asset_root() -> Path:
    """Directory holding ``<species>/`` art folders, in dev or frozen builds."""
    if getattr(sys, "frozen", False):  # PyInstaller: bundled via --add-data
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "assets" / "sprites"
    # dev: <repo>/assets/sprites  (this file is src/pocket_pet/ui/sprite_asset.py)
    return Path(__file__).resolve().parents[3] / "assets" / "sprites"


@dataclass(frozen=True)
class _Anim:
    pixmap: QPixmap
    frames: int
    fps: float
    scale: float = 1.0   # extra size factor (e.g. shrink adult art for a baby)


class AssetProvider(SpriteProvider):
    """Draws bundled art when present; otherwise defers to ``fallback``."""

    def __init__(self, fallback: SpriteProvider, root: Path | None = None):
        self._fallback = fallback
        self._root = root if root is not None else asset_root()
        self._cache: dict[tuple, _Anim | None] = {}  # None == known-missing

    def draw(self, p: QPainter, ctx: SpriteContext) -> None:
        anim = self._resolve(ctx.species_key, ctx.state.value, ctx.stage)
        if anim is None:
            self._fallback.draw(p, ctx)
            return
        self._blit(p, ctx, anim)

    def draw_petting_hand(self, p: QPainter, w: int, h: int, t: float) -> None:
        # The hand is a generic overlay; reuse the fallback's.
        self._fallback.draw_petting_hand(p, w, h, t)

    # --- loading + caching ----------------------------------------------
    def _resolve(self, species_key: str, state_name: str, stage: Stage) -> _Anim | None:
        cache_key = (species_key, state_name, stage)
        if cache_key not in self._cache:
            self._cache[cache_key] = self._load(species_key, state_name, stage)
        return self._cache[cache_key]

    def _load(self, species_key: str, state_name: str, stage: Stage) -> _Anim | None:
        if not species_key:
            return None
        folder = self._root / species_key

        # An egg always looks like an egg: only use art if it's egg-specific,
        # else fall through to the procedural egg drawing.
        if stage is Stage.EGG:
            return self._load_file(folder, f"{state_name}_egg.png")

        # A baby always uses the self-drawn ball creature (a distinct, cuter
        # life stage) — fall through so AssetProvider defers to the procedural
        # sprite, which draws the species' ball form at baby size.
        if stage is Stage.BABY:
            return None

        # Adult: the default sheet.
        return self._load_file(folder, f"{state_name}.png")

    def _load_file(self, folder: Path, name: str) -> _Anim | None:
        png = folder / name
        if not png.exists():
            return None
        pm = QPixmap(str(png))
        if pm.isNull():
            return None
        frames, fps = 1, 8.0
        meta = png.with_suffix(".json")
        if meta.exists():
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                frames = max(1, int(m.get("frames", 1)))
                fps = float(m.get("fps", 8.0))
            except (ValueError, OSError):
                pass
        return _Anim(pm, frames, fps)

    # --- drawing ---------------------------------------------------------
    def _blit(self, p: QPainter, ctx: SpriteContext, anim: _Anim) -> None:
        pm = anim.pixmap
        fw = pm.width() / anim.frames
        fh = float(pm.height())
        idx = int(ctx.t * anim.fps) % anim.frames if anim.frames > 1 else 0
        src = QRectF(idx * fw, 0.0, fw, fh)

        # Fit inside the sprite box, preserve aspect, bottom aligned (feet on
        # the floor line). Normally horizontally centred; while climbing, hug
        # the wall side so the pet sits flush against the window edge. (The
        # mirror transform below flips dx to the correct side for facing<0, so
        # ctx.w - dw lands flush against whichever wall it's climbing.)
        scale = min(ctx.w / fw, ctx.h / fh) * anim.scale
        dw, dh = fw * scale, fh * scale
        dx = (ctx.w - dw) if ctx.state is State.CLIMB else (ctx.w - dw) / 2.0
        dy = ctx.h - dh

        p.save()
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if ctx.facing < 0:  # mirror to face left
            p.translate(ctx.w, 0)
            p.scale(-1, 1)
        p.drawPixmap(QRectF(dx, dy, dw, dh), pm, src)
        p.restore()
