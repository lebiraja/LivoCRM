"""Classify user messages into CRM intents using Bedrock."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum

from app.services.bedrock_service import chat_completion, BedrockServiceError
from app.services.ai_engine.prompts import INTENT_CLASSIFIER_SYSTEM

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    ADD_CONTACT = "ADD_CONTACT"
    ADD_DEAL = "ADD_DEAL"
    LOG_ACTIVITY = "LOG_ACTIVITY"
    UPDATE_CONTACT = "UPDATE_CONTACT"
    UPDATE_DEAL = "UPDATE_DEAL"
    QUERY_DATA = "QUERY_DATA"
    GENERAL_CHAT = "GENERAL_CHAT"
    MULTI_INTENT = "MULTI_INTENT"


@dataclass
class ClassificationResult:
    intent: Intent
    confidence: float


def classify_intent(
    user_message: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> ClassificationResult:
    """Classify a user message into a CRM intent.

    Args:
        user_message: The latest message from the user.
        conversation_history: Previous messages for context (optional).

    Returns:
        ClassificationResult with intent and confidence score.
    """
    messages = []
    if conversation_history:
        # Include last 4 messages for context (keeps token usage low)
        for msg in conversation_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        raw = chat_completion(
            system_prompt=INTENT_CLASSIFIER_SYSTEM,
            messages=messages,
            max_tokens=100,
            temperature=0.0,
        )
    except BedrockServiceError as exc:
        logger.warning(f"Intent classification failed (BedrockServiceError): {exc}")
        return ClassificationResult(intent=Intent.GENERAL_CHAT, confidence=0.0)

    try:
        # Strip markdown fences if model wraps in ```json ... ```
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(cleaned)
        intent_str = data.get("intent", "GENERAL_CHAT").upper()
        confidence = float(data.get("confidence", 0.5))
        intent = Intent(intent_str)
        return ClassificationResult(intent=intent, confidence=confidence)
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning("Could not parse intent response: %s — raw: %s", exc, raw[:200])
        return ClassificationResult(intent=Intent.GENERAL_CHAT, confidence=0.0)
