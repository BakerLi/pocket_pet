"""Tunable constants. Pure data — no imports, no OS calls."""

# Sprite box, in physical pixels.
PET_SIZE = 96

# Physics (physical px, seconds).
GRAVITY = 2000.0       # px / s^2
WALK_SPEED = 150.0     # px / s

# Playful autonomous hop: chance per second while idling on the desktop floor.
JUMP_CHANCE = 0.12     # ~once every 8 s of idling
JUMP_VELOCITY = -560.0 # upward kick of a self-initiated hop

# Climbing window side edges.
CLIMB_SPEED = 95.0       # px / s the pet climbs upward
CLIMB_MAX_SECONDS = 14.0 # safety cap so a stuck climb always ends
CLIMB_CHANCE = 0.7       # on bumping a wall, odds it climbs (vs turning around)

# Running: occasionally sprint instead of walk.
RUN_SPEED = 320.0           # px / s
RUN_CHANCE = 0.35           # when starting to move, odds of a run vs a walk
RUN_DURATION = (1.0, 2.5)   # seconds, [min, max]

# Landing bounce: a brief squash when touching down from a real fall.
LAND_SECONDS = 0.22         # how long the bounce pose holds
LAND_MIN_IMPACT = 800.0     # px/s; gentler touchdowns (small hops) don't bounce

# Behavior timing (seconds), [min, max] picked at random.
IDLE_DURATION = (0.8, 3.0)
WALK_DURATION = (1.5, 4.5)
IDLE2_CHANCE = 0.25    # when idling, odds of the alternate idle (e.g. grooming)

# Update loop.
FPS = 60
DT = 1.0 / FPS

# How often to re-scan other windows for perch platforms (ms). Cheap per-frame
# reads, slower full rescans.
PLATFORM_POLL_MS = 250

# --- Needs (life-sim) ------------------------------------------------------
# All stats are 0..100 where higher = better, decaying downward over time.
# Rates are per second (derived from a comfortable real-world pace).
FULLNESS_DECAY = 100.0 / (3.0 * 3600)    # gets hungry over ~3 h
MOOD_DECAY = 100.0 / (4.0 * 3600)        # gets bored over ~4 h
ENERGY_DECAY = 100.0 / (2.5 * 3600)      # gets tired over ~2.5 h
ENERGY_RECOVER = 100.0 / (18.0 * 60)     # full recovery after ~18 min of sleep
STARVING_MOOD_FACTOR = 2.0               # mood drops faster while fullness is 0

LOW_NEED = 25.0          # below this a need is "low" (sad face, complaints)
SLEEP_ENTER = 15.0       # energy below this -> the pet sleeps
SLEEP_EXIT = 90.0        # energy above this -> it wakes up
FEED_AMOUNT = 35.0       # fullness restored per feeding
PET_MOOD_BOOST = 18.0    # mood restored per pet/stroke

# --- Refusal (懂得拒絕) -----------------------------------------------------
FULL_REFUSE = 90.0       # fullness >= this -> refuse more food
SLEEP_REFUSE = 70.0      # energy >= this -> refuse to sleep on command
SLEEP_WANT = 30.0        # energy < this -> shows it's sleepy

# --- Digestion -> poop (Phase 2) -------------------------------------------
# Eating fills the gut; it digests into the bowel over time; when the bowel is
# full the pet poops. Tuned so ~one feeding -> ~one poop after ~1.5 h.
GUT_PER_FULLNESS = 1.0                     # gut added per point of fullness fed
POOP_AMOUNT = 35.0                         # bowel needed for one poop
DIGEST_SECONDS = 1.5 * 3600               # time to digest one feeding
DIGEST_RATE = POOP_AMOUNT / DIGEST_SECONDS  # gut -> bowel per second
POOP_SIZE = 40                            # px box for a poop
MAX_POOPS = 6                             # cap on-screen poops

# Hygiene: drops while poop is left around, recovers once it's all cleaned.
HYGIENE_DECAY_PER_POOP = 100.0 / (3.0 * 3600)  # one poop empties hygiene in ~3 h
HYGIENE_RECOVER = 100.0 / (30.0 * 60)          # clean -> recovers over ~30 min

# --- Weight (kg) -----------------------------------------------------------
# Feeding adds weight; a steady metabolism burns it (more while moving).
WEIGHT_START = 3.5
WEIGHT_MIN = 2.0
WEIGHT_MAX = 6.0
WEIGHT_PER_FULLNESS = 0.004              # kg gained per point of fullness fed
WEIGHT_BASAL_BURN = 0.6 / (24 * 3600)   # ~0.6 kg/day at rest
WEIGHT_MOVE_BURN = 1.2 / (24 * 3600)    # extra while walking/running/climbing

# --- Food types ------------------------------------------------------------
# (key, emoji, display name, fullness restored, mood bonus). Picked from the
# right-click "餵食" submenu; the chosen food drops from the top of the screen
# onto the pet, which then eats it.
FOODS = [
    ("meat",   "🍖", "肉肉",   45.0,  6.0),
    ("fish",   "🐟", "小魚",   35.0,  5.0),
    ("apple",  "🍎", "蘋果",   25.0,  4.0),
    ("carrot", "🥕", "紅蘿蔔", 30.0,  3.0),
    ("cookie", "🍪", "餅乾",   20.0, 12.0),
]
FOOD_SIZE = 40            # px box for a falling food item
FOOD_GRAVITY = 1500.0     # px / s^2 for falling food (gentler than the pet)
EAT_DURATION = 1.4        # seconds the pet spends eating once food arrives

# --- Reactions (transient interaction states) ------------------------------
PET_REACT_SECONDS = 1.6   # how long the "being petted" animation lasts
HEART_COUNT = 4           # floating hearts spawned when petted
HEART_RISE = 70.0         # px/s the hearts drift upward

SAVE_INTERVAL_MS = 30000  # autosave cadence

# --- Speech bubbles --------------------------------------------------------
CHATTER_INTERVAL = (12.0, 22.0)  # seconds between ambient lines (random in range)
BUBBLE_SECONDS = 3.5             # how long a bubble stays up

# --- Growth (age in seconds; advances in real time, including offline) -----
EGG_UNTIL = 120.0      # stays an egg for the first ~2 min, then hatches
BABY_UNTIL = 1200.0    # baby until ~20 min, then adult
# Visual size of the body within the (fixed) sprite box, per stage.
STAGE_SCALE = {"egg": 0.70, "baby": 0.72, "adult": 1.0}
