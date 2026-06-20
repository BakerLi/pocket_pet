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
    # Run: the dash cycle (faster than walk).
    "run":   (["shime3e", "shime3f", "shime3g", "shime3h", "shime3i"], 14.0, (64, 128)),
    "fall":  (["shime4"], 1.0, (64, 128)),
    # Pinched (dragged): swing through the lean poses and back (ping-pong so it
    # loops smoothly without a jump from the last frame to the first).
    "drag":  (["shime6", "shime7", "shime8", "shime9", "shime10", "shime9", "shime8", "shime7"], 6.0, (64, 128)),
    # Bouncing: the landing squash.
    "land":  (["shime18", "shime19"], 12.0, (64, 128)),
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


def _content_bbox(img: QImage):
    """(minx, miny, maxx, maxy) of non-transparent pixels, or None if empty."""
    img = img.convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()

    def row_has(y):
        return any(img.pixelColor(x, y).alpha() > 0 for x in range(w))

    def col_has(x):
        return any(img.pixelColor(x, y).alpha() > 0 for y in range(h))

    miny = next((y for y in range(h) if row_has(y)), None)
    if miny is None:
        return None
    maxy = next(y for y in range(h - 1, -1, -1) if row_has(y))
    minx = next(x for x in range(w) if col_has(x))
    maxx = next(x for x in range(w - 1, -1, -1) if col_has(x))
    return minx, miny, maxx, maxy


def convert(src_dir: Path, out_dir: Path, flip: bool = True, pad: int = 2) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for state, (frames, fps, anchor) in MAPPING.items():
        # Composite this state's frames, then crop to ONE box covering all of
        # them (shared per state => frames stay aligned, no jitter; per state =>
        # each state fills the cell instead of a global box dominated by the
        # widest pose).
        cells = []
        union = None
        for stem in frames:
            png = src_dir / f"{stem}.png"
            if not png.exists():
                print(f"  ! {state}: missing {png.name}, skipping frame")
                continue
            src = QImage(str(png))
            if src.isNull():
                print(f"  ! {state}: unreadable {png.name}")
                continue
            cell = _cell(src, anchor, flip)
            cells.append(cell)
            bb = _content_bbox(cell)
            if bb:
                union = bb if union is None else (
                    min(union[0], bb[0]), min(union[1], bb[1]),
                    max(union[2], bb[2]), max(union[3], bb[3]),
                )
        if not cells or union is None:
            print(f"  - {state}: no content, skipped")
            continue

        x0 = max(0, union[0] - pad)
        y0 = max(0, union[1] - pad)
        x1 = min(CELL - 1, union[2] + pad)
        y1 = min(CELL - 1, union[3] + pad)
        cw, ch = x1 - x0 + 1, y1 - y0 + 1

        sheet = QImage(cw * len(cells), ch, QImage.Format_ARGB32)
        sheet.fill(Qt.transparent)
        p = QPainter(sheet)
        for i, im in enumerate(cells):
            p.drawImage(i * cw, 0, im.copy(x0, y0, cw, ch))
        p.end()
        sheet.save(str(out_dir / f"{state}.png"))
        (out_dir / f"{state}.json").write_text(
            json.dumps({"frames": len(cells), "fps": fps}), encoding="utf-8"
        )
        print(f"  {state}: {len(cells)} frames @ {fps}fps, cell {cw}x{ch}")


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
