"""Orchestrator — state machine driving the AI conversation lifecycle."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.services.bedrock_service import chat_completion, BedrockServiceError
from app.services.ai_engine.intent_classifier import classify_intent, Intent
from app.services.ai_engine.data_extractor import extract_data
from app.services.ai_engine.question_generator import generate_question
from app.services.ai_engine.prompts import SYSTEM_PERSONA, CONFIRMATION_SYSTEM

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    IDLE = "IDLE"
    CLASSIFYING = "CLASSIFYING"
    COLLECTING = "COLLECTING"
    CONFIRMING = "CONFIRMING"
    SAVING = "SAVING"
    COMPLETE = "COMPLETE"


# Intents that create or modify entities (trigger the data collection flow)
ENTITY_INTENTS = {
    Intent.ADD_CONTACT,
    Intent.ADD_DEAL,
    Intent.LOG_ACTIVITY,
    Intent.UPDATE_CONTACT,
    Intent.UPDATE_DEAL,
}


@dataclass
class OrchestratorResponse:
    """Returned to the caller after processing a user message."""

    ai_message: str
    session_state: SessionState
    intent: str | None = None
    extracted_data: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    ready_to_save: bool = False


@dataclass
class SessionContext:
    """In-memory state for a conversation session."""

    state: SessionState = SessionState.IDLE
    intent: Intent | None = None
    collected_data: dict[str, Any] = field(default_factory=dict)
    missing_required: list[str] = field(default_factory=list)
    history: list[dict[str, str]] = field(default_factory=list)


class Orchestrator:
    """Drives the conversation lifecycle from intent to entity creation.

    Usage::

        orch = Orchestrator()
        response = orch.process_message(context, "Add John from Acme, john@acme.io")
        # response.ai_message = "Got it! Here's what I have..."
        # response.session_state = CONFIRMING
        # response.extracted_data = {"name": "John", "company": "Acme", ...}
    """

    def process_message(
        self,
        ctx: SessionContext,
        user_message: str,
    ) -> OrchestratorResponse:
        """Process one user message and advance the session state.

        Args:
            ctx: The current session context (mutated in-place).
            user_message: Raw text from the user.

        Returns:
            OrchestratorResponse with the AI reply and updated state.
        """
        # Record user message in history
        ctx.history.append({"role": "user", "content": user_message})

        # ── Route based on current state ────────────────────────────────────
        if ctx.state == SessionState.IDLE:
            return self._handle_idle(ctx, user_message)
        elif ctx.state == SessionState.COLLECTING:
            return self._handle_collecting(ctx, user_message)
        elif ctx.state == SessionState.CONFIRMING:
            return self._handle_confirming(ctx, user_message)
        else:
            # SAVING / COMPLETE — shouldn't receive messages, reset
            ctx.state = SessionState.IDLE
            return self._handle_idle(ctx, user_message)

    # ── State handlers ──────────────────────────────────────────────────────

    def _handle_idle(
        self, ctx: SessionContext, user_message: str
    ) -> OrchestratorResponse:
        """Classify intent and begin data collection if entity-related."""
        ctx.state = SessionState.CLASSIFYING

        result = classify_intent(user_message, ctx.history)
        ctx.intent = result.intent

        if result.intent in ENTITY_INTENTS:
            # Move straight to data collection
            return self._collect_data(ctx, user_message)

        if result.intent == Intent.GENERAL_CHAT:
            return self._handle_general_chat(ctx, user_message)

        if result.intent == Intent.QUERY_DATA:
            return self._handle_query(ctx, user_message)

        if result.intent == Intent.MULTI_INTENT:
            ai_msg = (
                "It sounds like you're trying to do multiple things. "
                "Could you tell me about one thing at a time? "
                "For example, let's start with the contact first."
            )
            ctx.state = SessionState.IDLE
            response = OrchestratorResponse(
                ai_message=ai_msg,
                session_state=ctx.state,
                intent=result.intent.value,
            )
            ctx.history.append({"role": "assistant", "content": ai_msg})
            return response

        # Fallback
        ctx.state = SessionState.IDLE
        return self._handle_general_chat(ctx, user_message)

    def _collect_data(
        self, ctx: SessionContext, user_message: str
    ) -> OrchestratorResponse:
        """Extract data from message and decide next step."""
        ctx.state = SessionState.COLLECTING

        extraction = extract_data(
            intent=ctx.intent.value,
            user_message=user_message,
            already_collected=ctx.collected_data,
            conversation_history=ctx.history,
        )

        ctx.collected_data = extraction.extracted
        ctx.missing_required = extraction.missing_required

        if extraction.missing_required:
            # Still need more info — ask a follow-up question
            question = generate_question(
                intent=ctx.intent.value,
                collected=ctx.collected_data,
                missing_required=extraction.missing_required,
                conversation_history=ctx.history,
            )
            response = OrchestratorResponse(
                ai_message=question,
                session_state=ctx.state,
                intent=ctx.intent.value,
                extracted_data=ctx.collected_data,
                missing_fields=extraction.missing_required,
            )
            ctx.history.append({"role": "assistant", "content": question})
            return response

        # All required fields collected → present confirmation
        return self._present_confirmation(ctx)

    def _handle_collecting(
        self, ctx: SessionContext, user_message: str
    ) -> OrchestratorResponse:
        """Continue collecting data from follow-up messages."""
        return self._collect_data(ctx, user_message)

    def _present_confirmation(self, ctx: SessionContext) -> OrchestratorResponse:
        """Build and present a confirmation summary."""
        ctx.state = SessionState.CONFIRMING

        entity_type = (
            ctx.intent.value
            .replace("ADD_", "")
            .replace("LOG_", "")
            .replace("UPDATE_", "")
            .lower()
        )

        # Ask LLM to format a nice confirmation message
        data_str = json.dumps(ctx.collected_data, indent=2)
        user_prompt = (
            f"I'm about to save a new {entity_type} with this data:\n{data_str}\n\n"
            "Please format this as a brief confirmation and ask if it looks correct."
        )

        try:
            ai_msg = chat_completion(
                system_prompt=CONFIRMATION_SYSTEM,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=300,
                temperature=0.3,
            )
        except BedrockServiceError:
            # Deterministic fallback
            lines = [f"  • {k}: {v}" for k, v in ctx.collected_data.items()]
            ai_msg = (
                f"Here's the {entity_type} I'll create:\n"
                + "\n".join(lines)
                + "\n\nDoes this look correct? (yes/no)"
            )

        response = OrchestratorResponse(
            ai_message=ai_msg,
            session_state=ctx.state,
            intent=ctx.intent.value,
            extracted_data=ctx.collected_data,
            missing_fields=[],
            ready_to_save=True,
        )
        ctx.history.append({"role": "assistant", "content": ai_msg})
        return response

    def _handle_confirming(
        self, ctx: SessionContext, user_message: str
    ) -> OrchestratorResponse:
        """Handle yes/no confirmation response."""
        msg = user_message.strip().lower()

        # Check for affirmative responses
        if any(word in msg for word in ["yes", "yep", "yeah", "correct", "confirm", "save", "looks good", "go ahead", "do it"]):
            ctx.state = SessionState.SAVING
            entity_type = (
                ctx.intent.value
                .replace("ADD_", "")
                .replace("LOG_", "")
                .replace("UPDATE_", "")
                .lower()
            )
            ai_msg = f"✅ Saving your {entity_type} now..."
            response = OrchestratorResponse(
                ai_message=ai_msg,
                session_state=ctx.state,
                intent=ctx.intent.value,
                extracted_data=ctx.collected_data,
                ready_to_save=True,
            )
            ctx.history.append({"role": "assistant", "content": ai_msg})
            return response

        # Check for negative / change requests
        if any(word in msg for word in ["no", "nope", "change", "edit", "wrong", "fix", "update"]):
            ctx.state = SessionState.COLLECTING
            ai_msg = "No problem! What would you like to change?"
            response = OrchestratorResponse(
                ai_message=ai_msg,
                session_state=ctx.state,
                intent=ctx.intent.value,
                extracted_data=ctx.collected_data,
            )
            ctx.history.append({"role": "assistant", "content": ai_msg})
            return response

        # Ambiguous — extract any additional data and re-confirm
        return self._collect_data(ctx, user_message)

    def _handle_general_chat(
        self, ctx: SessionContext, user_message: str
    ) -> OrchestratorResponse:
        """Handle greetings, thanks, and general conversation."""
        ctx.state = SessionState.IDLE

        try:
            ai_msg = chat_completion(
                system_prompt=SYSTEM_PERSONA,
                messages=ctx.history,
                max_tokens=200,
                temperature=0.7,
            )
        except BedrockServiceError:
            ai_msg = (
                "Hi! I'm Livo, your CRM assistant. I can help you add contacts, "
                "create deals, log activities, and more. What would you like to do?"
            )

        response = OrchestratorResponse(
            ai_message=ai_msg,
            session_state=ctx.state,
        )
        ctx.history.append({"role": "assistant", "content": ai_msg})
        return response

    def _handle_query(
        self, ctx: SessionContext, user_message: str
    ) -> OrchestratorResponse:
        """Handle data queries (count, search, stats).

        Note: Full query support will be implemented in Phase 2 when we have
        access to the database session. For now, provide a helpful response.
        """
        ctx.state = SessionState.IDLE

        ai_msg = (
            "I can see you're asking about your data. Query support is coming soon! "
            "For now, you can check your dashboard for stats, or I can help you "
            "add contacts, deals, or log activities."
        )

        response = OrchestratorResponse(
            ai_message=ai_msg,
            session_state=ctx.state,
            intent=Intent.QUERY_DATA.value,
        )
        ctx.history.append({"role": "assistant", "content": ai_msg})
        return response
