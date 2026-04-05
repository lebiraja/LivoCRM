"""Generate natural follow-up questions for missing CRM fields."""

from __future__ import annotations

import logging
from typing import Any

from app.services.bedrock_service import chat_completion, BedrockServiceError
from app.services.ai_engine.prompts import QUESTION_GENERATOR_SYSTEM, ENTITY_SCHEMAS

logger = logging.getLogger(__name__)


def generate_question(
    intent: str,
    collected: dict[str, Any],
    missing_required: list[str],
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    """Generate a natural follow-up question for missing fields.

    Args:
        intent: The current entity intent (ADD_CONTACT, etc.)
        collected: Fields already collected.
        missing_required: Required fields still missing.
        conversation_history: Prior messages for tone matching.

    Returns:
        A natural-language question string.
    """
    schema = ENTITY_SCHEMAS.get(intent, {})

    # Build context for the LLM
    collected_desc = ", ".join(f"{k}: {v}" for k, v in collected.items()) or "nothing yet"
    missing_desc = ", ".join(
        f"{f} ({schema.get(f, {}).get('description', f)})" for f in missing_required
    )

    # Also identify optional fields not yet collected
    optional_missing = [
        f for f in schema
        if not schema[f].get("required") and f not in collected
    ]
    optional_desc = ", ".join(optional_missing) if optional_missing else "none"

    user_prompt = (
        f"Creating a {intent.replace('ADD_', '').replace('LOG_', '').lower()}.\n"
        f"Already collected: {collected_desc}\n"
        f"Missing required fields: {missing_desc or 'none'}\n"
        f"Optional fields not yet collected: {optional_desc}\n\n"
        "Generate a single conversational follow-up question."
    )

    messages = []
    if conversation_history:
        for msg in conversation_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_prompt})

    try:
        return chat_completion(
            system_prompt=QUESTION_GENERATOR_SYSTEM,
            messages=messages,
            max_tokens=150,
            temperature=0.7,
        )
    except BedrockServiceError:
        # Deterministic fallback
        if missing_required:
            field = missing_required[0]
            desc = schema.get(field, {}).get("description", field)
            return f"Could you provide the {desc}?"
        return "Would you like to add any additional details, or shall I save this now?"
