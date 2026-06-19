"""The drawing seam: how a pet is rendered, abstracted from what draws it.

Everything the UI needs to render one frame of a pet is bundled into
:class:`SpriteContext`; a :class:`SpriteProvider` turns that into pixels. Today
the only implementation is the procedural QPainter one
(:class:`pocket_pet.ui.sprite.ProceduralProvider`), but this seam lets an
asset-backed provider (PNG/SVG per species) drop in later — even per species,
falling back to procedural where art is missing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from PySide6.QtGui import QColor, QPainter

from ..core.state_machine import State
from ..sim.growth import Stage


@dataclass(frozen=True)
class SpriteContext:
    """Everything needed to render one frame of a pet (no Qt widget state)."""

    w: int
    h: int
    state: State
    facing: int          # +1 right, -1 left
    t: float             # accumulating animation time (seconds)
    vy: float            # vertical velocity (used by some fall poses)
    sad: bool            # low mood/fullness -> droopy face
    stage: Stage         # egg / baby / adult
    body_color: QColor
    edge_color: QColor
    species_key: str     # e.g. "rabbit", drives species-specific features


class SpriteProvider(ABC):
    """Renders a pet from a :class:`SpriteContext`."""

    @abstractmethod
    def draw(self, p: QPainter, ctx: SpriteContext) -> None:
        """Draw the pet for this frame into ``p``."""

    @abstractmethod
    def draw_petting_hand(self, p: QPainter, w: int, h: int, t: float) -> None:
        """Draw the stroking-hand overlay shown while the pet is petted."""
