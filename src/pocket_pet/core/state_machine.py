"""The pet's tiny behavior brain: decides where it wants to go.

Phase 1 states: IDLE, WALK, FALL. The brain only sets *intent* (``body.vx``)
and bookkeeping (``state``, ``facing``); :mod:`physics` does the integration and
reports back collision events the brain reacts to.
"""

from __future__ import annotations

import enum
import random

from ..config import (
    CLIMB_CHANCE,
    CLIMB_MAX_SECONDS,
    CLIMB_SPEED,
    IDLE_DURATION,
    JUMP_CHANCE,
    JUMP_VELOCITY,
    SLEEP_ENTER,
    SLEEP_EXIT,
    WALK_DURATION,
    WALK_SPEED,
)
from .physics import Body, StepResult


class State(enum.Enum):
    IDLE = "idle"
    WALK = "walk"
    FALL = "fall"
    DRAG = "drag"  # being held by the cursor
    SLEEP = "sleep"  # too tired; recovering energy
    EAT = "eat"    # eating a food that dropped in (transient)
    PET = "pet"    # being petted (transient)
    CLIMB = "climb"  # scaling a window's side edge


# States that play out for a fixed time and freeze ordinary movement.
_REACTION_STATES = (State.EAT, State.PET)


class Brain:
    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.state = State.IDLE
        self.facing = 1  # +1 right, -1 left
        self._timer = self._roll(IDLE_DURATION)
        self._react_t = 0.0  # remaining time in a transient reaction state
        self._climb_t = 0.0  # remaining climb time before giving up

    def _roll(self, span: tuple[float, float]) -> float:
        return self.rng.uniform(*span)

    def start_reaction(self, state: State, duration: float) -> None:
        """Enter a transient state (EAT/PET) held for ``duration`` seconds.

        Ignored while airborne, dragged, or asleep — the pet must be settled
        for the little animation to read.
        """
        if self.state in (State.FALL, State.DRAG, State.SLEEP):
            return
        self.state = state
        self._react_t = duration

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
        # Climbing a window wall (physics keeps body.climbing in sync).
        if body.climbing:
            if result.started_climb:
                # Sometimes just turn around instead of committing to a climb.
                if self.rng.random() >= CLIMB_CHANCE:
                    body.climbing = False
                    self.facing = -body.climb_facing
                    return
                self._climb_t = CLIMB_MAX_SECONDS
            self.state = State.CLIMB
            self.facing = body.climb_facing
            body.vx = 0.0
            body.vy = -CLIMB_SPEED
            self._climb_t -= dt
            if self._climb_t <= 0:
                body.climbing = False  # give up -> gravity resumes next step
            return

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

        # Transient reactions (eating / being petted) play out, then return.
        if self.state in _REACTION_STATES:
            body.vx = 0.0
            self._react_t -= dt
            if self._react_t <= 0:
                self._enter_idle()
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
            # Every so often, do a playful little hop (but not off a perch).
            if not body.on_platform and self.rng.random() < JUMP_CHANCE * dt:
                body.vy = JUMP_VELOCITY
                body.on_ground = False
                return
            if self._timer <= 0:
                self._enter_walk()
        elif self.state is State.WALK:
            body.vx = WALK_SPEED * self.facing
            if self._timer <= 0:
                self._enter_idle()
