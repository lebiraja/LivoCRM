"""Follow-up copilot: drafts an English and a Tamil message for a human to approve.

The model sees only the message purpose and the appointment time (IST), never the patient's
name or phone. It is told to mention the time only, with no clinical content. Any failure,
including malformed output, falls back to fixed templates, so a draft always exists.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.services.bedrock_service import chat_completion, llm_slots

logger = logging.getLogger(__name__)

# India observes no DST, so a fixed offset is exact and avoids a tz database dependency
IST = timezone(timedelta(hours=5, minutes=30), "IST")

_SYSTEM_PROMPT = (
    "You write short appointment messages for a clinic front desk, in English and in Tamil script. "
    'Reply with only a JSON object with the keys "en" and "ta". '
    "Mention only the appointment time. Never give medical advice, diagnoses, symptoms or medicines. "
    "Keep each message under 300 characters."
)

_PURPOSE = {
    "reminder": "a reminder ahead of the appointment",
    "recovery": "a follow-up after a missed appointment, offering to rebook",
    "general": "a general follow-up asking the patient to reply",
}

# Deterministic fallback: (English, Tamil) per kind, filled with the patient's name and the time
_TEMPLATES: dict[str, tuple[str, str]] = {
    "reminder": (
        "Hello {name}, this is a reminder from the clinic. Your appointment is on {when}. "
        "Reply to confirm or to reschedule.",
        "வணக்கம் {name}, இது கிளினிக்கிலிருந்து நினைவூட்டல். உங்கள் சந்திப்பு {when} அன்று உள்ளது. "
        "உறுதிப்படுத்த அல்லது நேரத்தை மாற்ற பதில் அனுப்புங்கள்.",
    ),
    "recovery": (
        "Hello {name}, we missed you at your appointment on {when}. Reply if you would like to rebook.",
        "வணக்கம் {name}, {when} அன்று உங்கள் சந்திப்புக்கு நீங்கள் வரவில்லை. "
        "மீண்டும் முன்பதிவு செய்ய விரும்பினால் பதில் அனுப்புங்கள்.",
    ),
    "general": (
        "Hello {name}, this is the clinic. Reply to this message and our front desk will help you.",
        "வணக்கம் {name}, இது கிளினிக். இந்த செய்திக்கு பதில் அனுப்புங்கள், எங்கள் வரவேற்பு மேசை உதவும்.",
    ),
}


class DraftPair(BaseModel):
    en: str = Field(min_length=1, max_length=500)
    ta: str = Field(min_length=1, max_length=500)


def _kind(reason: str, starts_at: datetime | None) -> str:
    if starts_at is None:
        return "general"
    if reason == "no_show_recovery":
        return "recovery"
    if reason.startswith("reminder_"):
        return "reminder"
    return "general"


def _user_prompt(kind: str, when: str | None) -> str:
    time_line = f"Appointment time: {when}." if when else "No appointment time applies."
    return f"Message purpose: {_PURPOSE[kind]}. {time_line}"


async def draft_follow_up(*, name: str, reason: str, starts_at: datetime | None) -> DraftPair:
    when = None if starts_at is None else f"{starts_at.astimezone(IST):%d %b %Y, %I:%M %p} IST"
    kind = _kind(reason, starts_at)
    try:
        async with llm_slots:
            raw = await asyncio.to_thread(
                chat_completion,
                system_prompt=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _user_prompt(kind, when)}],
                max_tokens=400,
                temperature=0.3,
            )
        return DraftPair.model_validate_json(raw)
    except Exception as exc:
        # Any failure (provider down, malformed JSON, schema mismatch) degrades to the template
        logger.warning("Follow-up draft fell back to template: %s", type(exc).__name__)
        en, ta = _TEMPLATES[kind]
        return DraftPair(en=en.format(name=name, when=when), ta=ta.format(name=name, when=when))
