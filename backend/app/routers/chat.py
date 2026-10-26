"""Chat router — AI conversation endpoints."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.chat import ChatAction, ChatMessage, ChatSession
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.user import User
from app.schemas.ai_actions import ACTION_MODELS, ActivityFields, ContactFields, DealFields
from app.schemas.chat import (
    ChatMessageRead,
    ChatMessageSend,
    ChatSendResponse,
    ChatSessionDetail,
    ChatSessionRead,
    ConfirmationPayload,
)
from app.services.ai_engine.orchestrator import Orchestrator, OrchestratorResponse, SessionState
from app.services.session_manager import (
    SessionBusyError,
    _save_context,
    clear_context,
    get_context,
    reset_context,
    session_lock,
)
from app.services.session_naming import generate_session_title
from app.routers.websocket import push_ai_typing, push_dashboard_update, push_entity_created
from app.services.analytics_cache import analytics_cache
from app.services.bedrock_service import llm_slots
from app.services.rate_limit import rate_limit, user_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Singleton orchestrator (stateless — all state lives in SessionContext)
_orchestrator = Orchestrator()

# Strong references so fire-and-forget tasks are not garbage-collected mid-run
_background_tasks: set[asyncio.Task[None]] = set()


# ── Session management ──────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all chat sessions for the current user, newest first."""
    # Sub-query for message count
    msg_count = (
        select(func.count(ChatMessage.id))
        .where(ChatMessage.session_id == ChatSession.id)
        .correlate(ChatSession)
        .scalar_subquery()
    )

    stmt = (
        select(ChatSession, msg_count.label("message_count"))
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        ChatSessionRead(
            id=session.id,
            title=session.title,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=count,
        )
        for session, count in rows
    ]


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new chat session."""
    session = ChatSession(user_id=user.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ChatSessionRead(
        id=session.id,
        title=session.title,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a session with all its messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Load messages
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = msg_result.scalars().all()

    return ChatSessionDetail(
        id=session.id,
        title=session.title,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(messages),
        messages=[ChatMessageRead.model_validate(m) for m in messages],
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a chat session and clear its context."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    await db.delete(session)
    await db.commit()
    await clear_context(session_id)


# ── Send message ────────────────────────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/message",
    response_model=ChatSendResponse,
    dependencies=[Depends(rate_limit("chat", 30, 60, user_key))],
)
async def send_message(
    session_id: UUID,
    body: ChatMessageSend,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a message to the AI and get a response.

    This is the main chat endpoint.  It:
      1. Verifies the session, then releases the DB connection
      2. Runs the orchestrator off the event loop (no connection held)
      3. Saves both messages in one short transaction
      4. If ready_to_save and state is SAVING, creates the CRM entity
      5. Returns both messages + orchestrator state
    """
    # Verify session belongs to user
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    # Return the connection to the pool before the slow LLM round-trips
    await db.commit()

    try:
        # One turn at a time per session: parallel "yes" messages must not both save (SEC-08)
        async with session_lock(session_id):
            # 2. Run orchestrator in a worker thread (with typing indicator via WS)
            await push_ai_typing(session_id, is_typing=True)
            ctx = await get_context(session_id)
            async with llm_slots:
                orch_response: OrchestratorResponse = await asyncio.to_thread(
                    _orchestrator.process_message, ctx, body.message
                )
            await push_ai_typing(session_id, is_typing=False)

            # 3. Save the user and AI messages
            user_msg = ChatMessage(
                session_id=session_id,
                role="user",
                content=body.message,
            )
            db.add(user_msg)
            ai_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=orch_response.ai_message,
                intent=orch_response.intent,
            )
            db.add(ai_msg)

            # 4. If entering SAVING state, validate and create the entity
            outcome: SaveOutcome | None = None
            if orch_response.session_state == SessionState.SAVING and orch_response.ready_to_save:
                outcome = await _save_entity(
                    db=db,
                    user_id=user.id,
                    session_id=session_id,
                    intent=orch_response.intent,
                    data=orch_response.extracted_data,
                )
                if not outcome.entity_id:
                    # Nothing saved: ask the user to fix the rejected fields instead
                    for field_name in outcome.bad_fields:
                        ctx.collected_data.pop(field_name, None)
                    ctx.state = SessionState.COLLECTING
                    ctx.history[-1] = {"role": "assistant", "content": outcome.message}
                    ai_msg.content = outcome.message
                    orch_response.ai_message = outcome.message
                    orch_response.session_state = SessionState.COLLECTING
                    orch_response.ready_to_save = False

            # ── Auto-naming: trigger on first exchange only ────────────────
            # Check BEFORE committing new messages (pre-exchange snapshot)
            is_first_exchange = session.title == "New Chat"

            # Update session timestamp
            session.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(user_msg)
            await db.refresh(ai_msg)

            # Persist context to Redis only once the DB state it describes is committed
            if outcome and outcome.entity_id:
                # Transition to IDLE — preserve history + remember what was saved
                await reset_context(
                    session_id,
                    ctx,
                    last_saved_entity={
                        "type": _intent_to_entity(orch_response.intent),
                        "id": str(outcome.entity_id),
                        "data": orch_response.extracted_data,
                        "intent": orch_response.intent,
                    },
                )
            else:
                await _save_context(session_id, ctx)
    except SessionBusyError:
        raise HTTPException(status_code=409, detail="Still answering your previous message in this chat")

    # 5. Publish only after commit so listeners never see a phantom entity (SEC-15)
    if outcome and outcome.entity_id:
        await push_entity_created(
            user.id, _intent_to_entity(orch_response.intent), outcome.entity_id, orch_response.extracted_data
        )
        stats = await analytics_cache.invalidate(user.id)
        await push_dashboard_update(user.id, stats)

    # Schedule background title generation (non-blocking, after commit)
    if is_first_exchange:
        task = asyncio.create_task(
            _auto_name_session(
                session_id=session_id,
                user_id=user.id,
                user_message=body.message,
                ai_response=orch_response.ai_message,
            )
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    # Build confirmation payload if ready to save
    confirmation = None
    if orch_response.ready_to_save and orch_response.session_state == SessionState.SAVING:
        confirmation = ConfirmationPayload(
            intent=orch_response.intent,
            entity_type=_intent_to_entity(orch_response.intent),
            data=orch_response.extracted_data,
            message=f"Ready to create {_intent_to_entity(orch_response.intent).lower()}. Please confirm:",
        )

    return ChatSendResponse(
        session_id=session_id,
        user_message=ChatMessageRead.model_validate(user_msg),
        ai_message=ChatMessageRead.model_validate(ai_msg),
        session_state=orch_response.session_state.value,
        intent=orch_response.intent,
        extracted_data=orch_response.extracted_data,
        missing_fields=orch_response.missing_fields,
        ready_to_save=orch_response.ready_to_save,
        confirmation=confirmation,
        session_title=session.title,
    )


# ── Manual rename endpoint ──────────────────────────────────────────────────

class _RenameBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


@router.patch("/sessions/{session_id}/title", response_model=ChatSessionRead)
async def rename_session(
    session_id: UUID,
    body: _RenameBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually rename a chat session."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session.title = body.title.strip()[:100]
    session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session)

    # Count messages
    msg_count_result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
    )
    msg_count = msg_count_result.scalar() or 0

    return ChatSessionRead(
        id=session.id,
        title=session.title,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=msg_count,
    )


