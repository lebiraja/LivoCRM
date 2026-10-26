"""Load-balancing pool of Groq API keys.

One key behaves exactly like a plain client. With several keys the pool spreads
calls by remaining token budget, cools a key down after a 429, and disables a key
the provider rejects (401/403). Secrets never leave this module: everything else
refers to a key by its id (first 8 hex of its SHA-256).

State is per process. Groq limits are per organisation and per model, so state is
tracked per (key, model). Keys from the same Groq org share one bucket.
"""

from __future__ import annotations

import hashlib
import re
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

DEFAULT_COOLDOWN_S = 20.0
AUTH_DISABLE_S = 3600.0
_DURATION = re.compile(r"(?:(\d+(?:\.\d+)?)h)?(?:(\d+(?:\.\d+)?)m(?!s))?(?:(\d+(?:\.\d+)?)s)?(?:(\d+(?:\.\d+)?)ms)?")


def key_id(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()[:8]


def parse_keys(keys_csv: str, single_key: str = "") -> list[str]:
    """Split GROQ_API_KEYS (comma-separated), add GROQ_API_KEY, drop blanks and duplicates."""
    seen: dict[str, None] = {}
    for raw in [*keys_csv.split(","), single_key]:
        key = raw.strip()
        if key:
            seen.setdefault(key, None)
    return list(seen)


def parse_duration(value: str | None) -> float | None:
    """Parse Groq reset headers such as '2.5s', '1m26.4s', '120ms' or plain seconds."""
    if not value:
        return None
    text = value.strip()
    try:
        return float(text)
    except ValueError:
        pass
    match = _DURATION.fullmatch(text)
    if not match or not any(match.groups()):
        return None
    hours, minutes, seconds, millis = (float(g) if g else 0.0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


@dataclass
class _Slot:
    cooldown_until: float = 0.0
    disabled_until: float = 0.0
    remaining_tokens: int | None = None
    remaining_requests: int | None = None
    last_used: float = 0.0
    calls: int = 0
    rate_limited: int = 0


@dataclass
class Lease:
    """A key chosen for one attempt. `secret` is only for the Authorization header."""

    id: str
    secret: str = field(repr=False)
    model: str


class KeyPool:
    def __init__(self, keys: list[str], clock: Callable[[], float] = time.monotonic) -> None:
        self._keys = {key_id(k): k for k in keys}
        self._slots: dict[tuple[str, str], _Slot] = {}
        self._clock = clock
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._keys)

    def _slot(self, kid: str, model: str) -> _Slot:
        return self._slots.setdefault((kid, model), _Slot())

    def acquire(self, model: str) -> Lease | None:
        """Pick the usable key with most remaining tokens (unknown counts as full), LRU on ties."""
        now = self._clock()
        with self._lock:
            best: tuple[tuple[float, float], str] | None = None
            for kid in self._keys:
                slot = self._slot(kid, model)
                if now < slot.cooldown_until or now < slot.disabled_until:
                    continue
                tokens = float("inf") if slot.remaining_tokens is None else slot.remaining_tokens
                rank = (-tokens, slot.last_used)
                if best is None or rank < best[0]:
                    best = (rank, kid)
            if best is None:
                return None
            kid = best[1]
            slot = self._slot(kid, model)
            slot.last_used = now
            slot.calls += 1
            return Lease(id=kid, secret=self._keys[kid], model=model)

    def next_available_in(self, model: str) -> float | None:
        """Seconds until some key can serve `model`; None when every key is disabled."""
        now = self._clock()
        with self._lock:
            waits = [
                max(slot.cooldown_until - now, 0.0)
                for kid in self._keys
                if (slot := self._slot(kid, model)).disabled_until <= now
            ]
        return min(waits) if waits else None

    def report_success(self, lease: Lease, headers: Mapping[str, str]) -> None:
        with self._lock:
            slot = self._slot(lease.id, lease.model)
            slot.remaining_tokens = _to_int(headers.get("x-ratelimit-remaining-tokens"))
            slot.remaining_requests = _to_int(headers.get("x-ratelimit-remaining-requests"))
            slot.cooldown_until = 0.0

    def report_rate_limited(self, lease: Lease, retry_after_s: float | None) -> None:
        wait = retry_after_s if retry_after_s and retry_after_s > 0 else DEFAULT_COOLDOWN_S
        with self._lock:
            slot = self._slot(lease.id, lease.model)
            slot.cooldown_until = self._clock() + wait
            slot.remaining_tokens = 0
            slot.rate_limited += 1

    def report_auth_failure(self, lease: Lease) -> None:
        """Provider rejected the key: stop using it (all models) for an hour."""
        with self._lock:
            until = self._clock() + AUTH_DISABLE_S
            for (kid, _model), slot in self._slots.items():
                if kid == lease.id:
                    slot.disabled_until = until
            self._slot(lease.id, lease.model).disabled_until = until

    def snapshot(self) -> list[dict[str, object]]:
        """Per-key, per-model state for the health endpoint. No secrets."""
        now = self._clock()
        with self._lock:
            rows: list[dict[str, object]] = []
            for kid in self._keys:
                models = {m: s for (k, m), s in self._slots.items() if k == kid}
                rows.append(
                    {
                        "key_id": kid,
                        "models": {
                            m: {
                                "state": "disabled"
                                if now < s.disabled_until
                                else "cooling"
                                if now < s.cooldown_until
                                else "ready",
                                "cooldown_s": round(max(s.cooldown_until - now, 0.0), 1),
                                "remaining_tokens": s.remaining_tokens,
                                "remaining_requests": s.remaining_requests,
                                "calls": s.calls,
                                "rate_limited": s.rate_limited,
                            }
                            for m, s in models.items()
                        },
                    }
                )
            return rows


def _to_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None
