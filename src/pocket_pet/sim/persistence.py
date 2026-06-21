"""Save/load the pet's needs to %APPDATA%/pocket_pet/pet.json.

The save stamps wall-clock time; on load we apply the elapsed gap as decay so
the pet is appropriately hungry/tired when you come back ("offline catch-up").
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .needs import Needs

SAVE_VERSION = 1


def save_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "pocket_pet"


def save_path() -> Path:
    return save_dir() / "pet.json"


def dev_mode_enabled() -> bool:
    """Developer mode (e.g. the revive backdoor) is on if EITHER:

    * the env var ``POCKET_PET_DEV`` is set, or
    * a file named ``dev`` exists in the save dir (%APPDATA%/pocket_pet/dev).

    The file is the easy way for a double-clicked exe — just create an empty
    file there and relaunch.
    """
    from ..config import DEV_ENV

    if os.environ.get(DEV_ENV):
        return True
    try:
        return (save_dir() / "dev").exists()
    except OSError:
        return False


def time_scale() -> float:
    """Dev time-acceleration factor for the whole life-sim (needs/digestion/
    growth/death timers). 1.0 = normal.

    Controlled by EITHER the env var ``POCKET_PET_SPEED`` or a file named
    ``speed`` in the save dir whose contents are the factor (e.g. ``60``). An
    empty/invalid value defaults to 60x. Clamped to [1, 100000].
    """
    raw = os.environ.get("POCKET_PET_SPEED")
    if raw is None:
        try:
            f = save_dir() / "speed"
            raw = f.read_text(encoding="utf-8").strip() if f.exists() else None
        except OSError:
            raw = None
    if raw is None:
        return 1.0
    try:
        val = float(raw)
    except ValueError:
        val = 60.0  # file present but empty/garbage -> a sensible default
    return max(1.0, min(100000.0, val))


def save_needs(
    needs: Needs,
    age: float = 0.0,
    weight: float = 3.5,
    dead: bool = False,
    death_cause: str = "",
    death_age: float = 0.0,
    death_flavour: str = "",
) -> None:
    d = save_dir()
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": SAVE_VERSION,
        "last_saved": time.time(),
        "age": age,
        "weight": weight,
        "needs": needs.to_dict(),
        "death": {
            "dead": dead,
            "cause": death_cause,
            "age": death_age,
            "flavour": death_flavour,
        },
    }
    tmp = save_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(save_path())  # atomic-ish: avoid a half-written save


_NO_DEATH = {"dead": False, "cause": "", "age": 0.0, "flavour": ""}


def load_needs() -> tuple[Needs | None, float, float, float, dict]:
    """Return (needs, elapsed_seconds, age_seconds, weight, death); needs None if no save.

    Offline decay is already applied; the pet also ages by the elapsed time.
    A dead pet's needs/age aren't decayed (it stays as it died).
    """
    path = save_path()
    if not path.exists():
        return None, 0.0, 0.0, 3.5, dict(_NO_DEATH)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, 0.0, 0.0, 3.5, dict(_NO_DEATH)

    death = {**_NO_DEATH, **data.get("death", {})}
    needs = Needs.from_dict(data.get("needs", {}))
    elapsed = max(0.0, time.time() - float(data.get("last_saved", time.time())))
    age = float(data.get("age", 0.0))
    if not death["dead"]:
        needs.decay(elapsed, sleeping=False)
        age += elapsed
    weight = float(data.get("weight", 3.5))
    return needs, elapsed, age, weight, death
