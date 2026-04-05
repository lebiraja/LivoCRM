"""Auto-generate concise titles for chat sessions after the first exchange.

Uses Bedrock LLM to produce a short, descriptive title from the first
user message and AI response. Falls back to extracting the first few
words from the user message if LLM generation fails.

This runs asynchronously to never block chat response delivery.
"""

from __future__ import annotations

import logging
import re

from app.services.bedrock_service import chat_completion, BedrockServiceError

logger = logging.getLogger(__name__)

_TITLE_SYSTEM_PROMPT = (
    "You are a title generator for a CRM assistant chat. "
    "Given the first user message and assistant reply, produce a short, "
    "descriptive title (max 4 words, max 50 characters). "
    "Output ONLY the title text — no quotes, no prefix like 'Title:', "
    "no punctuation at the end. Examples: 'Add New Contact', "
    "'Pipeline Forecast Q4', 'Score Marketing Leads'."
)


def generate_session_title(
    user_message: str,
    ai_response: str,
) -> str:
    """Generate a concise session title from the first exchange.

    Tries LLM first, falls back to first 4 words of user message.

    Args:
        user_message: The first message the user sent.
        ai_response: The AI's first response.

    Returns:
        A cleaned, truncated title string (never empty).
    """
    try:
        raw_title = chat_completion(
            system_prompt=_TITLE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"User message: {user_message}\n\n"
                        f"Assistant response: {ai_response[:200]}"
                    ),
                }
            ],
            max_tokens=30,
            temperature=0.3,
        )
        title = _normalize_title(raw_title)
        if title:
            logger.info("Auto-named session: %r", title)
            return title
    except BedrockServiceError as exc:
        logger.warning("LLM title generation failed: %s", exc)

    # Fallback: first 4 words of user message
    return _fallback_title(user_message)


def _normalize_title(raw: str) -> str:
    """Clean and truncate an LLM-generated title.

    Rules (from skill spec):
    - Strip prefixes like 'Title:' and surrounding quotes.
    - Cap at 4 words and 50 characters.
    - Return empty string if result is invalid.
    """
    title = raw.strip()

    # Remove common LLM prefixes
    title = re.sub(r"^(title\s*:\s*)", "", title, flags=re.IGNORECASE)

    # Remove surrounding quotes
    title = title.strip("\"'`")

    # Remove trailing punctuation
    title = title.rstrip(".,;:!?")

    # Cap at 4 words
    words = title.split()
    if len(words) > 4:
        title = " ".join(words[:4])

    # Cap at 50 characters
    if len(title) > 50:
        title = title[:47] + "..."

    # Validate minimum quality
    if len(title) < 2:
        return ""

    return title


def _fallback_title(user_message: str) -> str:
    """Derive a title from the first 4 words of the user message."""
    words = user_message.strip().split()[:4]
    title = " ".join(words)

    if len(title) > 50:
        title = title[:47] + "..."

    return title if len(title) >= 2 else "Chat"
