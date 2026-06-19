"""The pet's needs: fullness, mood, energy (each 0..100, higher = better).

Pure model, OS-agnostic. Decays over time; interactions top stats back up.
Offline catch-up is just :meth:`decay` called with the elapsed seconds.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import (
    ENERGY_DECAY,
    ENERGY_RECOVER,
    FEED_AMOUNT,
    FULLNESS_DECAY,
    MOOD_DECAY,
    PET_MOOD_BOOST,
    STARVING_MOOD_FACTOR,
)


def _clamp(v: float) -> float:
    return 100.0 if v > 100.0 else 0.0 if v < 0.0 else v


@dataclass
class Needs:
    fullness: float = 100.0
    mood: float = 100.0
    energy: float = 100.0

    def decay(self, seconds: float, sleeping: bool = False) -> None:
        """Advance the needs by ``seconds`` of elapsed time.

        Works for both a single 1/60 s frame and a multi-hour offline gap.
        """
        if seconds <= 0:
            return
        self.fullness = _clamp(self.fullness - FULLNESS_DECAY * seconds)

        mood_rate = MOOD_DECAY * (STARVING_MOOD_FACTOR if self.fullness <= 0 else 1.0)
        self.mood = _clamp(self.mood - mood_rate * seconds)

        if sleeping:
            self.energy = _clamp(self.energy + ENERGY_RECOVER * seconds)
        else:
            self.energy = _clamp(self.energy - ENERGY_DECAY * seconds)

    # --- interactions ----------------------------------------------------
    def feed(self, amount: float = FEED_AMOUNT) -> None:
        self.fullness = _clamp(self.fullness + amount)
        self.mood = _clamp(self.mood + 5.0)

    def stroke(self, amount: float = PET_MOOD_BOOST) -> None:
        self.mood = _clamp(self.mood + amount)

    # --- queries ---------------------------------------------------------
    @property
    def lowest(self) -> tuple[str, float]:
        """(name, value) of the most-depleted need."""
        return min(
            (("energy", self.energy), ("fullness", self.fullness), ("mood", self.mood)),
            key=lambda kv: kv[1],
        )

    # --- serialization ---------------------------------------------------
    def to_dict(self) -> dict:
        return {"fullness": self.fullness, "mood": self.mood, "energy": self.energy}

    @classmethod
    def from_dict(cls, d: dict) -> "Needs":
        return cls(
            fullness=_clamp(float(d.get("fullness", 100.0))),
            mood=_clamp(float(d.get("mood", 100.0))),
            energy=_clamp(float(d.get("energy", 100.0))),
        )
