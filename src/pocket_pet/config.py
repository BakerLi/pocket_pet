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

# --- Sickness (Phase 3) ----------------------------------------------------
SICK_HYGIENE = 30.0                    # below this hygiene, illness can set in
SICK_ONSET_CHANCE = 1.0 / 600.0        # per second at max filth (hygiene 0)
SICK_HEALTH_DECAY = 100.0 / (6.0 * 3600)   # being sick drains health over ~6 h
SICK_MOOD_EXTRA = 100.0 / (8.0 * 3600)     # extra mood drop while sick
HEALTH_REGEN = 100.0 / (2.0 * 3600)        # heal over ~2 h while healthy
MEDICINE_HEAL = 35.0                       # health restored by one dose

# --- Death (Phase 4) -------------------------------------------------------
STARVE_DEATH_SECONDS = 30.0 * 60     # fullness pinned at 0 this long -> starves
DEPRESS_DEATH_SECONDS = 45.0 * 60    # mood pinned at 0 this long -> dies of sorrow
# (health reaching 0 from illness kills immediately)
CAUSE_STARVE = "餓壞了"
CAUSE_DEPRESS = "鬱鬱而終"
CAUSE_ILLNESS = "病重不治"
DEATH_FLAVOURS = [
    "謝謝你陪我走過這段桌面時光。",
    "別難過,我只是去別的視窗探險了。",
    "記得…要好好吃飯喔。",
    "下輩子還要當你的桌寵。",
    "願我在雲端安息 ☁️",
]
# Preset last words per cause of death (fallback when AI is off/unavailable).
# Each line roasts first, then turns warm at the end.
DEATH_FLAVOURS_BY_CAUSE = {
    CAUSE_STARVE: [
        "都怪你不餵我…笨蛋…不過,能當你的寵物…我很開心…",
        "餓死我了啦…哼…但…謝謝你陪我這一場…",
        "連口飯都不給…真小氣…算了,下輩子…我還找你…",
    ],
    CAUSE_DEPRESS: [
        "都沒人陪我…好寂寞…可是…遇見你…還是值得的…",
        "你都不理我…哼…不過…別太難過喔,笨蛋…",
        "無聊死了啦…但…謝謝你曾經…把我放在心上…",
    ],
    CAUSE_ILLNESS: [
        "藥都不給我…真過分…可是…還是…最喜歡你了…",
        "咳…病死了啦…笨主人…要…好好照顧自己喔…",
        "都怪你不救我…哼…謝謝你…陪我走到最後…",
    ],
}
DEV_ENV = "POCKET_PET_DEV"           # set to 1 to unlock the revive backdoor

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
# Ambient chatter cadence presets (seconds between lines, random in range).
# "high" is the original lively pace; pick in the tray ("說話頻率").
CHATTER_RATES = {
    "high": (12.0, 22.0),
    "medium": (28.0, 50.0),
    "low": (75.0, 140.0),
}
AI_DEFAULT_CHATTER_RATE = "high"
CHATTER_INTERVAL = CHATTER_RATES["high"]  # default / fallback
BUBBLE_SECONDS = 3.5             # legacy fixed duration (fallback)
# A bubble's on-screen time scales with how much there is to read, so longer
# (AI) lines linger and short quips flash by.
BUBBLE_MIN_SECONDS = 2.5
BUBBLE_MAX_SECONDS = 10.0
BUBBLE_SECONDS_PER_CHAR = 0.22   # added reading time per character

