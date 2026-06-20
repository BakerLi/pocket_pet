"""Turn a contact-sheet style PNG (frames on a solid bg) into a clean sheet.

The eat2 art the user supplied is 10 carrot-eating frames laid out on a BLACK
background with a thin WHITE border, and the bunny outline is near-black. A plain
colour-key would punch holes in the eyes/outline, so we flood-fill the
background to transparent FROM THE EDGES (removing the black bg and white border,
which are connected to the edges) while leaving interior darks (eyes, outline)
intact. Then crop all frames to one shared content box and write our sheet+JSON.

Usage:
    .venv/Scripts/python.exe tools/process_eat2.py <in.png> <frames> <species> <state> <fps>
e.g.
    .venv/Scripts/python.exe tools/process_eat2.py art_src/extra/eat2.png 10 rabbit eat 7
"""

from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

DARK = 24    # sum(r,g,b) <= this is background black
LIGHT = 720  # sum(r,g,b) >= this is background white (border)
PAD = 2


def _key_bg(cell: QImage) -> QImage:
    """Flood-fill connected bg (black or white) from the edges -> transparent."""
    cell = cell.convertToFormat(QImage.Format_ARGB32)
    w, h = cell.width(), cell.height()

    def is_bg(x, y):
        c = cell.pixelColor(x, y)
        s = c.red() + c.green() + c.blue()
        return s <= DARK or s >= LIGHT

    seen = bytearray(w * h)
    dq = deque()

    def push(x, y):
        if 0 <= x < w and 0 <= y < h and not seen[y * w + x] and is_bg(x, y):
            seen[y * w + x] = 1
            dq.append((x, y))

    for x in range(w):
        push(x, 0); push(x, h - 1)
    for y in range(h):
        push(0, y); push(w - 1, y)
    while dq:
        x, y = dq.popleft()
        push(x + 1, y); push(x - 1, y); push(x, y + 1); push(x, y - 1)

    clear = QColor(0, 0, 0, 0)
    for y in range(h):
        row = y * w
        for x in range(w):
            if seen[row + x]:
                cell.setPixelColor(x, y, clear)
    return cell


def _bbox(img: QImage):
    img = img.convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()

    def row_has(y):
        return any(img.pixelColor(x, y).alpha() > 8 for x in range(w))

    def col_has(x):
        return any(img.pixelColor(x, y).alpha() > 8 for y in range(h))

    miny = next((y for y in range(h) if row_has(y)), None)
    if miny is None:
        return None
    maxy = next(y for y in range(h - 1, -1, -1) if row_has(y))
    minx = next(x for x in range(w) if col_has(x))
    maxx = next(x for x in range(w - 1, -1, -1) if col_has(x))
    return minx, miny, maxx, maxy


def main() -> int:
    if len(sys.argv) < 6:
        print(__doc__)
        return 2
    inp = Path(sys.argv[1]); n = int(sys.argv[2])
    species, state, fps = sys.argv[3], sys.argv[4], float(sys.argv[5])
    flip = "--flip" in sys.argv
    if not inp.exists():
        print(f"input not found: {inp}")
        return 1
    QApplication(sys.argv)

    sheet = QImage(str(inp)).convertToFormat(QImage.Format_ARGB32)
    cw = sheet.width() // n
    frames = []
    union = None
    for i in range(n):
        cell = _key_bg(sheet.copy(i * cw, 0, cw, sheet.height()))
        if flip:
            cell = cell.mirrored(True, False)
        frames.append(cell)
        bb = _bbox(cell)
        if bb:
            union = bb if union is None else (
                min(union[0], bb[0]), min(union[1], bb[1]),
                max(union[2], bb[2]), max(union[3], bb[3]),
            )
    if union is None:
        print("no content found")
        return 1
    x0 = max(0, union[0] - PAD); y0 = max(0, union[1] - PAD)
    x1 = min(cw - 1, union[2] + PAD); y1 = min(sheet.height() - 1, union[3] + PAD)
    fw, fh = x1 - x0 + 1, y1 - y0 + 1

    out = QImage(fw * n, fh, QImage.Format_ARGB32)
    out.fill(QColor(0, 0, 0, 0))
    p = QPainter(out)
    for i, fr in enumerate(frames):
        p.drawImage(i * fw, 0, fr.copy(x0, y0, fw, fh))
    p.end()

    out_dir = Path(__file__).resolve().parents[1] / "assets" / "sprites" / species
    out_dir.mkdir(parents=True, exist_ok=True)
    out.save(str(out_dir / f"{state}.png"))
    (out_dir / f"{state}.json").write_text(
        json.dumps({"frames": n, "fps": fps}), encoding="utf-8"
    )
    print(f"{species}/{state}: {n} frames @ {fps}fps, cell {fw}x{fh}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
