"""Bedrock integration for generating CRM insights with deterministic fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class BedrockServiceError(RuntimeError):
    """Raised when Bedrock generation fails."""


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


def _extract_converse_text(response: dict[str, Any]) -> str:
    content = response.get("output", {}).get("message", {}).get("content", [])
    parts: list[str] = []
    for chunk in content:
        value = chunk.get("text")
        if value:
            parts.append(value)
    return "\n".join(parts).strip()


def generate_bedrock_insights(metrics: dict[str, Any]) -> list[str]:
    if not settings.BEDROCK_ENABLED:
        raise BedrockServiceError("Bedrock is disabled by configuration")

    client = boto3.client("bedrock-runtime", region_name=settings.AWS_DEFAULT_REGION)
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
