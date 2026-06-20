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
    # --- climbing a window's side face ---
    climbing: bool = False
    climb_target_top: float = 0.0   # y to settle onto once the top is reached
    climb_settle_x: float = 0.0     # x to move to (onto the edge) at the top
    climb_facing: int = 1           # which way the pet faces the wall (+1 / -1)


@dataclass
class StepResult:
    landed: bool = False     # transitioned from airborne to grounded this step
    hit_left: bool = False
    hit_right: bool = False
    started_climb: bool = False  # grabbed a window wall this step
    land_impact: float = 0.0     # downward speed at the moment of landing (px/s)


def _covered(cx: float, top: float, platforms, own_z: int) -> bool:
    """True if point (cx, top) lies inside a window strictly above ``own_z``."""
    for q in platforms:
        if q.z < own_z and q.left <= cx <= q.right and q.top <= top <= q.bottom:
            return True
    return False


def _find_climb_wall(body: Body, old_x: float, platforms):
    """A window side face the walking pet just bumped into, or None.

    Returns ``(platform, side)`` where ``side`` is +1 if the window is to the
    pet's right (climb its LEFT face) or -1 if to the left (climb its RIGHT
    face). Only walls whose top is above the pet's head (so there's something to
    climb) and that are exposed (not occluded by a higher window) qualify.
    """
    head_y = body.y
    for p in platforms:
        if not (p.top < head_y < p.bottom):  # head inside the face, below its top
            continue
        if body.vx > 0:  # walking right into a window's left face
            if old_x + body.width <= p.left <= body.x + body.width and not _covered(
                p.left, head_y, platforms, p.z
            ):
                return p, 1
        elif body.vx < 0:  # walking left into a window's right face
            if body.x <= p.right <= old_x and not _covered(
                p.right, head_y, platforms, p.z
            ):
                return p, -1
    return None


def _climb_wall_present(body: Body, platforms) -> bool:
    """True while a wall still supports the climb (window may move/close)."""
    tol = 8.0
    feet_y = body.y + body.height
    for p in platforms:
        edge = p.left if body.climb_facing > 0 else p.right
        own = body.x + body.width if body.climb_facing > 0 else body.x
        if abs(edge - own) <= tol and p.top <= feet_y <= p.bottom and not _covered(
            edge, feet_y, platforms, p.z
        ):
            return True
    return False


def step(body: Body, bounds: Bounds, dt: float, platforms=()) -> StepResult:
    """Advance one fixed timestep. Mutates ``body``; returns collision events."""
    result = StepResult()

    # --- climbing: move straight up the wall, no gravity ---
    if body.climbing:
        body.y += body.vy * dt  # vy is negative (upward); x stays locked
        feet = body.y + body.height
        if feet <= body.climb_target_top or body.y <= 0:
            # Top reached: hop onto the edge; next step's gravity settles it.
            body.x = body.climb_settle_x
            body.y = min(body.y, body.climb_target_top - body.height)
            body.climbing = False
            body.vy = 0.0
        elif not _climb_wall_present(body, platforms):
            body.climbing = False  # wall vanished -> fall
            body.vy = 0.0
        body.on_ground = False
        body.on_platform = False
        return result

    old_feet = body.y + body.height
    old_x = body.x
    was_grounded = body.on_ground

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

    # Grab a climbable window wall if we walked into one.
    if was_grounded and body.vx != 0.0 and not (result.hit_left or result.hit_right):
        wall = _find_climb_wall(body, old_x, platforms)
        if wall is not None:
            p, side = wall
            if side > 0:                       # window on the right; climb left face
                body.x = p.left - body.width
                body.climb_settle_x = p.left
            else:                              # window on the left; climb right face
                body.x = p.right
                body.climb_settle_x = p.right - body.width
            body.climb_facing = side
            body.climb_target_top = p.top
            body.climbing = True
            body.vy = 0.0
            body.on_ground = False
            body.on_platform = False
            result.started_climb = True
            return result

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
            result.land_impact = body.vy  # impact speed before we zero it
        body.vy = 0.0
        body.on_ground = True
        body.on_platform = best_is_platform
    else:
        body.on_ground = False
        body.on_platform = False

    # Safety net: never let the pet sink below the desktop floor (e.g. dropped
    # below the taskbar line), where the landing check above can't catch it.
    if body.y + body.height > bounds.floor:
        body.y = bounds.floor - body.height
        if not body.on_ground:
            result.landed = True
            result.land_impact = body.vy
        if body.vy > 0:
            body.vy = 0.0
        body.on_ground = True
        body.on_platform = False

    return result
