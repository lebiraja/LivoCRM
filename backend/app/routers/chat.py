"""Chat router — AI conversation endpoints."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.chat import ChatAction, ChatMessage, ChatSession
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.user import User
from app.schemas.chat import (
    ChatMessageRead,
    ChatMessageSend,
    ChatSendResponse,
    ChatSessionDetail,
    ChatSessionRead,
    ConfirmationPayload,
)
from app.services.ai_engine.orchestrator import Orchestrator, OrchestratorResponse, SessionState
from app.services.session_manager import clear_context, get_context, reset_context, _save_context
from app.services.session_naming import generate_session_title
from app.routers.websocket import push_ai_typing, push_dashboard_update, push_entity_created
from app.services.analytics_cache import analytics_cache
from app.services.bedrock_service import llm_slots

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

@router.post("/sessions/{session_id}/message", response_model=ChatSendResponse)
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

    # 2. Run orchestrator in a worker thread (with typing indicator via WS)
    await push_ai_typing(session_id, is_typing=True)
    ctx = await get_context(session_id)
    async with llm_slots:
        orch_response: OrchestratorResponse = await asyncio.to_thread(
            _orchestrator.process_message, ctx, body.message
        )
    await push_ai_typing(session_id, is_typing=False)

    # Persist context to Redis so it survives restarts
    await _save_context(session_id, ctx)

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

    # 4. If entering SAVING state, create the entity + push WS events
    saved_entity_id = None
    if orch_response.session_state == SessionState.SAVING and orch_response.ready_to_save:
        saved_entity_id = await _save_entity(
            db=db,
            user_id=user.id,
            session_id=session_id,
            intent=orch_response.intent,
            data=orch_response.extracted_data,
        )
        if saved_entity_id:
            entity_type = _intent_to_entity(orch_response.intent)
            await push_entity_created(
                user.id, entity_type, saved_entity_id, orch_response.extracted_data
            )
            stats = await analytics_cache.invalidate(user.id)
            await push_dashboard_update(user.id, stats)
        # Transition to IDLE — preserve history + remember what was saved
        await reset_context(
            session_id,
            last_saved_entity={
                "type": _intent_to_entity(orch_response.intent),
                "id": str(saved_entity_id) if saved_entity_id else None,
                "data": orch_response.extracted_data,
                "intent": orch_response.intent,
            },
        )

    # ── Auto-naming: trigger on first exchange only ────────────────────────
    # Check BEFORE committing new messages (pre-exchange snapshot)
    is_first_exchange = session.title == "New Chat"

    # Update session timestamp
    session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(ai_msg)

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

async def _save_entity(
    *,
    db: AsyncSession,
    user_id: UUID,
    session_id: UUID,
    intent: str,
    data: dict,
) -> UUID | None:
    """Create a CRM entity from collected conversation data.

    Returns the new entity's UUID, or None on failure.
    """
    entity_type = "unknown"
    entity_id = None

    try:
        if intent == "ADD_CONTACT":
            entity_type = "contact"
            contact = Contact(
                user_id=user_id,
                name=data.get("name", ""),
                email=data.get("email", ""),
                phone=data.get("phone", ""),
                company=data.get("company", ""),
                notes=data.get("notes", ""),
            )
            db.add(contact)
            await db.flush()
            entity_id = contact.id

        elif intent == "UPDATE_CONTACT":
            entity_type = "contact"
            # Look up existing contact by _entity_id or by name
            existing = None
            eid = data.get("_entity_id")
            if eid:
                result = await db.execute(
                    select(Contact).where(Contact.id == UUID(eid), Contact.user_id == user_id)
                )
                existing = result.scalar_one_or_none()
            if not existing and data.get("name"):
                result = await db.execute(
                    select(Contact).where(
                        Contact.user_id == user_id,
                        Contact.name.ilike(f"%{data['name']}%"),
                    ).limit(1)
                )
                existing = result.scalar_one_or_none()

            if existing:
                # Update only non-empty fields
                for field_name in ("name", "email", "phone", "company", "notes"):
                    val = data.get(field_name)
                    if val:
                        setattr(existing, field_name, val)
                entity_id = existing.id
            else:
                # No existing contact found — create new
                contact = Contact(
                    user_id=user_id,
                    name=data.get("name", ""),
                    email=data.get("email", ""),
                    phone=data.get("phone", ""),
                    company=data.get("company", ""),
                    notes=data.get("notes", ""),
                )
                db.add(contact)
                await db.flush()
                entity_id = contact.id

        elif intent == "ADD_DEAL":
            entity_type = "deal"
            deal = Deal(
                user_id=user_id,
                title=data.get("title", "Untitled Deal"),
                value=float(data.get("value", 0)),
                stage=data.get("stage", "lead"),
                notes=data.get("notes", ""),
            )
            # Try to link to a contact by name
            contact_name = data.get("contact_name")
            if contact_name:
                result = await db.execute(
                    select(Contact).where(
                        Contact.user_id == user_id,
                        Contact.name.ilike(f"%{contact_name}%"),
                    ).limit(1)
                )
                contact = result.scalar_one_or_none()
                if contact:
                    deal.contact_id = contact.id

            db.add(deal)
            await db.flush()
            entity_id = deal.id

        elif intent == "UPDATE_DEAL":
            entity_type = "deal"
            existing = None
            eid = data.get("_entity_id")
            if eid:
                result = await db.execute(
                    select(Deal).where(Deal.id == UUID(eid), Deal.user_id == user_id)
                )
                existing = result.scalar_one_or_none()
            if not existing and data.get("title"):
                result = await db.execute(
                    select(Deal).where(
                        Deal.user_id == user_id,
                        Deal.title.ilike(f"%{data['title']}%"),
                    ).limit(1)
                )
                existing = result.scalar_one_or_none()

            if existing:
                for field_name in ("title", "stage", "notes"):
                    val = data.get(field_name)
                    if val:
                        setattr(existing, field_name, val)
                val = data.get("value")
                if val is not None:
                    existing.value = float(val)
                entity_id = existing.id
            else:
                deal = Deal(
                    user_id=user_id,
                    title=data.get("title", "Untitled Deal"),
                    value=float(data.get("value", 0)),
                    stage=data.get("stage", "lead"),
                    notes=data.get("notes", ""),
                )
                db.add(deal)
                await db.flush()
                entity_id = deal.id

        elif intent == "LOG_ACTIVITY":
            entity_type = "activity"
            activity = Activity(
                user_id=user_id,
                type=data.get("type", "note"),
                description=data.get("description", ""),
                occurred_at=datetime.utcnow(),
            )
            # Try to link to a contact
            contact_name = data.get("contact_name")
            if contact_name:
                result = await db.execute(
                    select(Contact).where(
                        Contact.user_id == user_id,
                        Contact.name.ilike(f"%{contact_name}%"),
                    ).limit(1)
                )
                contact = result.scalar_one_or_none()
                if contact:
                    activity.contact_id = contact.id

            db.add(activity)
            await db.flush()
            entity_id = activity.id

        # Record the action
        action = ChatAction(
            session_id=session_id,
            action_type=intent,
            entity_type=entity_type,
            entity_id=entity_id,
            status="completed" if entity_id else "failed",
        )
        db.add(action)

    except Exception:
        logger.exception("Failed to save entity from chat")
        action = ChatAction(
            session_id=session_id,
            action_type=intent,
            entity_type=entity_type,
            status="failed",
        )
        db.add(action)

    return entity_id
