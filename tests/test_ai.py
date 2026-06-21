"""Offline unit tests for the AI snark module's pure logic.

No network and no config writes: we exercise the prompt builders, the response
cleaner, and the chatter-rate lookup only. The networked paths (AINarrator
refill / one-shots) are intentionally not touched here.
"""

from __future__ import annotations

import pytest

from pocket_pet.config import (
    AI_DEFAULT_CHATTER_RATE,
    AI_LINES_PER_BUCKET,
    AI_MAX_LINE_CHARS,
    CHATTER_RATES,
)
from pocket_pet.sim import ai


def _ctx():
    return {
        "species": "兔子",
        "shiny": False,
        "stage": "成年",
        "needs": {"fullness": 40, "mood": 20, "energy": 80,
                  "health": 100, "hygiene": 70, "sick": False},
        "weight": 3.5,
        "hour": 3,
        "date": "12-25",
        "recent": ["被餵了餅乾", "被摸摸"],
    }


def test_buckets_cover_events_and_extras():
    for key in ("greet", "feed", "thrown", "sick", "happy", "night",
                "neglected", "death_starve", "death_depress", "death_illness"):
        assert key in ai._BUCKETS


def test_clean_filters_and_caps():
    data = {
        "greet": ["嗨", "你來啦", "x" * (AI_MAX_LINE_CHARS + 1)],  # 3rd too long
        "feed": "not-a-list",                                     # wrong type
        "bogus": ["不該出現"],                                     # unknown bucket
        "thrown": [f"line{i}" for i in range(AI_LINES_PER_BUCKET + 3)],
    }
    out = ai._clean(data)
    assert out["greet"] == ["嗨", "你來啦"]          # over-long dropped
    assert "feed" not in out                          # non-list skipped
    assert "bogus" not in out                         # unknown bucket skipped
    assert len(out["thrown"]) == AI_LINES_PER_BUCKET  # capped


def test_clean_handles_garbage():
    assert ai._clean("nope") == {}
    assert ai._clean({"greet": [1, 2, None]}) == {}   # no usable strings


def test_batch_prompt_has_all_buckets_and_pun_hint():
    p = ai._build_prompt(_ctx())
    for key in ai._BUCKETS:
        assert key in p
    assert ai._PUN_HINT in p
    assert "兔子" in p


def test_window_prompt_includes_window():
    p = ai._build_window_prompt(_ctx(), "report.xlsx - Excel", "EXCEL.EXE")
    assert "report.xlsx - Excel" in p
    assert ai._PUN_HINT in p


def test_musing_prompt_includes_context():
    p = ai._build_musing_prompt(_ctx(), "晴 +27°C", "main.py - VS Code")
    assert "晴 +27°C" in p
    assert "main.py - VS Code" in p
    assert "被餵了餅乾" in p          # memory carried in


def test_epitaph_prompt_includes_cause_age_memory():
    p = ai._build_epitaph_prompt(_ctx(), "餓壞了", "3 天")
    assert "餓壞了" in p
    assert "3 天" in p
    assert "被摸摸" in p


def test_chatter_interval_valid_and_falls_back(monkeypatch):
    monkeypatch.setitem(ai._config, "chatter_rate", "low")
    assert ai.chatter_interval() == CHATTER_RATES["low"]
    monkeypatch.setitem(ai._config, "chatter_rate", "bogus")
    assert ai.chatter_rate() == AI_DEFAULT_CHATTER_RATE   # invalid -> default


@pytest.mark.parametrize("key", ["high", "medium", "low"])
def test_chatter_rates_are_ascending_pairs(key):
    lo, hi = CHATTER_RATES[key]
    assert 0 < lo < hi
