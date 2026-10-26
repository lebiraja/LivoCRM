"""Process-wide logging with PII redaction (SEC-13).

Code should log ids, counts and latencies, never message text or model
output. As a backstop, the formatter masks anything that looks like an email
address or phone number, and every URL query string (WS tickets, stray JWTs,
search terms), in messages and exception text before it is written.
"""

from __future__ import annotations

import logging
import re

from app.config import settings

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# 9+ digits with optional spaces, dashes or brackets (no dots, so IP addresses stay readable)
_PHONE = re.compile(r"(?<![\w-])\+?\d[\d\s()-]{7,}\d(?![\w-])")
# Query string of a logged path, e.g. uvicorn's "GET /ws/chat/<id>?ticket=..." request lines
_QUERY = re.compile(r"(/[^\s?\"]*)\?[^\s\"]+")


def redact(text: str) -> str:
    return _PHONE.sub("[phone]", _EMAIL.sub("[email]", _QUERY.sub(r"\1?[redacted]", text)))


class RedactingFormatter(logging.Formatter):
    """Applies redact() to the message and traceback, not to the timestamp."""

    def formatMessage(self, record: logging.LogRecord) -> str:
        record.message = redact(record.message)
        return super().formatMessage(record)

    def formatException(self, ei: logging._SysExcInfoType) -> str:
        return redact(super().formatException(ei))


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.LOG_LEVEL)
    # uvicorn installs its own handlers before importing the app; send its lines through ours
    for name in ("uvicorn", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
