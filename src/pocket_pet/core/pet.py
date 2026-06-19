"""The Pet entity: body + brain + needs + identity + age, advanced per tick.

Still OS-agnostic — no Qt, no Win32. The UI layer owns the timer and rendering.
"""

from __future__ import annotations

import random

from ..sim.growth import Stage, stage_for
from ..sim.needs import Needs
from ..sim.species import Identity, random_identity
from .physics import Body, Bounds, StepResult, step
from .state_machine import Brain, State


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
    ):
        self.bounds = bounds
        self.body = Body(x=x, y=y, width=width, height=height)
        self.brain = Brain(rng)
        self.needs = needs or Needs()
        self.identity = identity or random_identity(self.brain.rng)
        self.age = age
        self.stage = stage_for(age)

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

        if self.body.held:
            self.brain.state = State.DRAG
            return StepResult()

        result = step(self.body, self.bounds, dt, platforms)
        self.brain.react(
            self.body, result, dt,
            needs=None if is_egg else self.needs,
            can_walk=not is_egg,
        )
        return result
