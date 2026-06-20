"""Speech-bubble lines, chosen from the pet's needs and what just happened.

Returns None sometimes for ambient chatter so the pet isn't constantly talking.
"""

from __future__ import annotations

import random

from ..config import LOW_NEED
from .needs import Needs

_EVENT_LINES = {
    "greet": ["嗨!", "你來啦~", "哈囉 ♪", "嘿嘿~"],
    "feed": ["好好吃!", "謝謝你~", "再來一點?", "嗯…滿足!"],
    "pet": ["好舒服…", "嘿嘿 ♥", "最喜歡你了", "再摸一下嘛~"],
    "refuse_full": ["吃不下了…", "好飽~不要了", "等等再吃啦", "肚子好撐"],
    "refuse_sleep": ["還不睏耶", "我不想睡!", "現在很有精神~", "再玩一下嘛"],
}

_NEED_LINES = {
    "energy": ["好睏…", "想睡覺了 zzz", "撐不住了…"],
    "fullness": ["肚子餓了…", "有點餓餒", "好想吃東西…"],
    "mood": ["有點無聊…", "陪我玩嘛", "唉…", "好寂寞喔"],
}

_HAPPY_LINES = ["今天天氣真好~", "在忙什麼呢?", "♪~", "我在看著你哦", "要不要休息一下?"]


def pick(needs: Needs, event: str | None, rng: random.Random) -> str | None:
    """Pick a line. ``event`` is 'greet'/'feed'/'pet' or None for ambient."""
    if event is not None:
        return rng.choice(_EVENT_LINES[event])

    name, value = needs.lowest
    if value < LOW_NEED:
        return rng.choice(_NEED_LINES[name])

    # Content pet: stay quiet about half the time.
    if rng.random() < 0.5:
        return None
    return rng.choice(_HAPPY_LINES)
