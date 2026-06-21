# Pocket Pet 🐾

A Windows desktop mascot that walks the desktop, perches on the top edge of
other windows, falls with gravity, and (eventually) grows. Inspired by Claude
Code's `/buddy` April Fools easter egg.

See [`DESIGN.md`](DESIGN.md) for the full architecture and roadmap.

The rabbit's sprite art is by **FluffyFoxOfFate** (Light Brown Bunny Shimeji),
via Kilkakon's Shimeji-ee — see [`CREDITS.md`](CREDITS.md). All other species
are drawn procedurally.

## Status

- **Phase 0 — scaffolding + de-risking spikes (done).** Reading other windows'
  positions to perch on them is proven feasible (see spikes below).
- **Phase 1 — movement + physics + animation (done).** The pet falls in on
  launch, lands on the taskbar-aware floor, walks back and forth turning at the
  screen edges, idles/blinks, and is drawn with an animated procedural sprite.
- **Phase 2 — interaction (done).** Left-drag to grab and throw it (release
  velocity feeds back into gravity), left-click for a hop, right-click for a
  context menu (feed / pet / stats / quit), and a system-tray icon (menu to
  quit). One pet at a time.
- **Phase 3 — window perching (done).** The pet stands and walks on the top
  edge of other windows. Window edges are one-way platforms (land from above,
  pass up from below) with z-order occlusion (never stands on a hidden edge);
  walking off the edge, or the window moving/closing, drops the pet. Throw it
  onto a window to perch it. Windows are rescanned every 250 ms.
- **Phase 4a — needs, persistence, speech (done).** The pet has fullness / mood
  / energy stats that decay over time; it sleeps when exhausted (Zzz) and looks
  sad when hungry/bored. Feed and stroke it from the right-click menu. State is
  saved to `%APPDATA%/pocket_pet/pet.json` and decayed for the time you were
  away (offline catch-up). Speech bubbles show greetings, reactions, and
  needs-based chatter.
- **Phase 4b — species, growth, stats panel (done).** 18 species with rarity
  tiers (common→legendary) and a 1% shiny, deterministically generated from your
  machine+user id so your pet is always the same one (à la Buddy). It hatches
  from an egg → baby → adult as it ages (age persists). Right-click → ℹ️ 狀態
  opens a panel with species, rarity, stage/age, and live need bars.
- **Phase 5a — richer interactions (done).** Feed submenu with several food
  types that drop in from above and are eaten; a stroking hand + floating hearts
  when petted; the pet hops on its own and **climbs the side of windows** it
  walks into, then settles on the top edge (and falls if that window moves or
  closes mid-climb).
- **Phase 5b — art pipeline + rabbit trial (in progress).** Rendering goes
  through a `SpriteProvider` seam: `AssetProvider` loads per-species sprite-sheet
  art from `assets/sprites/<species>/` and falls back to the procedural drawing
  wherever art is missing — so art can land one species/state at a time. The
  rabbit is the first fully-arted species (8 states, multi-frame); see
  `tools/gen_rabbit_art.py` and `assets/sprites/README.md`.
- **Life-sim v2 (done).** Health, hygiene and weight (kg) join the needs; the
  pet **digests food and poops** (clean it by clicking; poop rests on windows
  and falls when they close), left-around poop drops **hygiene** which can make
  it **sick** (green tint + 💀, cure with 💊 medicine). It runs, does a landing
  bounce, naps on command, and politely **refuses** food/sleep/medicine it
  doesn't need. Prolonged starvation, sustained sadness, or untreated illness
  lead to **permanent death** — a 🪦 tombstone with an epitaph (click to read).
  Set `POCKET_PET_DEV=1` for a hidden tray "復活" revive backdoor.
- **AI snark (optional, Gemini).** With an API key the pet voices AI-generated
  lines — situational quips (time-of-day, neglect, being thrown, sickness),
  selectable personalities (savage / tsundere / chuuni / gentle), comments on
  your active window, occasional philosophical musings (optionally seasoned with
  local weather), and a cause-+memory-aware epitaph when it dies. It **always
  falls back** to the built-in preset lines when there's no key / no network /
  quota is exhausted, so nothing ever breaks. See **AI snark setup** below.

