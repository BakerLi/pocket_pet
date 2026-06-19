"""Growth stages driven by the pet's age (seconds). Pure model."""

from __future__ import annotations

import enum

from ..config import BABY_UNTIL, EGG_UNTIL, STAGE_SCALE


class Stage(enum.Enum):
    EGG = "egg"
    BABY = "baby"
    ADULT = "adult"

    @property
    def label(self) -> str:
        return {"egg": "蛋", "baby": "幼體", "adult": "成體"}[self.value]

    @property
    def scale(self) -> float:
        return STAGE_SCALE[self.value]


def stage_for(age_seconds: float) -> Stage:
    if age_seconds < EGG_UNTIL:
        return Stage.EGG
    if age_seconds < BABY_UNTIL:
        return Stage.BABY
    return Stage.ADULT
