"""Test doubles that keep the suite off the network."""

from __future__ import annotations

import time
from typing import Any

from botocore.exceptions import BotoCoreError


class FakeLLMProvider:
    """Stands in for the boto3 bedrock-runtime client installed as `bedrock_service._bedrock_client`.

    Replays scripted replies in order. With an empty script it raises like a
    failed Bedrock call, so callers take their deterministic fallbacks.
    `delay` blocks the calling thread, mimicking a slow synchronous SDK call.
    Interim seam until the Phase 1 provider interface replaces Bedrock.
    """

    def __init__(self) -> None:
        self.replies: list[str] = []
        self.calls: list[dict[str, Any]] = []
        self.delay: float = 0.0

    def script(self, *replies: str) -> None:
        self.replies.extend(replies)

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        if self.delay:
            time.sleep(self.delay)
        if not self.replies:
            raise BotoCoreError()
        return {"output": {"message": {"content": [{"text": self.replies.pop(0)}]}}}