### Run the pet

```sh
.venv/Scripts/python.exe -m pocket_pet.main
```

Controls: **left-drag** = pick up & throw · **left-click** = hop ·
**right-click** = menu · **tray icon** = quit.

Interactions: right-click → **餵食** picks one of several foods, which drops
from the top of the screen onto the pet to eat (different fullness/mood values);
**摸摸** strokes it with a hand and floats hearts (hovering the pet shows a hand
cursor). The pet also does the odd playful hop on its own.

## AI snark setup (optional)

The pet works fully without this — it's pure topping. To enable AI lines:

1. Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com)
   (sign in → *Get API key* → *Create API key*).
2. Put it where the app looks (neither path is in the repo, so the key is never
   committed):
   - environment variable `GEMINI_API_KEY`, **or**
   - a file `%APPDATA%\pocket_pet\gemini_key.txt` containing just the key.
3. Restart the pet. A **🤖 AI 嘴砲** submenu appears in the tray.

Tray controls:

- **🤖 AI 嘴砲** → enable, pick a **personality**, and toggle **👀 偷看視窗吐槽**
  (window snark), **🌌 哲學murmur** (philosophical musings), **🌦️ 天氣素材**
  (weather flavour).
- **🗣️ 說話頻率** → ambient chatter cadence (高 / 中 / 低), works with or
  without a key.

Preferences live in `%APPDATA%\pocket_pet\ai_config.json` (`personality`,
`model`, the toggles, `chatter_rate`).

**Privacy.** Window snark sends the *foreground window's title* to Gemini;
weather sends your *approximate location (IP)* to wttr.in. Both are toggleable
in the tray. (In the current build they default on — flip them off if you don't
want that.) The pet only ever sends its own state and these opted-in extras.

**Quota.** Lines are batch-generated into a local pool, so the network is hit
rarely; on the free tier this is plenty. If the quota runs out it silently
reverts to preset lines.

## Setup (developers)

```sh
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
```

(PySide6 + pywin32; Windows only.)

## Package for non-developers (standalone .exe)

Build a single `PocketPet.exe` that runs **without Python installed** — hand it
to anyone on Windows and they just double-click it:

```powershell
./build.ps1
```

This installs the build deps, runs PyInstaller (`--onefile --windowed`), and
produces `dist/PocketPet.exe` (~44 MB). No asset files are bundled — the sprite
and tray icon are drawn procedurally. To start automatically at login, drop a
shortcut to the exe into `shell:startup`.

(Build details live in `build.ps1` + `packaging/launcher.py`. A
`pocket-pet` GUI launcher entry point is also defined, so `pipx install .`
works for users who do have Python.)

## Uninstall

The pet keeps no installer registration; removing it is just deleting files:

1. Quit it (system-tray menu → quit, or right-click the pet → 退出).
2. Delete `PocketPet.exe` (and any `shell:startup` shortcut you made).
3. Delete the save data: `%APPDATA%\pocket_pet` (holds `pet.json`). This is
   never removed automatically, by any install method.

For a dev/pipx install instead: `pip uninstall pocket-pet` (or
`pipx uninstall pocket-pet`), then delete `%APPDATA%\pocket_pet`.

## Run the spikes

```sh
# A) Transparent always-on-top pet + gravity + floor + click/throw.
.venv/Scripts/python.exe spikes/spike_overlay.py

# B) Debug overlay drawing the top edge of every detected window (= perch
#    platforms). Drag windows around and watch the red lines follow. Esc to quit.
.venv/Scripts/python.exe spikes/spike_windows.py
```

If console output shows mojibake / a `cp950` error from a window title, prefix
with `set PYTHONIOENCODING=utf-8` (Windows console encoding, not a code bug).

## Layout

```
src/pocket_pet/
  platform/winapi.py   # Win32/DWM/DPI: window enum, perch bounds, positioning
  core/  ui/  sim/     # (Phase 1+) physics, Qt windows, life-sim
spikes/                # throwaway proofs-of-concept
DESIGN.md              # architecture + phased roadmap
```
