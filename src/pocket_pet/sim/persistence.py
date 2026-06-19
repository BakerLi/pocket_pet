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


def save_needs(needs: Needs, age: float = 0.0) -> None:
    d = save_dir()
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": SAVE_VERSION,
        "last_saved": time.time(),
        "age": age,
        "needs": needs.to_dict(),
    }
    tmp = save_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(save_path())  # atomic-ish: avoid a half-written save


def load_needs() -> tuple[Needs | None, float, float]:
    """Return (needs, elapsed_seconds, age_seconds); needs is None if no save.

    Offline decay is already applied; the pet also ages by the elapsed time.
    """
    path = save_path()
    if not path.exists():
        return None, 0.0, 0.0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, 0.0, 0.0

    needs = Needs.from_dict(data.get("needs", {}))
    elapsed = max(0.0, time.time() - float(data.get("last_saved", time.time())))
    needs.decay(elapsed, sleeping=False)
    age = float(data.get("age", 0.0)) + elapsed
    return needs, elapsed, age
