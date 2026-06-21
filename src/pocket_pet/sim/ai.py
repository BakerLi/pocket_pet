"""AI-generated snark via Google's Gemini API — an optional topping on dialogue.

Design goals (see also the preset fallback in :mod:`dialogue`):

* **Never block the UI.** Network calls run on a background thread. One call
  *batch-fills* every situation into a local pool; the pet then speaks instantly
  by popping a line, and we touch the network only every few minutes.
* **Always degrade gracefully.** No key / no network / quota gone / any error ->
  :meth:`AINarrator.pick` returns ``None`` and the caller uses preset lines.
* **No extra dependencies.** Talks to the Gemini REST endpoint with stdlib only,
  so PyInstaller bundling stays trivial.

The key is read from ``$GEMINI_API_KEY`` or ``%APPDATA%/pocket_pet/gemini_key.txt``;
preferences live in ``%APPDATA%/pocket_pet/ai_config.json``. Both sit outside the
repo, so secrets never get committed.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.request

from ..config import (
    AI_CONFIG_FILE,
    AI_DEFAULT_ENABLED,
    AI_DEFAULT_MODEL,
    AI_DEFAULT_PERSONALITY,
    AI_DEFAULT_PHILOSOPHY,
    AI_DEFAULT_WEATHER,
    AI_DEFAULT_WINDOW_SNARK,
    AI_FAIL_BACKOFF,
    AI_KEY_ENV,
    AI_KEY_FILE,
    AI_LINES_PER_BUCKET,
    AI_MAX_LINE_CHARS,
    AI_MAX_PER_BUCKET,
    AI_MIN_REFILL_INTERVAL,
    AI_PERSONALITIES,
    AI_POOL_LOW_WATER,
    AI_REQUEST_TIMEOUT,
    WEATHER_CACHE_SECONDS,
    WEATHER_TIMEOUT,
    WEATHER_URL,
)
from .persistence import save_dir

# Situations the model writes for. Keys that overlap dialogue's event/need names
# let the caller fall back seamlessly; the rest are AI-only extras.
_BUCKETS = {
    "greet": "主人來打招呼或點擊時的回應",
    "feed": "被餵食、開心吃東西時",
    "pet": "被摸摸/撫摸時",
    "refuse_full": "太飽了,拒絕再吃",
    "refuse_sleep": "還不睏,拒絕睡覺",
    "medicine": "生病吃藥後好一點",
    "refuse_medicine": "根本沒生病,拒絕吃藥",
    "thrown": "被主人用滑鼠抓起來甩飛出去,嚇到/生氣的大叫",
    "energy": "很睏、沒體力時的抱怨",
    "fullness": "肚子餓時的抱怨",
    "mood": "無聊、心情低落時",
    "sick": "生病難受時",
    "happy": "狀態很好時的隨口閒聊",
    "night": "深夜時段對還沒睡的主人講的話",
    "neglected": "很久沒被理會、覺得被冷落時",
    "death_starve": "餓死前的遺言:先毒舌埋怨主人不餵食,後半話鋒一轉收成溫馨不捨的告別",
    "death_depress": "鬱鬱而終的遺言:先毒舌埋怨主人不陪,後半話鋒一轉收成溫馨不捨的告別",
    "death_illness": "病死前的遺言:先毒舌埋怨主人不給藥,後半話鋒一轉收成溫馨不捨的告別",
}


# --- config / key (module-level, shared by all pets) -----------------------
def _config_path():
    return save_dir() / AI_CONFIG_FILE


def load_config() -> dict:
    cfg = {
        "enabled": AI_DEFAULT_ENABLED,
        "personality": AI_DEFAULT_PERSONALITY,
        "model": AI_DEFAULT_MODEL,
    }
    try:
        p = _config_path()
        if p.exists():
            cfg.update(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    try:
        d = save_dir()
        d.mkdir(parents=True, exist_ok=True)
        _config_path().write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


_config = load_config()


def load_key() -> str:
    k = os.environ.get(AI_KEY_ENV)
    if k:
        return k.strip()
    try:
        p = save_dir() / AI_KEY_FILE
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""


def has_key() -> bool:
    return bool(load_key())


def is_enabled() -> bool:
    return bool(_config.get("enabled", AI_DEFAULT_ENABLED))


def set_enabled(on: bool) -> None:
    _config["enabled"] = bool(on)
    save_config(_config)


def window_snark_enabled() -> bool:
    return bool(_config.get("window_snark", AI_DEFAULT_WINDOW_SNARK))


def set_window_snark(on: bool) -> None:
    _config["window_snark"] = bool(on)
    save_config(_config)


def philosophy_enabled() -> bool:
    return bool(_config.get("philosophy", AI_DEFAULT_PHILOSOPHY))


def set_philosophy(on: bool) -> None:
    _config["philosophy"] = bool(on)
    save_config(_config)


def weather_enabled() -> bool:
    return bool(_config.get("weather", AI_DEFAULT_WEATHER))


def set_weather(on: bool) -> None:
    _config["weather"] = bool(on)
    save_config(_config)


def personality() -> str:
    key = _config.get("personality", AI_DEFAULT_PERSONALITY)
    return key if key in AI_PERSONALITIES else AI_DEFAULT_PERSONALITY


def set_personality(key: str) -> None:
    if key in AI_PERSONALITIES:
        _config["personality"] = key
        save_config(_config)


def personalities() -> list[tuple[str, str]]:
    """(key, display label) pairs for the UI, in definition order."""
    return [(k, v[0]) for k, v in AI_PERSONALITIES.items()]


def _persona() -> str:
    return AI_PERSONALITIES[personality()][1]


# --- prompt + network ------------------------------------------------------
# Shared flavour hint: encourage occasional wordplay without forcing it.
_PUN_HINT = "偶爾可以玩點諧音/同音字雙關增加趣味(別硬要、別每句都用)。"


def _build_prompt(ctx: dict) -> str:
    n = ctx.get("needs", {})
    recent = ctx.get("recent") or []
    recent_txt = "、".join(recent) if recent else "（沒什麼特別的事）"
    buckets_txt = "\n".join(f'  - "{k}": {v}' for k, v in _BUCKETS.items())
    shiny = "(閃光稀有個體!)" if ctx.get("shiny") else ""
    return (
        f"你是一隻桌面寵物,{_persona()}\n"
        f"你是一隻「{ctx.get('species', '生物')}」{shiny},目前是{ctx.get('stage', '成年')}階段。\n"
        f"現在狀態(0~100,越高越好):飽食{n.get('fullness')}、心情{n.get('mood')}、"
        f"體力{n.get('energy')}、健康{n.get('health')}、清潔{n.get('hygiene')}"
        f"{'、目前生病中' if n.get('sick') else ''}。\n"
        f"體重{ctx.get('weight')}kg。現在時間 {ctx.get('hour')} 點,日期 {ctx.get('date')}"
        f"(若是節日請應景一下)。最近發生:{recent_txt}。\n\n"
        "請用繁體中文,為下列每個情境各寫"
        f" {AI_LINES_PER_BUCKET} 句『不同』的台詞。口語、有個性、夠嗆;"
        "長度自由(可短可長,大多 10~30 字,但別超過 40 字),可帶最多一個 emoji,"
        "不要加引號、不要解釋。"
        f"{_PUN_HINT}\n"
        f"情境:\n{buckets_txt}\n\n"
        "只回傳一個 JSON 物件,key 為上面的情境代號,value 為該情境的台詞字串陣列。"
    )


def _call_gemini(prompt: str, key: str, model: str) -> dict:
    """POST to the Gemini REST endpoint; return the parsed JSON object of lines."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 1.3,
                "responseMimeType": "application/json",
                # Disable "thinking" on Gemini 2.5 models: without this the batch
                # takes ~23 s (often timing out) AND tends to emit malformed JSON.
                # With it off it's ~7 s and clean.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=AI_REQUEST_TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def _build_window_prompt(ctx: dict, title: str, proc: str) -> str:
    shiny = "(閃光稀有個體!)" if ctx.get("shiny") else ""
    app = f"(程式:{proc})" if proc else ""
    return (
        f"你是一隻桌面寵物,{_persona()}\n"
        f"你是一隻「{ctx.get('species', '生物')}」{shiny}。\n"
        f"主人現在在用的視窗標題是:「{title}」{app}。\n"
        "請針對主人正在做的事,用繁體中文吐槽『一句』話,口語、有個性、夠嗆,"
        "可長可短但別超過 40 字,可帶最多一個 emoji。"
        f"{_PUN_HINT}只回那一句,不要解釋、不要引號。"
    )


