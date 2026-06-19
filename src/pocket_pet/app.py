"""World orchestrator: owns screen bounds, the live pet windows, and the tray.

Kept thin on purpose — settings and multi-monitor handling will grow here.
"""

from __future__ import annotations

import random

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .config import PET_SIZE, PLATFORM_POLL_MS, SAVE_INTERVAL_MS
from .core.pet import Pet
from .core.physics import Bounds, Platform
from .platform import winapi
from .sim.needs import Needs
from .sim.persistence import save_needs
from .sim.species import Identity
from .ui.pet_window import PetWindow
from .ui.tray import build_tray


class World:
    def __init__(self):
        screen_w, _ = winapi.primary_screen_size()
        floor = winapi.primary_work_area()[3]
        self.bounds = Bounds(left=0, right=screen_w, floor=floor)
        self.windows: list[PetWindow] = []
        self.platforms: list[Platform] = []
        self.tray = None

        # Poll other windows on a slow timer; pets read self.platforms each frame.
        self._poll = QTimer()
        self._poll.timeout.connect(self.refresh_platforms)
        self._poll.start(PLATFORM_POLL_MS)
        self.refresh_platforms()

        # Autosave the primary pet's needs.
        self._save = QTimer()
        self._save.timeout.connect(self.save_state)
        self._save.start(SAVE_INTERVAL_MS)

    def refresh_platforms(self) -> None:
        """Rebuild the perch-platform list from current top-level windows."""
        skip = {w.hwnd for w in self.windows}  # never perch on our own pets
        wins = winapi.enum_top_level_windows(skip_hwnds=skip)
        self.platforms = [
            Platform(left=l, top=t, right=r, bottom=b, z=i)
            for i, w in enumerate(wins)
            for (l, t, r, b) in (w["rect"],)
        ]

    def start_tray(self) -> None:
        self.tray = build_tray(self)

    def spawn(
        self,
        rng: random.Random | None = None,
        needs: Needs | None = None,
        identity: Identity | None = None,
        age: float = 0.0,
    ) -> PetWindow:
        rng = rng or random.Random()
        pet = Pet(
            self.bounds,
            width=PET_SIZE,
            height=PET_SIZE,
            x=self.bounds.right * 0.45,
            y=60.0,  # start in the air so it falls in on launch
            rng=rng,
            needs=needs,
            identity=identity,
            age=age,
        )
        window = PetWindow(pet, self)
        window.show()
        self.windows.append(window)
        return window

    def remove(self, window: PetWindow) -> None:
        if window in self.windows:
            self.windows.remove(window)
            window.shutdown()

    def save_state(self) -> None:
        """Persist the primary (first) pet's needs + age. Multi-pet save is later."""
        if self.windows:
            pet = self.windows[0].pet
            save_needs(pet.needs, pet.age)

    def quit(self) -> None:
        self.save_state()
        QApplication.quit()
