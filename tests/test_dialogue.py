"""Offline unit tests for the preset dialogue fallback."""

from __future__ import annotations

import random

import pytest

from pocket_pet.sim import dialogue
from pocket_pet.sim.needs import Needs


@pytest.mark.parametrize(
    "bucket",
    ["energy", "fullness", "mood", "sick", "greet", "feed", "pet",
     "thrown", "night", "neglected", "happy", "unknown_bucket"],
)
def test_line_for_always_returns_a_line(bucket):
    rng = random.Random(0)
    line = dialogue.line_for(bucket, rng)
    assert isinstance(line, str) and line          # never None/empty


def test_line_for_maps_known_buckets():
    rng = random.Random(1)
    assert dialogue.line_for("thrown", rng) in dialogue._EVENT_LINES["thrown"]
    assert dialogue.line_for("energy", rng) in dialogue._NEED_LINES["energy"]
    assert dialogue.line_for("sick", rng) in dialogue._SICK_LINES
    # unknown / ambient buckets fall through to the happy lines
    assert dialogue.line_for("night", rng) in dialogue._HAPPY_LINES


def test_pick_event_returns_from_event_lines():
    rng = random.Random(2)
    needs = Needs()
    assert dialogue.pick(needs, "greet", rng) in dialogue._EVENT_LINES["greet"]


def test_pick_low_need_complains():
    rng = random.Random(3)
    needs = Needs(fullness=5, mood=100, energy=100)   # hungry
    assert dialogue.pick(needs, None, rng) in dialogue._NEED_LINES["fullness"]
