"""SEC-13/23/26: no PII or raw LLM output in logs; CORS from env; docs gated; no model id leak."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.logging_config import RedactingFormatter
from app.models.contact import Contact
from app.models.user import User
from app.services.ai_engine.data_extractor import extract_data
from app.services.ai_engine.intent_classifier import classify_intent
from tests.conftest import auth_headers
from tests.fakes import FakeLLMProvider

PII = re.compile(r"asha@example\.com|98400\s?12345")


def test_no_pii_in_logs(llm: FakeLLMProvider, caplog: pytest.LogCaptureFixture) -> None:
    leak = "Sure! Asha, asha@example.com, 98400 12345"
    llm.script(leak, leak)

    with caplog.at_level(logging.DEBUG):
        classify_intent("add Asha asha@example.com 98400 12345")
        extract_data("ADD_CONTACT", "add Asha asha@example.com 98400 12345")

    assert caplog.records, "parse failures should still be logged"
    assert not PII.search(caplog.text)


def test_redacting_formatter_masks_email_and_phone() -> None:
    record = logging.LogRecord("x", logging.WARNING, __file__, 1, "saved %s / %s", ("asha@example.com", "+91 98400 12345"), None)

    line = RedactingFormatter("%(asctime)s %(message)s").format(record)

    assert not PII.search(line) and "[email]" in line and "[phone]" in line
    assert "192.168.112.1" in RedactingFormatter("%(message)s").format(
        logging.LogRecord("x", logging.INFO, __file__, 1, "client 192.168.112.1", None, None)
    )


@pytest.mark.parametrize(
    "line",
    [
        '1.2.3.4 - "WebSocket /ws/dashboard/abc?token=eyJhbGciOi.payload.sig" 403',
        '1.2.3.4 - "WebSocket /ws/chat/abc?ticket=Zx_9-secret" [accepted]',
        '1.2.3.4:0 - "GET /api/contacts/?search=Priya HTTP/1.1" 200',
    ],
)
def test_query_strings_redacted(line: str) -> None:
    record = logging.LogRecord("uvicorn.error", logging.INFO, __file__, 1, line, None, None)

    out = RedactingFormatter("%(message)s").format(record)

    assert not re.search(r"eyJ|secret|Priya", out) and "?[redacted]" in out


def test_uvicorn_logs_use_redacting_handler() -> None:
    from app.logging_config import configure_logging

    for name in ("uvicorn", "uvicorn.access"):  # what uvicorn's own dictConfig sets up
        logging.getLogger(name).handlers = [logging.StreamHandler()]
        logging.getLogger(name).propagate = False

    configure_logging()

    for name in ("uvicorn", "uvicorn.access"):
        assert logging.getLogger(name).handlers == [] and logging.getLogger(name).propagate
    assert isinstance(logging.getLogger().handlers[0].formatter, RedactingFormatter)


@pytest.fixture
async def user(make_user: Callable[..., Awaitable[User]]) -> User:
    return await make_user()


async def test_generated_by_hides_model_id(client: AsyncClient, user: User, llm: FakeLLMProvider) -> None:
    llm.script("Call proposal deals\nLog more activities\nFollow up leads")

    with_ai = (await client.post("/api/ai/insights", headers=auth_headers(user))).json()
    fallback = (await client.post("/api/ai/insights", headers=auth_headers(user))).json()

    assert (with_ai["generated_by"], fallback["generated_by"]) == ("ai", "fallback")


@pytest.mark.parametrize(("search", "expected"), [("%", ["100% Clinic"]), ("_", ["A_B"]), ("clinic", ["100% Clinic"])])
async def test_contact_search_escapes_wildcards(
    client: AsyncClient, db: AsyncSession, user: User, search: str, expected: list[str]
) -> None:
    db.add_all([Contact(user_id=user.id, name=n) for n in ("100% Clinic", "A_B", "Asha")])
    await db.commit()

    response = await client.get("/api/contacts/", params={"search": search}, headers=auth_headers(user))

    assert sorted(c["name"] for c in response.json()["items"]) == expected


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/api/docs", "/api/openapi.json"])
async def test_api_docs_disabled_by_default(client: AsyncClient, path: str) -> None:
    assert (await client.get(path)).status_code == 404


def test_cors_origins_from_env() -> None:
    settings = Settings(CORS_ORIGINS="https://crm.example.in, http://localhost:3500")

    assert settings.cors_origins == ["https://crm.example.in", "http://localhost:3500"]


@pytest.mark.parametrize(("origin", "allowed"), [("http://localhost:3500", True), ("https://evil.example", False)])
async def test_cors_preflight(client: AsyncClient, origin: str, allowed: bool) -> None:
    response = await client.options(
        "/api/contacts/", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )

    assert (response.headers.get("access-control-allow-origin") == origin) is allowed
