"""The pet's tiny behavior brain: decides where it wants to go.

Phase 1 states: IDLE, WALK, FALL. The brain only sets *intent* (``body.vx``)
and bookkeeping (``state``, ``facing``); :mod:`physics` does the integration and
reports back collision events the brain reacts to.
"""

from __future__ import annotations

import enum
import random

from ..config import IDLE_DURATION, SLEEP_ENTER, SLEEP_EXIT, WALK_DURATION, WALK_SPEED
from .physics import Body, StepResult


class State(enum.Enum):
    IDLE = "idle"
    WALK = "walk"
    FALL = "fall"
    DRAG = "drag"  # being held by the cursor
    SLEEP = "sleep"  # too tired; recovering energy


class Brain:
    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.state = State.IDLE
        self.facing = 1  # +1 right, -1 left
        self._timer = self._roll(IDLE_DURATION)

    def _roll(self, span: tuple[float, float]) -> float:
        return self.rng.uniform(*span)

    def _enter_idle(self) -> None:
        self.state = State.IDLE
        self._timer = self._roll(IDLE_DURATION)

    def _enter_walk(self) -> None:
        self.state = State.WALK
        self.facing = self.rng.choice((-1, 1))
        self._timer = self._roll(WALK_DURATION)

    def react(
        self, body: Body, result: StepResult, dt: float, needs=None, can_walk: bool = True
    ) -> None:
        """Update behavior after a physics step and set next-frame intent."""
        # Bounced off a wall while walking -> turn around.
        if result.hit_left:
            self.facing = 1
        elif result.hit_right:
            self.facing = -1

        if not body.on_ground:
            self.state = State.FALL
            return

        if self.state in (State.FALL, State.DRAG):  # just landed / just released near ground
            self._enter_idle()

        # An egg can't walk or sleep — it just sits and wobbles.
        if not can_walk:
            self.state = State.IDLE
            body.vx = 0.0
            return

        # Need-driven sleep takes priority over idle/walk.
        if needs is not None:
            if self.state is State.SLEEP:
                body.vx = 0.0
                if needs.energy >= SLEEP_EXIT:
                    self._enter_idle()
                return
            if needs.energy <= SLEEP_ENTER:
                self.state = State.SLEEP
                body.vx = 0.0
                return

        self._timer -= dt
        if self.state is State.IDLE:
            body.vx = 0.0
            if self._timer <= 0:
                self._enter_walk()
        elif self.state is State.WALK:
            body.vx = WALK_SPEED * self.facing
            if self._timer <= 0:
                self._enter_idle()