# ── Background auto-naming ─────────────────────────────────────────────────

async def _auto_name_session(
    *,
    session_id: UUID,
    user_id: UUID,
    user_message: str,
    ai_response: str,
) -> None:
    """Generate and persist a session title in the background.

    Runs as an asyncio task — never blocks the chat response.
    Uses its own DB session so the main request isn't affected.
    """
    from app.database import async_session_factory

    try:
        # Run LLM call in a thread to avoid blocking the event loop
        async with llm_slots:
            title = await asyncio.to_thread(
                generate_session_title, user_message, ai_response
            )

        async with async_session_factory() as db:
            result = await db.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id,
                )
            )
            session = result.scalar_one_or_none()
            if session and session.title == "New Chat":
                session.title = title
                session.updated_at = datetime.utcnow()
                await db.commit()
                logger.info("Auto-named session %s → %r", session_id, title)
    except Exception:
        logger.exception("Background session naming failed for %s", session_id)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _intent_to_entity(intent: str) -> str:
    """Map an intent string to an entity type name."""
    mapping = {
        "ADD_CONTACT": "contact",
        "UPDATE_CONTACT": "contact",
        "ADD_DEAL": "deal",
        "UPDATE_DEAL": "deal",
        "LOG_ACTIVITY": "activity",
    }
    return mapping.get(intent, "unknown")


# ── Entity saving ──────────────────────────────────────────────────────────


@dataclass
class SaveOutcome:
    entity_id: UUID | None
    # When nothing was saved: what to tell the user, and which collected fields to drop
    message: str = ""
    bad_fields: list[str] = field(default_factory=list)


class UnresolvedTarget(Exception):
    """The record the user referred to does not exist or matches more than one row."""


async def _save_entity(
    *,
    db: AsyncSession,
    user_id: UUID,
    session_id: UUID,
    intent: str,
    data: dict,
) -> SaveOutcome:
    """Validate AI-collected data, then write the CRM entity inside a savepoint.

    LLM output is untrusted (SEC-05): it must fit the intent's model in
    app.schemas.ai_actions. A rejected value or an unknown target leaves the
    request transaction usable, records a `failed` ChatAction and returns a
    clarification for the user instead of a 500 (SEC-06).
    """
    entity_type = _intent_to_entity(intent)
    # `_entity_id` is set server-side for follow-up updates; the extractor never passes model ids
    entity_ref = data.get("_entity_id")
    fields = {k: v for k, v in data.items() if v is not None and k != "_entity_id"}

    try:
        action = ACTION_MODELS[intent].model_validate(fields)
        async with db.begin_nested():
            entity_id = await _WRITERS[intent](db, user_id, session_id, action, entity_ref)
        outcome = SaveOutcome(entity_id)
    except ValidationError as exc:
        bad_fields = sorted({str(err["loc"][0]) for err in exc.errors() if err["loc"]})
        outcome = SaveOutcome(
            None,
            f"I couldn't save that {entity_type}: please check {', '.join(bad_fields)}. What should it be?",
            bad_fields,
        )
    except UnresolvedTarget as exc:
        outcome = SaveOutcome(None, str(exc))

    db.add(
        ChatAction(
            session_id=session_id,
            action_type=intent,
            entity_type=entity_type,
            entity_id=outcome.entity_id,
            status="completed" if outcome.entity_id else "failed",
        )
    )
    return outcome


