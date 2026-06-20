"""The Pet entity: body + brain + needs + identity + age, advanced per tick.

Still OS-agnostic — no Qt, no Win32. The UI layer owns the timer and rendering.
"""

from __future__ import annotations

import random

from ..config import (
    DIGEST_RATE,
    GUT_PER_FULLNESS,
    POOP_AMOUNT,
    SICK_HYGIENE,
    SICK_ONSET_CHANCE,
    WEIGHT_BASAL_BURN,
    WEIGHT_MAX,
    WEIGHT_MIN,
    WEIGHT_MOVE_BURN,
    WEIGHT_PER_FULLNESS,
    WEIGHT_START,
)
from ..sim.growth import Stage, stage_for
from ..sim.needs import Needs
from ..sim.species import Identity, random_identity
from .physics import Body, Bounds, StepResult, step
from .state_machine import Brain, State

_MOVING = (State.WALK, State.RUN, State.CLIMB)


def _clamp_weight(kg: float) -> float:
    return max(WEIGHT_MIN, min(WEIGHT_MAX, kg))


class Pet:
    def __init__(
        self,
        bounds: Bounds,
        width: int,
        height: int,
        x: float,
        y: float,
        rng: random.Random | None = None,
        needs: Needs | None = None,
        identity: Identity | None = None,
        age: float = 0.0,
        weight: float = WEIGHT_START,
    ):
        self.bounds = bounds
        self.body = Body(x=x, y=y, width=width, height=height)
        self.brain = Brain(rng)
        self.needs = needs or Needs()
        self.identity = identity or random_identity(self.brain.rng)
        self.age = age
        self.stage = stage_for(age)
        self.weight = _clamp_weight(weight)
        # Digestion: gut (undigested food) -> bowel -> poop.
        self.gut = 0.0
        self.bowel = 0.0
        self.wants_poop = False  # set when a poop should drop; UI consumes it

    def add_weight(self, kg: float) -> None:
        self.weight = _clamp_weight(self.weight + kg)

    def gain_from_food(self, fullness_restored: float) -> None:
        self.add_weight(fullness_restored * WEIGHT_PER_FULLNESS)
        self.gut += GUT_PER_FULLNESS * fullness_restored

    @property
    def state(self) -> State:
        return self.brain.state

    @property
    def facing(self) -> int:
        return self.brain.facing

    def update(self, dt: float, platforms=()) -> StepResult:
        """Integrate age + needs + physics, then let the brain react."""
        self.age += dt
        self.stage = stage_for(self.age)
        is_egg = self.stage is Stage.EGG

        # Eggs don't get hungry/tired; older pets decay normally.
        if not is_egg:
            sleeping = self.brain.state is State.SLEEP
            self.needs.decay(dt, sleeping=sleeping)
            # Metabolism: burn a little weight, more while actively moving.
            burn = WEIGHT_BASAL_BURN
            if self.brain.state in _MOVING:
                burn += WEIGHT_MOVE_BURN
            self.add_weight(-burn * dt)

            # Digestion: move food gut -> bowel; poop when the bowel fills.
            if self.gut > 0.0:
                moved = min(self.gut, DIGEST_RATE * dt)
                self.gut -= moved
                self.bowel += moved
                if self.bowel >= POOP_AMOUNT:
                    self.bowel -= POOP_AMOUNT
                    self.wants_poop = True

            # Filthy surroundings can make the pet sick (more likely the dirtier
            # it is). Once sick it stays sick until given medicine.
            if not self.needs.sick and self.needs.hygiene < SICK_HYGIENE:
                severity = (SICK_HYGIENE - self.needs.hygiene) / SICK_HYGIENE
                if self.brain.rng.random() < SICK_ONSET_CHANCE * severity * dt:
                    self.needs.sick = True

        if self.body.held:
            self.body.climbing = False  # grabbing interrupts a climb
            self.brain.state = State.DRAG
            return StepResult()

        result = step(self.body, self.bounds, dt, platforms)
        self.brain.react(
            self.body, result, dt,
            needs=None if is_egg else self.needs,
            can_walk=not is_egg,
        )
        return result
