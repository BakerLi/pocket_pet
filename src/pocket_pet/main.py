"""Entry point.

    .venv/Scripts/python.exe -m pocket_pet.main

Right-click the pet to quit (a proper tray menu lands in Phase 2).
"""

from __future__ import annotations

import sys


def main() -> int:
    # DPI awareness MUST be set before QApplication is constructed.
    from .platform import winapi

    winapi.set_dpi_awareness()

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    # Pets live in the tray, not the taskbar; don't quit when a pet is released.
    app.setQuitOnLastWindowClosed(False)

    from .app import World
    from .sim import species
    from .sim.persistence import load_needs

    world = World()
    world.start_tray()

    # The primary pet's species is deterministic from this machine+user (à la Buddy).
    identity = species.generate(winapi.device_id())

    saved, elapsed, age, weight, death = load_needs()
    pet = world.spawn(needs=saved, identity=identity, age=age, weight=weight, death=death)
    if saved is not None and elapsed > 60 and not death.get("dead"):
        mins = int(elapsed // 60)
        pet._say(f"你回來啦~ (離開了 {mins} 分鐘)")

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