# --- AI snark (Gemini) -----------------------------------------------------
# The pet can voice AI-generated lines via Google's Gemini API. The key is read
# from the env var GEMINI_API_KEY, else %APPDATA%/pocket_pet/gemini_key.txt
# (neither lives in the repo, so it never gets committed). With no key / no
# network / quota exhausted / any error, it silently falls back to the built-in
# preset lines in dialogue.py — AI is a topping, never a dependency.
AI_KEY_ENV = "GEMINI_API_KEY"
AI_KEY_FILE = "gemini_key.txt"        # in the save dir (%APPDATA%/pocket_pet)
AI_CONFIG_FILE = "ai_config.json"     # {enabled, personality, model}
AI_DEFAULT_MODEL = "gemini-2.5-flash" # change in ai_config.json if you like
AI_DEFAULT_ENABLED = True
AI_DEFAULT_PERSONALITY = "savage"
# "Snark about what you're doing": peeks at the foreground window's title/app and
# comments on it. Privacy-sensitive (titles can hold filenames/URLs), so it is
# OFF by default and only ever runs when both a key is present AND you opt in.
AI_DEFAULT_WINDOW_SNARK = True
WINDOW_SNARK_INTERVAL = (180.0, 360.0)  # s between window peeks (random in range)
# Occasional philosophical/existential musings, generated on demand from the live
# context (time, festival, memory, + weather/window if those are also on). Off by
# default; toggle in the tray.
AI_DEFAULT_PHILOSOPHY = True
PHILOSOPHY_INTERVAL = (240.0, 480.0)    # s between musings (random in range)
# Optional weather flavour via wttr.in (free, no key). Sends your approximate
# location (IP) to a third party — still a toggle, but on by default here.
AI_DEFAULT_WEATHER = True
WEATHER_URL = "https://wttr.in/?format=%C+%t&lang=zh"  # e.g. "晴 +27°C"
WEATHER_CACHE_SECONDS = 3600.0          # refetch weather at most hourly
WEATHER_TIMEOUT = 8.0                    # s network timeout for the weather fetch

# Personality presets: key -> (display name, persona fed to Gemini). Pick one in
# ai_config.json ("personality": "tsundere"); each pet's species/shiny is mixed
# in too so lines feel like *this* pet.
AI_PERSONALITIES = {
    "savage":   ("毒舌", "個性毒舌、嘴巴很壞、超愛吐槽主人,但其實是刀子嘴豆腐心。"),
    "tsundere": ("傲嬌", "傲嬌,嘴上嫌棄、口嫌體正直,偶爾流露關心又急著否認。"),
    "chuuni":   ("中二", "中二病,自稱被封印的魔王,講話浮誇愛用厲害的詞,其實只是隻桌寵。"),
    "gentle":   ("溫柔", "溫柔療癒、講話暖心貼心,偶爾對主人撒嬌。"),
}

# Generation / caching. One API call batch-fills every situation at once, so the
# pet talks instantly from the local pool and we rarely hit the network.
AI_LINES_PER_BUCKET = 5         # lines per situation requested each batch
AI_MAX_PER_BUCKET = 12          # cap pooled lines per situation
AI_POOL_LOW_WATER = 20          # total pooled lines at/below this -> refill
AI_MIN_REFILL_INTERVAL = 90.0   # s; never batch-generate more often than this
AI_FAIL_BACKOFF = 300.0         # s to wait after an API error before retrying
# A whole batch (~15 situations) takes ~7-8 s even with "thinking" disabled, so
# keep this generous; it runs on a background thread and never blocks the pet.
AI_REQUEST_TIMEOUT = 30.0       # s network timeout per request
AI_MAX_LINE_CHARS = 60          # defensively drop only truly runaway lines

NEGLECT_SECONDS = 20.0 * 60     # no interaction this long -> "neglected" chatter
THROW_SNARK_SPEED = 900.0       # px/s release speed above which a throw earns a yell

# --- Growth (age in seconds; advances in real time, including offline) -----
EGG_UNTIL = 120.0      # stays an egg for the first ~2 min, then hatches
BABY_UNTIL = 1200.0    # baby until ~20 min, then adult
# Visual size of the body within the (fixed) sprite box, per stage.
STAGE_SCALE = {"egg": 0.70, "baby": 0.72, "adult": 1.0}
