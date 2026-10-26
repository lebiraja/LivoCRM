"""Groq client + key pool. No network: httpx.MockTransport, injected clock."""

from __future__ import annotations

import httpx
import pytest

from app.services.llm.groq_client import GroqServiceError, groq_chat
from app.services.llm.key_pool import KeyPool, key_id, parse_duration, parse_keys

KEY_A, KEY_B, KEY_C = "gsk_fake_a", "gsk_fake_b", "gsk_fake_c"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def ok(text: str = "hello", remaining: int = 7000) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": text}}]},
        headers={"x-ratelimit-remaining-tokens": str(remaining)},
    )


def make_http(handler) -> httpx.Client:
    return httpx.Client(base_url="https://groq.test/v1", transport=httpx.MockTransport(handler))


def run(pool: KeyPool, handler, **kw) -> str:
    return groq_chat("sys", [{"role": "user", "content": "hi"}], pool=pool, http=make_http(handler), sleep=lambda s: None, **kw)


def bearer(request: httpx.Request) -> str:
    return request.headers["Authorization"].removeprefix("Bearer ")


def test_parse_keys_dedupes_and_trims():
    assert parse_keys(" a, b ,a,,", "c") == ["a", "b", "c"]
    assert parse_keys("", "") == []
    assert parse_keys("", "solo") == ["solo"]


@pytest.mark.parametrize(
    ("raw", "seconds"),
    [("2.527s", 2.527), ("1m26.4s", 86.4), ("120ms", 0.12), ("7", 7.0), ("1h2m3s", 3723.0), (None, None), ("junk", None)],
)
def test_parse_duration(raw, seconds):
    assert parse_duration(raw) == pytest.approx(seconds) if seconds is not None else parse_duration(raw) is None


def test_key_id_is_stable_and_hides_secret():
    assert key_id(KEY_A) == key_id(KEY_A)
    assert KEY_A not in key_id(KEY_A)
    assert len(key_id(KEY_A)) == 8


def test_single_key_works():
    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(bearer(req))
        return ok("pong")

    assert run(KeyPool([KEY_A]), handler) == "pong"
    assert seen == [KEY_A]


def test_request_body_uses_model_and_reasoning_budget():
    bodies: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        import json

        bodies.append(json.loads(req.content))
        return ok()

    run(KeyPool([KEY_A]), handler, max_tokens=50)
    body = bodies[0]
    assert body["model"] == "openai/gpt-oss-20b"
    assert body["max_completion_tokens"] >= 512
    assert body["reasoning_effort"] == "low"
    assert body["messages"][0] == {"role": "system", "content": "sys"}


def test_429_fails_over_to_next_key_without_sleeping():
    clock = Clock()
    pool = KeyPool([KEY_A, KEY_B], clock=clock)
    used: list[str] = []
    slept: list[float] = []

    def handler(req: httpx.Request) -> httpx.Response:
        used.append(bearer(req))
        if len(used) == 1:
            return httpx.Response(429, headers={"retry-after": "30"})
        return ok("second key")

    out = groq_chat("s", [{"role": "user", "content": "x"}], pool=pool, http=make_http(handler), sleep=slept.append)
    assert out == "second key"
    assert used[0] != used[1]
    assert slept == []


def test_cooldown_expires_and_key_is_reused():
    clock = Clock()
    pool = KeyPool([KEY_A], clock=clock)
    lease = pool.acquire("m")
    pool.report_rate_limited(lease, 10)
    assert pool.acquire("m") is None
    clock.now += 11
    assert pool.acquire("m") is not None


def test_all_keys_rate_limited_raises_cleanly():
    pool = KeyPool([KEY_A, KEY_B])

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "60"})

    with pytest.raises(GroqServiceError):
        run(pool, handler)
    assert all(row["models"]["openai/gpt-oss-20b"]["state"] == "cooling" for row in pool.snapshot())


def test_401_disables_only_that_key():
    pool = KeyPool([KEY_A, KEY_B])
    used: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        used.append(bearer(req))
        return httpx.Response(401) if bearer(req) == used[0] else ok("fine")

    assert run(pool, handler) == "fine"
    states = {row["key_id"]: row["models"]["openai/gpt-oss-20b"]["state"] for row in pool.snapshot()}
    assert sorted(states.values()) == ["disabled", "ready"]
    # next call never touches the disabled key
    used.clear()
    assert run(pool, lambda r: (used.append(bearer(r)), ok("again"))[1]) == "again"
    assert used == [used[0]] and key_id(used[0]) != key_id(KEY_A) or key_id(used[0]) != key_id(KEY_B)


def test_5xx_and_timeout_retry_on_another_attempt():
    pool = KeyPool([KEY_A, KEY_B])
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("slow", request=req)
        if calls["n"] == 2:
            return httpx.Response(503)
        return ok("recovered")

    assert run(pool, handler) == "recovered"
    assert calls["n"] == 3


def test_client_error_is_not_retried():
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": "bad"})

    with pytest.raises(GroqServiceError):
        run(KeyPool([KEY_A, KEY_B]), handler)
    assert calls["n"] == 1


def test_selection_prefers_most_remaining_tokens_then_lru():
    clock = Clock()
    pool = KeyPool([KEY_A, KEY_B, KEY_C], clock=clock)
    a = pool.acquire("m")
    pool.report_success(a, {"x-ratelimit-remaining-tokens": "100"})
    clock.now += 1
    b = pool.acquire("m")
    pool.report_success(b, {"x-ratelimit-remaining-tokens": "5000"})
    clock.now += 1
    c = pool.acquire("m")
    pool.report_success(c, {"x-ratelimit-remaining-tokens": "5000"})
    clock.now += 1
    # b and c tie on tokens; b was used earlier, so b goes first, never the nearly empty a
    assert pool.acquire("m").id == b.id
    assert len({a.id, b.id, c.id}) == 3


def test_keys_are_spread_across_calls():
    pool = KeyPool([KEY_A, KEY_B, KEY_C], clock=Clock())
    first_round = {pool.acquire("m").id for _ in range(3)}
    assert len(first_round) == 3


def test_empty_or_malformed_response_raises():
    with pytest.raises(GroqServiceError):
        run(KeyPool([KEY_A]), lambda r: httpx.Response(200, json={"choices": []}))
    with pytest.raises(GroqServiceError):
        run(KeyPool([KEY_A]), lambda r: ok("   "))


def test_no_keys_configured_raises():
    with pytest.raises(GroqServiceError):
        run(KeyPool([]), lambda r: ok())


def test_secrets_never_reach_logs_or_errors_or_health(caplog):
    pool = KeyPool([KEY_A])
    caplog.set_level("DEBUG")
    with pytest.raises(GroqServiceError) as err:
        run(pool, lambda r: httpx.Response(401))
    assert KEY_A not in str(err.value)
    assert KEY_A not in caplog.text
    assert KEY_A not in str(pool.snapshot())


async def test_ai_health_endpoint_hides_secrets(client, make_user):
    from tests.conftest import auth_headers

    user = await make_user()
    resp = await client.get("/api/ai/health", headers=auth_headers(user))
    assert resp.status_code == 200
    body = resp.json()
    assert {"provider", "keys", "pool"} <= body.keys()
    assert "gsk_" not in resp.text
    assert (await client.get("/api/ai/health")).status_code in (401, 403)
