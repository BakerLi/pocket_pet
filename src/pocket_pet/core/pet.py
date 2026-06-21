"""The Pet entity: body + brain + needs + identity + age, advanced per tick.

Still OS-agnostic — no Qt, no Win32. The UI layer owns the timer and rendering.
"""

from __future__ import annotations

import random

from ..config import (
    CAUSE_DEPRESS,
    CAUSE_ILLNESS,
    CAUSE_STARVE,
    DEATH_FLAVOURS,
    DEPRESS_DEATH_SECONDS,
    DIGEST_RATE,
    GUT_PER_FULLNESS,
    POOP_AMOUNT,
    SICK_HYGIENE,
    SICK_ONSET_CHANCE,
    STARVE_DEATH_SECONDS,
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
        dead: bool = False,
        death_cause: str = "",
        death_age: float = 0.0,
        death_flavour: str = "",
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
        # Death (permanent until a dev revive).
        self.dead = dead
        self.death_cause = death_cause
        self.death_age = death_age
        self.death_flavour = death_flavour
        self._starve_t = 0.0
        self._depress_t = 0.0
        self.just_died = False  # one-shot signal for the UI

    def _die(self, cause: str) -> None:
        self.dead = True
        self.just_died = True
        self.death_cause = cause
        self.death_age = self.age
        self.death_flavour = self.brain.rng.choice(DEATH_FLAVOURS)
        b = self.body
        b.vx = b.vy = 0.0
        b.held = b.climbing = False
        b.on_ground = True
        b.y = self.bounds.floor - b.height  # the body rests; UI shows a grave

    def revive(self) -> None:
        """Developer backdoor: bring a dead pet back."""
        self.dead = False
        self.death_cause = self.death_flavour = ""
        self._starve_t = self._depress_t = 0.0
        self.needs = Needs(fullness=70, mood=70, energy=70, health=100, hygiene=90)
        self.body.y = 60.0
        self.body.vy = 0.0
        self.body.on_ground = False

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

    def update(self, dt: float, platforms=(), sim_dt: float | None = None) -> StepResult:
        """Advance the pet one frame.

        ``dt`` drives physics + animation (real time). ``sim_dt`` drives the
        life-sim (ageing, needs, digestion, sickness, death timers); it defaults
        to ``dt`` but a dev time-accelerator can pass a larger value so the
        whole life cycle runs faster WITHOUT speeding up movement.
        """
        if self.dead:
            return StepResult()  # a grave doesn't age, decay, or move
        if sim_dt is None:
            sim_dt = dt

        self.age += sim_dt
        self.stage = stage_for(self.age)
        is_egg = self.stage is Stage.EGG

        # Eggs don't get hungry/tired; older pets decay normally.
        if not is_egg:
            sleeping = self.brain.state is State.SLEEP
            self.needs.decay(sim_dt, sleeping=sleeping)
            # Metabolism: burn a little weight, more while actively moving.
            burn = WEIGHT_BASAL_BURN
            if self.brain.state in _MOVING:
                burn += WEIGHT_MOVE_BURN
            self.add_weight(-burn * sim_dt)

            # Digestion: move food gut -> bowel; poop when the bowel fills.
            if self.gut > 0.0:
                moved = min(self.gut, DIGEST_RATE * sim_dt)
                self.gut -= moved
                self.bowel += moved
                if self.bowel >= POOP_AMOUNT:
                    self.bowel -= POOP_AMOUNT
                    self.wants_poop = True

            # Filthy surroundings can make the pet sick (more likely the dirtier
            # it is). Once sick it stays sick until given medicine.
            if not self.needs.sick and self.needs.hygiene < SICK_HYGIENE:
                severity = (SICK_HYGIENE - self.needs.hygiene) / SICK_HYGIENE
                if self.brain.rng.random() < SICK_ONSET_CHANCE * severity * sim_dt:
                    self.needs.sick = True

            # Death from prolonged neglect or untreated illness.
            n = self.needs
            self._starve_t = self._starve_t + sim_dt if n.fullness <= 0 else 0.0
            self._depress_t = self._depress_t + sim_dt if n.mood <= 0 else 0.0
            if n.health <= 0:
                self._die(CAUSE_ILLNESS)
            elif self._starve_t >= STARVE_DEATH_SECONDS:
                self._die(CAUSE_STARVE)
            elif self._depress_t >= DEPRESS_DEATH_SECONDS:
                self._die(CAUSE_DEPRESS)
            if self.dead:
                return StepResult()

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
