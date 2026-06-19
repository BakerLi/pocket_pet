# Sprite art

Drop per-species art here and the app uses it automatically; anything missing
falls back to the built-in procedural drawing (so partial art is fine).

## Layout

```
assets/sprites/<species_key>/<state>.png         # adult / default
assets/sprites/<species_key>/<state>_baby.png    # optional stage override
assets/sprites/<species_key>/<state>_egg.png     # optional stage override
assets/sprites/<species_key>/<state>.json        # optional: {"frames": N, "fps": F}
```

- `<species_key>` is the species key (see `src/pocket_pet/sim/species.py`):
  `duck goose cat rabbit owl penguin turtle snail dragon octopus axolotl ghost
  robot blob cactus mushroom chonk capybara`.
- `<state>` is one of: `idle walk fall drag sleep eat pet climb`.
- A PNG with no JSON is a single static frame. With `{"frames": N}` it's a
  **horizontal sprite sheet** — N equal-width frames left-to-right, looped at
  `fps` (default 8).
- Art should **face right**; left-facing is drawn by mirroring.
- Frames are scaled to fit the sprite box and bottom-centre aligned (feet on
  the floor). Transparent PNGs.

## Example

```
assets/sprites/rabbit/idle.png      + idle.json  {"frames": 2, "fps": 3}
assets/sprites/rabbit/walk.png      + walk.json  {"frames": 4, "fps": 10}
assets/sprites/rabbit/eat.png
```

Only the rabbit's idle/walk/eat would use art; every other species/state stays
procedural until you add files. The loader is `src/pocket_pet/ui/sprite_asset.py`.

Builds bundle this folder automatically (`build.ps1` adds it via `--add-data`).