_weather_cache = {"text": "", "at": 0.0}
_weather_lock = threading.Lock()


def current_weather() -> str:
    """Local weather as a short string (e.g. "晴 +27°C"), cached hourly.

    Best-effort via wttr.in (free, no key, auto-locates by IP). Returns the last
    known value (or "") on any failure. Call only off the main thread.
    """
    now = time.monotonic()
    with _weather_lock:
        if _weather_cache["text"] and now - _weather_cache["at"] < WEATHER_CACHE_SECONDS:
            return _weather_cache["text"]
    text = ""
    try:
        # wttr.in returns plain text only for curl-like agents (browsers get HTML).
        req = urllib.request.Request(WEATHER_URL, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=WEATHER_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace").strip()
        if raw and "Unknown location" not in raw and "<" not in raw:
            text = raw.splitlines()[0][:40]
    except Exception:
        text = ""
    with _weather_lock:
        if text:
            _weather_cache["text"] = text
            _weather_cache["at"] = now
        return text or _weather_cache["text"]


def _build_musing_prompt(ctx: dict, weather: str, window_title: str) -> str:
    recent = ctx.get("recent") or []
    recent_txt = "、".join(recent) if recent else "（沒什麼特別的）"
    shiny = "(閃光稀有個體!)" if ctx.get("shiny") else ""
    bits = [f"現在 {ctx.get('hour')} 點", f"日期 {ctx.get('date')}(若是節日請帶到)"]
    if weather:
        bits.append(f"天氣 {weather}")
    if window_title:
        bits.append(f"主人正在用的視窗:「{window_title}」")
    bits.append(f"最近的回憶:{recent_txt}")
    return (
        f"你是一隻桌面寵物,{_persona()}\n"
        f"你是一隻「{ctx.get('species', '生物')}」{shiny}。\n"
        f"目前情境:{';'.join(bits)}。\n"
        "請以這隻寵物的口吻,講『一句』帶點哲學味/存在主義的吐槽或感慨,"
        "從上面情境挑一兩個來呼應(時間、節日、天氣、視窗或回憶),"
        "毒舌中帶看破紅塵,可長可短但別超過 40 字。"
        f"{_PUN_HINT}只回那一句,不要解釋、不要引號。"
    )


def _build_epitaph_prompt(ctx: dict, cause: str, age_text: str) -> str:
    recent = ctx.get("recent") or []
    recent_txt = "、".join(recent) if recent else "（沒什麼特別的回憶）"
    shiny = "(閃光稀有個體!)" if ctx.get("shiny") else ""
    return (
        f"你是一隻桌面寵物,{_persona()}\n"
        f"你是一隻「{ctx.get('species', '生物')}」{shiny},現在因為「{cause}」走到生命盡頭,"
        f"總共活了{age_text}。\n"
        f"你和主人之間最近發生的事(你的回憶):{recent_txt}。\n"
        "請說出你的『遺言』:前半依你的個性毒舌吐槽/抱怨(扣住死因、呼應回憶),"
        "後半『話鋒一轉』,收成一句有點溫馨、不捨、刀子嘴豆腐心的告別。"
        "整體 30~50 字。只回這段話,不要解釋、不要引號。"
    )


def _call_gemini_text(prompt: str, key: str, model: str) -> str:
    """Single plain-text line (for on-demand one-shots like window snark)."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 1.3,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=AI_REQUEST_TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    return text.strip().strip("「」\"'").splitlines()[0] if text.strip() else ""


def _clean(data: dict) -> dict:
    """Keep only known buckets with sane, short string lines."""
    if not isinstance(data, dict):
        return {}
    out: dict[str, list[str]] = {}
    for bucket in _BUCKETS:
        vals = data.get(bucket)
        if not isinstance(vals, list):
            continue
        lines = []
        for v in vals:
            if not isinstance(v, str):
                continue
            s = v.strip().strip("「」\"'")
            if s and len(s) <= AI_MAX_LINE_CHARS:
                lines.append(s)
        if lines:
            out[bucket] = lines[:AI_LINES_PER_BUCKET]
    return out


# --- the narrator (one per pet) --------------------------------------------
class AINarrator:
    """A per-pet pool of AI lines, refilled lazily in the background.

    ``context_fn`` is a callable returning the current pet snapshot dict (it is
    invoked on the background thread, so it must only read plain values).
    """

    def __init__(self, context_fn):
        self._context_fn = context_fn
        self._pool: dict[str, list[str]] = {}
        self._lock = threading.Lock()
        self._refilling = False
        self._last_refill = 0.0
        self._fail_until = 0.0
        self._key = load_key()  # cached; add a key then restart to enable
        self._outbox: list[str] = []  # one-shot lines (window snark / musing)
        self._oneshot_busy = False
        self._musing_busy = False

    def available(self) -> bool:
        return bool(self._key) and is_enabled()

    def reset(self) -> None:
        """Drop the pooled lines (e.g. after a personality change) so the next
        pick triggers a fresh batch in the new voice."""
        with self._lock:
            self._pool.clear()
            self._last_refill = 0.0
            self._fail_until = 0.0

    # --- one-shot context-specific lines (window snark) ------------------
    def request_window_comment(self, title: str, proc: str) -> None:
        """Kick off a background single-line comment about the given window.
        The result lands in the outbox; drain it with :meth:`take_comment`."""
        if not self.available():
            return
        with self._lock:
            if self._oneshot_busy:
                return
            self._oneshot_busy = True
        args = (title, proc)
        threading.Thread(target=self._oneshot, args=args, daemon=True).start()

    def _oneshot(self, title: str, proc: str) -> None:
        try:
            ctx = self._context_fn()
            line = _call_gemini_text(
                _build_window_prompt(ctx, title, proc),
                self._key,
                _config.get("model", AI_DEFAULT_MODEL),
            )
            if line and len(line) <= AI_MAX_LINE_CHARS:
                with self._lock:
                    self._outbox.append(line)
        except Exception:
            pass
        finally:
            with self._lock:
                self._oneshot_busy = False

    def take_comment(self) -> str | None:
        with self._lock:
            return self._outbox.pop(0) if self._outbox else None

    def request_musing(self, window_title: str = "") -> None:
        """Kick off a philosophical musing built from the live context (weather is
        fetched here, off the main thread). Result lands in the outbox."""
        if not self.available():
            return
        with self._lock:
            if self._musing_busy:
                return
            self._musing_busy = True
        threading.Thread(
            target=self._musing_worker, args=(window_title,), daemon=True
        ).start()

    def _musing_worker(self, window_title: str) -> None:
        try:
            ctx = self._context_fn()
            weather = current_weather() if weather_enabled() else ""
            line = _call_gemini_text(
                _build_musing_prompt(ctx, weather, window_title),
                self._key,
                _config.get("model", AI_DEFAULT_MODEL),
            )
            if line and len(line) <= AI_MAX_LINE_CHARS:
                with self._lock:
                    self._outbox.append(line)
        except Exception:
            pass
        finally:
            with self._lock:
                self._musing_busy = False

    def request_epitaph(self, cause: str, age_text: str) -> bool:
        """Kick off a memory-aware bespoke last line (cause + age + recent).
        Returns True if a request was actually started. The result lands in the
        outbox; drain it with :meth:`take_comment`."""
        if not self.available():
            return False
        with self._lock:
            self._outbox.clear()  # ensure only the epitaph is waiting there
        threading.Thread(
            target=self._epitaph_worker, args=(cause, age_text), daemon=True
        ).start()
        return True

    def _epitaph_worker(self, cause: str, age_text: str) -> None:
        try:
            ctx = self._context_fn()
            line = _call_gemini_text(
                _build_epitaph_prompt(ctx, cause, age_text),
                self._key,
                _config.get("model", AI_DEFAULT_MODEL),
            )
            if line and len(line) <= AI_MAX_LINE_CHARS:
                with self._lock:
                    self._outbox.append(line)
        except Exception:
            pass

    def pick(self, bucket: str) -> str | None:
        """Pop a pooled line for ``bucket``; trigger a refill when running low.

        Returns ``None`` (caller falls back to presets) if AI is unavailable or
        that bucket happens to be empty right now.
        """
        if not self.available():
            return None
        with self._lock:
            lines = self._pool.get(bucket)
            line = lines.pop() if lines else None
            total = sum(len(v) for v in self._pool.values())
        self._maybe_refill(total)
        return line

    def _maybe_refill(self, total: int) -> None:
        if total > AI_POOL_LOW_WATER:
            return
        now = time.monotonic()
        if now < self._fail_until or now - self._last_refill < AI_MIN_REFILL_INTERVAL:
            return
        with self._lock:
            if self._refilling:
                return
            self._refilling = True
        threading.Thread(target=self._refill, daemon=True).start()

    def _refill(self) -> None:
        ok = False
        try:
            ctx = self._context_fn()
            data = _call_gemini(
                _build_prompt(ctx), self._key, _config.get("model", AI_DEFAULT_MODEL)
            )
            cleaned = _clean(data)
            if cleaned:
                with self._lock:
                    for bucket, vals in cleaned.items():
                        cur = self._pool.setdefault(bucket, [])
                        cur.extend(vals)
                        del cur[:-AI_MAX_PER_BUCKET]  # keep only the freshest N
                ok = True
        except Exception:
            ok = False  # network/parse/quota — caller already falls back
        finally:
            now = time.monotonic()
            with self._lock:
                self._refilling = False
                if ok:
                    self._last_refill = now
                else:
                    self._fail_until = now + AI_FAIL_BACKOFF
