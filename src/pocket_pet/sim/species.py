"""Species + rarity + shiny, deterministically generated from an identity string.

Like Claude Code's Buddy: the same id always hatches the same species/rarity, so
your pet is "yours". Extra pets spawned at runtime get a random identity.
"""

from __future__ import annotations

import enum
import hashlib
import random
from dataclasses import dataclass

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class Species:
    key: str
    name: str        # display name (zh)
    body: RGB        # base body colour
    edge: RGB        # outline / feet colour


# 18 species, echoing Buddy's roster.
SPECIES: list[Species] = [
    Species("duck", "鴨子", (255, 214, 102), (214, 158, 46)),
    Species("goose", "鵝", (245, 245, 250), (180, 180, 200)),
    Species("cat", "貓", (255, 190, 140), (200, 130, 90)),
    Species("rabbit", "兔子", (250, 230, 235), (210, 175, 185)),
    Species("owl", "貓頭鷹", (180, 150, 110), (120, 95, 65)),
    Species("penguin", "企鵝", (90, 110, 140), (45, 60, 85)),
    Species("turtle", "烏龜", (120, 195, 130), (70, 140, 80)),
    Species("snail", "蝸牛", (210, 180, 150), (160, 130, 100)),
    Species("dragon", "龍", (140, 110, 220), (90, 65, 160)),
    Species("octopus", "章魚", (235, 130, 170), (190, 80, 120)),
    Species("axolotl", "六角恐龍", (255, 170, 200), (225, 110, 160)),
    Species("ghost", "幽靈", (225, 230, 240), (170, 180, 200)),
    Species("robot", "機器人", (170, 185, 195), (110, 125, 135)),
    Species("blob", "史萊姆", (130, 215, 200), (70, 165, 150)),
    Species("cactus", "仙人掌", (120, 185, 110), (70, 135, 65)),
    Species("mushroom", "蘑菇", (230, 120, 110), (180, 70, 65)),
    Species("chonk", "胖胖", (200, 175, 230), (150, 120, 190)),
    Species("capybara", "水豚", (175, 140, 105), (125, 95, 65)),
]


class Rarity(enum.Enum):
    COMMON = ("普通", 60, (150, 160, 170))
    UNCOMMON = ("罕見", 25, (90, 190, 120))
    RARE = ("稀有", 13, (90, 150, 235))
    LEGENDARY = ("傳說", 2, (235, 175, 60))

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def weight(self) -> int:
        return self.value[1]

    @property
    def color(self) -> RGB:
        return self.value[2]


SHINY_CHANCE = 0.01


@dataclass(frozen=True)
class Identity:
    species: Species
    rarity: Rarity
    shiny: bool

    @property
    def display(self) -> str:
        star = " ✨" if self.shiny else ""
        return f"{self.species.name}{star}"


def _weighted_rarity(rng: random.Random) -> Rarity:
    tiers = list(Rarity)
    total = sum(r.weight for r in tiers)
    roll = rng.uniform(0, total)
    acc = 0.0
    for r in tiers:
        acc += r.weight
        if roll <= acc:
            return r
    return Rarity.COMMON


def generate(seed_id: str) -> Identity:
    """Deterministic identity from a stable id string."""
    digest = hashlib.sha256(seed_id.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big")
    rng = random.Random(seed)
    species = rng.choice(SPECIES)
    rarity = _weighted_rarity(rng)
    shiny = rng.random() < SHINY_CHANCE
    return Identity(species=species, rarity=rarity, shiny=shiny)


def random_identity(rng: random.Random) -> Identity:
    """A fresh random identity for extra pets (not tied to the device)."""
    return Identity(
        species=rng.choice(SPECIES),
        rarity=_weighted_rarity(rng),
        shiny=rng.random() < SHINY_CHANCE,
    )