async def _matching(db: AsyncSession, model: type[Contact] | type[Deal], column: Any, user_id: UUID, value: str) -> list:
    """Rows of the user's `model` whose `column` equals `value`, ignoring case (never a LIKE)."""
    result = await db.scalars(
        select(model).where(model.user_id == user_id, func.lower(column) == value.lower()).limit(5)
    )
    return list(result.all())


async def _resolve(
    db: AsyncSession, model: type[Contact] | type[Deal], column: Any, user_id: UUID, value: str, entity_ref: str | None
) -> Any:
    """Find the record an update refers to: the server-side id first, else one exact name match."""
    label = model.__tablename__[:-1]
    if entity_ref:
        row = (await db.scalars(select(model).where(model.id == UUID(entity_ref), model.user_id == user_id))).first()
        if row:
            return row
    rows = await _matching(db, model, column, user_id, value)
    if not rows:
        raise UnresolvedTarget(f'I couldn\'t find a {label} called "{value}". Check the name, or ask me to add it.')
    if len(rows) > 1:
        raise UnresolvedTarget(
            f'I found {len(rows)} {label}s called "{value}". Tell me which one, or update it from the {label} page.'
        )
    return rows[0]


async def _single_id(db: AsyncSession, model: type[Contact] | type[Deal], column: Any, user_id: UUID, value: str) -> UUID | None:
    """Id of the one exact match for an optional link (deal -> contact), else no link."""
    rows = await _matching(db, model, column, user_id, value) if value else []
    return rows[0].id if len(rows) == 1 else None


def _changes(action: ContactFields | DealFields, skip: str) -> dict[str, Any]:
    """Fields the user actually supplied, minus the lookup key and empty values."""
    return {
        k: v for k, v in action.model_dump(exclude_unset=True).items()
        if k not in (skip, "contact_name") and v not in ("", [], None)
    }


async def _add_contact(db: AsyncSession, user_id: UUID, session_id: UUID, action: ContactFields, _: str | None) -> UUID:
    contact = Contact(user_id=user_id, source="ai_chat", ai_session_id=session_id, **action.model_dump())
    db.add(contact)
    await db.flush()
    return contact.id


async def _update_contact(
    db: AsyncSession, user_id: UUID, session_id: UUID, action: ContactFields, entity_ref: str | None
) -> UUID:
    contact = await _resolve(db, Contact, Contact.name, user_id, action.name, entity_ref)
    for field_name, value in _changes(action, skip="" if entity_ref else "name").items():
        setattr(contact, field_name, value)
    await db.flush()
    return contact.id


async def _add_deal(db: AsyncSession, user_id: UUID, session_id: UUID, action: DealFields, _: str | None) -> UUID:
    deal = Deal(
        user_id=user_id,
        title=action.title,
        value=action.value or 0,
        stage=action.stage or "lead",
        expected_close=action.expected_close,
        notes=action.notes,
        contact_id=await _single_id(db, Contact, Contact.name, user_id, action.contact_name),
        source="ai_chat",
        ai_session_id=session_id,
    )
    db.add(deal)
    await db.flush()
    return deal.id


async def _update_deal(
    db: AsyncSession, user_id: UUID, session_id: UUID, action: DealFields, entity_ref: str | None
) -> UUID:
    deal = await _resolve(db, Deal, Deal.title, user_id, action.title, entity_ref)
    for field_name, value in _changes(action, skip="" if entity_ref else "title").items():
        setattr(deal, field_name, value)
    if action.contact_name:
        deal.contact_id = await _single_id(db, Contact, Contact.name, user_id, action.contact_name) or deal.contact_id
    await db.flush()
    return deal.id


async def _log_activity(db: AsyncSession, user_id: UUID, session_id: UUID, action: ActivityFields, _: str | None) -> UUID:
    activity = Activity(
        user_id=user_id,
        type=action.activity_type,
        description=action.description,
        occurred_at=datetime.now(timezone.utc),
        contact_id=await _single_id(db, Contact, Contact.name, user_id, action.contact_name),
        deal_id=await _single_id(db, Deal, Deal.title, user_id, action.deal_title),
    )
    db.add(activity)
    await db.flush()
    return activity.id


_WRITERS: dict[str, Callable[..., Awaitable[UUID]]] = {
    "ADD_CONTACT": _add_contact,
    "UPDATE_CONTACT": _update_contact,
    "ADD_DEAL": _add_deal,
    "UPDATE_DEAL": _update_deal,
    "LOG_ACTIVITY": _log_activity,
}
