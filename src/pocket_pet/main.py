"""Entry point.

    .venv/Scripts/python.exe -m pocket_pet.main [options]

Dev/testing options (override who is born; not persisted):
    --species KEY     force a species (duck, cat, rabbit, dragon, ...)
    --rarity KEY      force rarity (common|uncommon|rare|legendary)
    --shiny           force shiny ✨
    --age SECONDS     start at this age (0 = egg; see growth thresholds)
    --fresh           ignore the saved pet (fresh stats, e.g. a new egg)
"""

from __future__ import annotations

import argparse
import sys


def _parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="pocket_pet", add_help=True)
    ap.add_argument("--species")
    ap.add_argument("--rarity")
    ap.add_argument("--shiny", action="store_true", default=None)
    ap.add_argument("--age", type=float)
    ap.add_argument("--fresh", action="store_true")
    # Ignore unknown args (e.g. Qt's own) so the GUI still launches.
    args, _ = ap.parse_known_args(argv)
    return args


def main() -> int:
    args = _parse_args(sys.argv[1:])

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

    # The primary pet's species is deterministic from this machine+user (à la
    # Buddy); CLI flags can override it for dev/testing.
    identity = species.generate(winapi.device_id())
    if args.species or args.rarity or args.shiny:
        identity = species.make_identity(
            identity, args.species, args.rarity, args.shiny
        )

    saved, elapsed, age, weight, death = load_needs()
    if args.fresh:  # start over, ignoring the saved pet
        saved, elapsed, age, weight, death = None, 0.0, 0.0, 3.5, {"dead": False}
    if args.age is not None:
        age = args.age

    pet = world.spawn(needs=saved, identity=identity, age=age, weight=weight, death=death)
    if saved is not None and elapsed > 60 and not death.get("dead"):
        mins = int(elapsed // 60)
        pet._say(f"你回來啦~ (離開了 {mins} 分鐘)")

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
