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
    HEALTH_REGEN,
    MOOD_DECAY,
    PET_MOOD_BOOST,
    SICK_HEALTH_DECAY,
    SICK_MOOD_EXTRA,
    STARVING_MOOD_FACTOR,
)


def _clamp(v: float) -> float:
    return 100.0 if v > 100.0 else 0.0 if v < 0.0 else v


@dataclass
class Needs:
    fullness: float = 100.0
    mood: float = 100.0
    energy: float = 100.0
    health: float = 100.0    # drops while sick; cured by medicine, heals when well
    hygiene: float = 100.0   # drops while poop is left around (Phase 2)
    sick: bool = False       # ill from filth; needs medicine

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

        # Health: drained while sick (plus an extra mood hit), heals when well.
        if self.sick:
            self.health = _clamp(self.health - SICK_HEALTH_DECAY * seconds)
            self.mood = _clamp(self.mood - SICK_MOOD_EXTRA * seconds)
        else:
            self.health = _clamp(self.health + HEALTH_REGEN * seconds)

    # --- interactions ----------------------------------------------------
    def feed(self, amount: float = FEED_AMOUNT, mood_bonus: float = 5.0) -> None:
        self.fullness = _clamp(self.fullness + amount)
        self.mood = _clamp(self.mood + mood_bonus)

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
        return {
            "fullness": self.fullness,
            "mood": self.mood,
            "energy": self.energy,
            "health": self.health,
            "hygiene": self.hygiene,
            "sick": self.sick,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Needs":
        return cls(
            fullness=_clamp(float(d.get("fullness", 100.0))),
            mood=_clamp(float(d.get("mood", 100.0))),
            energy=_clamp(float(d.get("energy", 100.0))),
            health=_clamp(float(d.get("health", 100.0))),
            hygiene=_clamp(float(d.get("hygiene", 100.0))),
            sick=bool(d.get("sick", False)),
        )
