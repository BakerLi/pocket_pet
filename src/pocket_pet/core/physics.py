"""Kinematics + collision against a floor, side walls, and window platforms.

OS-agnostic: everything operates on plain numbers in an abstract physical-pixel
space. The caller supplies :class:`Bounds` and a list of :class:`Platform`
(window top edges); the UI layer fills those from the Win32 work area and window
enumeration.

Platforms are **one-way**: the pet lands on a platform's top edge only while
moving downward and only if its feet cross that edge this step. It can pass up
through from below. A platform is ignored at a point that a higher-z-order
window covers (so the pet never stands on a hidden edge).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import GRAVITY


@dataclass
class Bounds:
    """The world the pet lives in (physical px). y grows downward."""

    left: float
    right: float   # right screen edge (x); pet's right side clamps to this
    floor: float   # y of the ground line (work-area bottom, above taskbar)


@dataclass
class Platform:
    """A window's visual rect (physical px). Its TOP edge is the standable line.

    ``z`` is the z-order index (0 == topmost) used for occlusion tests.
    """

    left: float
    top: float
    right: float
    bottom: float
    z: int = 0


@dataclass
class Body:
    """Kinematic state of one pet (physical px)."""

    x: float
    y: float
    width: int
    height: int
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    held: bool = False        # grabbed by the cursor; physics is suspended while True
    on_platform: bool = False  # standing on a window edge (vs the desktop floor)


@dataclass
class StepResult:
    landed: bool = False     # transitioned from airborne to grounded this step
    hit_left: bool = False
    hit_right: bool = False


def _covered(cx: float, top: float, platforms, own_z: int) -> bool:
    """True if point (cx, top) lies inside a window strictly above ``own_z``."""
    for q in platforms:
        if q.z < own_z and q.left <= cx <= q.right and q.top <= top <= q.bottom:
            return True
    return False


def step(body: Body, bounds: Bounds, dt: float, platforms=()) -> StepResult:
    """Advance one fixed timestep. Mutates ``body``; returns collision events."""
    result = StepResult()
    old_feet = body.y + body.height

    body.vy += GRAVITY * dt
    body.x += body.vx * dt
    body.y += body.vy * dt

    # Side walls (screen edges).
    if body.x <= bounds.left:
        body.x = bounds.left
        body.vx = 0.0
        result.hit_left = True
    right_limit = bounds.right - body.width
    if body.x >= right_limit:
        body.x = right_limit
        body.vx = 0.0
        result.hit_right = True

    new_feet = body.y + body.height
    cx = body.x + body.width / 2.0

    # Landing: only while moving (or resting) downward, only surfaces the feet
    # cross this step. Pick the highest such surface (first one hit going down).
    best_top = None
    best_is_platform = False
    if body.vy >= 0:
        # Desktop floor spans the whole width and is always exposed.
        if old_feet <= bounds.floor <= new_feet:
            best_top = bounds.floor
            best_is_platform = False
        for p in platforms:
            if not (p.left <= cx <= p.right):
                continue
            if not (old_feet <= p.top <= new_feet):
                continue
            if _covered(cx, p.top, platforms, p.z):
                continue
            if best_top is None or p.top < best_top:
                best_top = p.top
                best_is_platform = True

    if best_top is not None:
        body.y = best_top - body.height
        if not body.on_ground:
            result.landed = True
        body.vy = 0.0
        body.on_ground = True
        body.on_platform = best_is_platform
    else:
        body.on_ground = False
        body.on_platform = False

    return result
