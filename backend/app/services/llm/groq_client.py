"""Groq chat-completions client (OpenAI-compatible) on top of the key pool.

Synchronous on purpose: the AI engine already runs it inside asyncio.to_thread.
Never logs prompts, completions or key material; keys appear only as key ids.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

import httpx

from app.config import settings
from app.services.bedrock_service import BedrockServiceError
from app.services.llm.key_pool import KeyPool, Lease, parse_duration, parse_keys

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 4
MAX_WAIT_S = 2.0
MIN_COMPLETION_TOKENS = 512  # gpt-oss spends part of the budget on reasoning


class GroqServiceError(BedrockServiceError):
    """Groq call failed; callers already degrade to deterministic fallbacks."""


_pool: KeyPool | None = None


def get_pool() -> KeyPool:
    global _pool
    if _pool is None:
        _pool = KeyPool(parse_keys(settings.GROQ_API_KEYS, settings.GROQ_API_KEY))
    return _pool


def reset_pool() -> None:
    global _pool
    _pool = None


def _sanitize(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Drop leading assistant turns, merge same-role neighbours, never send an empty list."""
    out: list[dict[str, str]] = []
    for m in messages:
        if not out and m["role"] != "user":
            continue
        if out and out[-1]["role"] == m["role"]:
            out[-1]["content"] += "\n\n" + m["content"]
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out or [{"role": "user", "content": "Hello"}]


def groq_chat(
    system_prompt: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
    model: str | None = None,
    pool: KeyPool | None = None,
    http: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    pool = pool or get_pool()
    if len(pool) == 0:
        raise GroqServiceError("no Groq API key configured")
    model = model or settings.GROQ_MODEL_FAST
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, *_sanitize(messages)],
        "max_completion_tokens": max(max_tokens or 0, MIN_COMPLETION_TOKENS),
        "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature,
        "reasoning_effort": "low",
        "include_reasoning": False,
    }
    attempts = min(len(pool) + 1, MAX_ATTEMPTS)
    client = http or httpx.Client(
        base_url=settings.GROQ_BASE_URL,
        timeout=httpx.Timeout(settings.LLM_TIMEOUT_S, connect=3.0),
    )
    try:
        last = "no attempt made"
        for _ in range(attempts):
            lease = pool.acquire(model)
            if lease is None:
                wait = pool.next_available_in(model)
                if wait is None or wait > MAX_WAIT_S:
                    raise GroqServiceError("all Groq keys are rate limited or disabled")
                sleep(wait)
                lease = pool.acquire(model)
                if lease is None:
                    raise GroqServiceError("all Groq keys are rate limited or disabled")
            text, failure = _attempt(client, pool, lease, body)
            if text is not None:
                return text
            last = failure
        raise GroqServiceError(last)
    finally:
        if http is None:
            client.close()


def _attempt(
    client: httpx.Client, pool: KeyPool, lease: Lease, body: dict[str, object]
) -> tuple[str | None, str]:
    """Return (text, "") on success, or (None, failure label) when another key should be tried."""
    try:
        resp = client.post(
            "/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {lease.secret}"},
        )
    except httpx.TimeoutException:
        logger.warning("groq timeout key=%s model=%s", lease.id, lease.model)
        return None, "timeout"
    except httpx.HTTPError as exc:
        logger.warning("groq transport error key=%s type=%s", lease.id, type(exc).__name__)
        return None, "transport error"

    status = resp.status_code
    if status == 429:
        retry_after = parse_duration(resp.headers.get("retry-after"))
        pool.report_rate_limited(lease, retry_after)
        logger.warning("groq 429 key=%s model=%s retry_after=%s", lease.id, lease.model, retry_after)
        return None, "rate limited"
    if status in (401, 403):
        pool.report_auth_failure(lease)
        logger.error("groq rejected key=%s status=%s", lease.id, status)
        return None, "key rejected"
    if status >= 500 or status in (408, 498):
        logger.warning("groq server error key=%s status=%s", lease.id, status)
        return None, f"server error {status}"
    if status >= 400:
        raise GroqServiceError(f"Groq rejected the request (HTTP {status})")

    pool.report_success(lease, resp.headers)
    try:
        text = (resp.json()["choices"][0]["message"].get("content") or "").strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise GroqServiceError("unexpected Groq response shape") from exc
    if not text:
        raise GroqServiceError("Groq response did not contain usable text")
    return text, ""
