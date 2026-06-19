"""Convert a Shimeji art pack (one PNG per frame) into our sheet+JSON format.

Shimeji stores each frame as a separate image (shime1.png, shime2.png, ...) and
an ``actions.xml`` listing which frames make up each animation. Our AssetProvider
wants ONE horizontal sprite-sheet PNG per state plus a small JSON
(``{"frames": N, "fps": F}``). This tool bridges the two: it picks the frames
for each of our states, composites them onto uniform cells (aligned by each
frame's ImageAnchor so they don't jitter), optionally mirrors them to face
right, and writes ``<state>.png`` + ``<state>.json`` into the species folder.

Usage:
    .venv/Scripts/python.exe tools/shimeji_to_sheets.py \
        "assets/sprites/Bunny Shimeji/img/Light Brown Bunny" rabbit

Shimeji art faces left by default; we mirror so the baseline faces right (our
AssetProvider mirrors back for left-facing). Attribution/licence: see the pack's
licence.txt — keep it with any redistribution.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

CELL = 128  # Shimeji frames are 128x128 with anchor ~ (64,128) = bottom-centre

# Our state -> (list of shime frame stems, fps, anchor (ax,ay)).
# Derived from the pack's conf/actions.xml (one clean cycle per state).
MAPPING = {
    # Stand: mostly still with an occasional blink (shime1a).
    "idle":  (["shime1"] * 5 + ["shime1a"], 6.0, (64, 128)),
    "walk":  (["shime2", "shime3", "shime3a", "shime3b", "shime3c", "shime3d"], 10.0, (64, 128)),
    "fall":  (["shime4"], 1.0, (64, 128)),
    # Pinched (dragged): the centred dangle frames.
    "drag":  (["shime5a", "shime5ab"], 3.0, (64, 128)),
    # Sprawl: laying down -> our sleep.
    "sleep": (["shime20", "shime21"], 1.5, (64, 128)),
    # CleanAction (grooming) is the closest analogue to eating.
    "eat":   (["shime15", "shime16", "shime17", "shime27", "shime28"], 8.0, (64, 128)),
    "pet":   ([f"shime{n}" for n in range(45, 58)], 12.0, (64, 128)),
    # ClimbWall going up: a short clean cycle. (Anchor is 50,128 in the pack.)
    "climb": (["shime14", "shime12", "shime13"], 8.0, (50, 128)),
}


def _cell(src: QImage, anchor: tuple[int, int], flip: bool) -> QImage:
    """Composite one source frame onto a CELL, aligned by its anchor."""
    cell = QImage(CELL, CELL, QImage.Format_ARGB32)
    cell.fill(Qt.transparent)
    ax, ay = anchor
    # Place the image so its anchor lands at the cell's bottom-centre.
    dx = CELL // 2 - ax
    dy = CELL - ay
    p = QPainter(cell)
    p.drawImage(dx, dy, src)
    p.end()
    return cell.mirrored(True, False) if flip else cell


def convert(src_dir: Path, out_dir: Path, flip: bool = True) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for state, (frames, fps, anchor) in MAPPING.items():
        imgs = []
        for stem in frames:
            png = src_dir / f"{stem}.png"
            if not png.exists():
                print(f"  ! {state}: missing {png.name}, skipping frame")
                continue
            src = QImage(str(png))
            if src.isNull():
                print(f"  ! {state}: unreadable {png.name}")
                continue
            imgs.append(_cell(src, anchor, flip))
        if not imgs:
            print(f"  - {state}: no frames, skipped")
            continue
        sheet = QImage(CELL * len(imgs), CELL, QImage.Format_ARGB32)
        sheet.fill(Qt.transparent)
        p = QPainter(sheet)
        for i, im in enumerate(imgs):
            p.drawImage(i * CELL, 0, im)
        p.end()
        sheet.save(str(out_dir / f"{state}.png"))
        (out_dir / f"{state}.json").write_text(
            json.dumps({"frames": len(imgs), "fps": fps}), encoding="utf-8"
        )
        print(f"  {state}: {len(imgs)} frames @ {fps}fps")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    species = sys.argv[2]
    flip = "--no-flip" not in sys.argv
    if not src.is_dir():
        print(f"source not found: {src}")
        return 1
    out = Path(__file__).resolve().parents[1] / "assets" / "sprites" / species
    print(f"Converting {src}  ->  {out}  (flip={flip})")
    QApplication(sys.argv)
    convert(src, out, flip=flip)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
