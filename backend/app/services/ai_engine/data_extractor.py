"""Extract structured entity data from natural language messages."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.bedrock_service import chat_completion, BedrockServiceError
from app.services.ai_engine.prompts import DATA_EXTRACTOR_SYSTEM, ENTITY_SCHEMAS

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    extracted: dict[str, Any] = field(default_factory=dict)
    missing_required: list[str] = field(default_factory=list)
    raw_response: str = ""


def extract_data(
    intent: str,
    user_message: str,
    already_collected: dict[str, Any] | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> ExtractionResult:
    """Extract entity fields from a user message based on the intent schema.

    Args:
        intent: One of the entity-creating intents (ADD_CONTACT, ADD_DEAL, etc.)
        user_message: The user's latest message.
        already_collected: Fields already collected in this session.
        conversation_history: Prior messages for context.

    Returns:
        ExtractionResult with extracted data and missing required fields.
    """
    schema = ENTITY_SCHEMAS.get(intent)
    if not schema:
        return ExtractionResult()

    already = already_collected or {}

    # Build the extraction prompt
    schema_desc = json.dumps(schema, indent=2)
    already_desc = json.dumps(already, indent=2) if already else "{}"

    user_prompt = (
        f"Entity schema:\n{schema_desc}\n\n"
        f"Already collected fields:\n{already_desc}\n\n"
        f"User message: {user_message}\n\n"
        "Extract fields from the user message. Include already_collected fields "
        "in the output. For missing_required, only list fields that are required "
        "and not in already_collected and not found in the message."
    )

    messages = []
    if conversation_history:
        for msg in conversation_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_prompt})

    try:
        raw = chat_completion(
            system_prompt=DATA_EXTRACTOR_SYSTEM,
            messages=messages,
            max_tokens=500,
            temperature=0.0,
        )
    except BedrockServiceError as exc:
        logger.warning(f"Data extraction failed (BedrockServiceError): {exc}")
        return ExtractionResult(extracted=already_collected or {})

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(cleaned)

        extracted = data.get("extracted", {})

        # Merge: anything already collected + newly extracted
        merged = {**already, **extracted}

        # Recompute missing required: check schema for required fields not in merged
        actual_missing = []
        for field_name, field_spec in schema.items():
            if field_spec.get("required") and field_name not in merged:
                actual_missing.append(field_name)

        return ExtractionResult(
            extracted=merged,
            missing_required=actual_missing,
            raw_response=raw,
        )
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse extractor response: {raw}")
        return ExtractionResult(extracted=already, raw_response=raw)
    except Exception as exc:
        logger.warning(f"Unexpected error in extract_data: {exc}")
        return ExtractionResult(extracted=already, raw_response=raw)
