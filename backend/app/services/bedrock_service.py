"""Bedrock integration for CRM insights and generic AI chat completion."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

logger = logging.getLogger(__name__)

# ── Shared Bedrock client (module-level lazy singleton) ─────────────────────
_bedrock_client = None

# Bound every call: boto3 defaults are 60 s timeouts with several retries
_CLIENT_CONFIG = Config(connect_timeout=3, read_timeout=15, retries={"max_attempts": 2})

# Caps concurrent LLM calls process-wide; async callers hold a slot around asyncio.to_thread()
llm_slots = asyncio.Semaphore(8)


def _get_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime", region_name=settings.AWS_DEFAULT_REGION, config=_CLIENT_CONFIG
        )
    return _bedrock_client


class BedrockServiceError(RuntimeError):
    """Raised when Bedrock generation fails."""


# ── Generic chat completion (used by AI engine) ─────────────────────────────


def _extract_converse_text(response: dict[str, Any]) -> str:
    content = response.get("output", {}).get("message", {}).get("content", [])
    parts: list[str] = []
    for chunk in content:
        value = chunk.get("text")
        if value:
            parts.append(value)
    return "\n".join(parts).strip()


def chat_completion(
    system_prompt: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
    model_id: str | None = None,
) -> str:
    """Send a multi-turn conversation to Bedrock Converse and return the text.

    Args:
        system_prompt: System-level instruction for the model.
        messages: List of {"role": "user"|"assistant", "content": "..."} dicts.
        max_tokens: Override default max tokens.
        temperature: Override default temperature.
        model_id: Override default model.

    Returns:
        Raw text string from the model.

    Raises:
        BedrockServiceError: If the API call fails or returns empty text.
    """
    if not settings.BEDROCK_ENABLED:
        raise BedrockServiceError("Bedrock is disabled by configuration")

    client = _get_client()
    # Sanitize messages to meet Bedrock Converse API requirements:
    # 1. Must start with a 'user' message
    # 2. Roles must strictly alternate
    sanitized = []
    for m in messages:
        if not sanitized and m["role"] != "user":
            continue  # Drop leading assistant messages
        if sanitized and sanitized[-1]["role"] == m["role"]:
            # Combine consecutive messages of the same role
            sanitized[-1]["content"] += "\n\n" + m["content"]
        else:
            sanitized.append({"role": m["role"], "content": m["content"]})
            
    # Guarantee there's at least one message
    if not sanitized:
        sanitized.append({"role": "user", "content": "Hello"})
        
    formatted_messages = [
        {"role": m["role"], "content": [{"text": m["content"]}]}
        for m in sanitized
    ]

    try:
        response = client.converse(
            modelId=model_id or settings.BEDROCK_LLM_MODEL,
            system=[{"text": system_prompt}],
            messages=formatted_messages,
            inferenceConfig={
                "maxTokens": max_tokens or settings.BEDROCK_MAX_TOKENS,
                "temperature": temperature if temperature is not None else settings.BEDROCK_TEMPERATURE,
            },
        )
    except (ClientError, BotoCoreError) as exc:
        raise BedrockServiceError(str(exc)) from exc

    text = _extract_converse_text(response)
    if not text:
        raise BedrockServiceError("Bedrock response did not contain usable text")
    return text


# ── Dashboard insights (existing feature) ───────────────────────────────────


def _build_prompt(metrics: dict[str, Any]) -> str:
    return (
        "You are an assistant for a CRM sales dashboard. "
        "Generate exactly 3 concise actionable insights as plain text lines. "
        "No markdown, no numbering, each line under 22 words.\n\n"
        f"CRM Metrics:\n{json.dumps(metrics, default=str, indent=2)}"
    )


def _extract_lines(text: str) -> list[str]:
    lines = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    return lines[:3]


def generate_bedrock_insights(metrics: dict[str, Any]) -> list[str]:
    if not settings.BEDROCK_ENABLED:
        raise BedrockServiceError("Bedrock is disabled by configuration")

    client = _get_client()
    prompt = _build_prompt(metrics)

    try:
        response = client.converse(
            modelId=settings.BEDROCK_LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            inferenceConfig={
                "maxTokens": settings.BEDROCK_MAX_TOKENS,
                "temperature": settings.BEDROCK_TEMPERATURE,
            },
        )
    except (ClientError, BotoCoreError) as exc:
        raise BedrockServiceError(str(exc)) from exc

    text = _extract_converse_text(response)
    lines = _extract_lines(text)
    if not lines:
        raise BedrockServiceError("Bedrock response did not contain usable text")

    return lines


def generate_fallback_insights(metrics: dict[str, Any]) -> list[str]:
    contacts = int(metrics.get("contacts", 0))
    deals = int(metrics.get("deals", 0))
    activities = int(metrics.get("activities", 0))
    pipeline_value = float(metrics.get("pipeline_value", 0))

    return [
        f"You currently have {contacts} contacts and {deals} active deals to prioritize this week.",
        f"Recent activity count is {activities}; schedule follow-ups for contacts with no touches in 7 days.",
        f"Pipeline value is ${pipeline_value:,.0f}; focus proposal-stage deals first to improve near-term conversion.",
    ]


def get_insights(metrics: dict[str, Any]) -> tuple[list[str], str]:
    try:
        insights = generate_bedrock_insights(metrics)
        return insights, f"bedrock:{settings.BEDROCK_LLM_MODEL}"
    except BedrockServiceError as exc:
        logger.warning("Bedrock insights failed, using fallback: %s", exc)
        return generate_fallback_insights(metrics), "fallback:deterministic"
