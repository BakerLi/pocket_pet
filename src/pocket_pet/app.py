"""World orchestrator: owns screen bounds, the live pet windows, and the tray.

Kept thin on purpose — settings and multi-monitor handling will grow here.
"""

from __future__ import annotations

import random

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .config import MAX_POOPS, PET_SIZE, PLATFORM_POLL_MS, SAVE_INTERVAL_MS
from .core.pet import Pet
from .core.physics import Bounds, Platform
from .platform import winapi
from .sim.needs import Needs
from .sim.persistence import save_needs
from .sim.species import Identity
from .ui.pet_window import PetWindow
from .ui.poop import PoopWindow
from .ui.tray import build_tray


class World:
    def __init__(self):
        screen_w, _ = winapi.primary_screen_size()
        floor = winapi.primary_work_area()[3]
        self.bounds = Bounds(left=0, right=screen_w, floor=floor)
        self.pet_window: PetWindow | None = None  # exactly one pet at a time
        self.poops: list[PoopWindow] = []
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
        # Never perch on our own pet or its poops.
        skip = {p.hwnd for p in self.poops}
        if self.pet_window:
            skip.add(self.pet_window.hwnd)
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
        weight: float = 3.5,
    ) -> PetWindow:
        """Create the pet window. Called once at startup (one pet at a time)."""
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
            weight=weight,
        )
        window = PetWindow(pet, self)
        window.show()
        self.pet_window = window
        return window

    def spawn_poop(self, x: float, y: float) -> None:
        """Drop a poop at (x, y) physical px, unless we're at the cap."""
        if len(self.poops) >= MAX_POOPS:
            return
        poop = PoopWindow(self, x, y)
        self.poops.append(poop)

    def clean_poop(self, poop: PoopWindow) -> None:
        if poop in self.poops:
            self.poops.remove(poop)
            poop.shutdown()

    def recall_pet(self) -> None:
        """Bring a lost pet back: re-drop it at center-top with a clean state."""
        if self.pet_window is None:
            return
        b = self.pet_window.pet.body
        b.x = self.bounds.right * 0.45
        b.y = 60.0
        b.vx = b.vy = 0.0
        b.held = False
        b.climbing = False
        b.on_ground = False

    def save_state(self) -> None:
        """Persist the pet's needs + age + weight."""
        if self.pet_window is not None:
            pet = self.pet_window.pet
            save_needs(pet.needs, pet.age, pet.weight)

    def quit(self) -> None:
        self.save_state()
        for poop in self.poops:
            poop.shutdown()
        self.poops.clear()
        QApplication.quit()
