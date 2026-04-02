"""Chat router — AI conversation endpoints."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.chat import ChatAction, ChatMessage, ChatSession
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.user import User
from app.schemas.chat import (
    ChatActionRead,
    ChatMessageRead,
    ChatMessageSend,
    ChatSendResponse,
    ChatSessionDetail,
    ChatSessionRead,
)
from app.services.ai_engine.orchestrator import Orchestrator, OrchestratorResponse, SessionState
from app.services.session_manager import clear_context, get_context, reset_context
from app.routers.websocket import push_ai_typing, push_dashboard_update, push_entity_created
from app.services.analytics_cache import analytics_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Singleton orchestrator (stateless — all state lives in SessionContext)
_orchestrator = Orchestrator()


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
    clear_context(session_id)


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
      1. Saves the user message to the DB
      2. Runs the orchestrator to get an AI response
      3. Saves the AI message to the DB
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

    # 1. Save the user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)

    # 2. Run orchestrator (with typing indicator via WS)
    await push_ai_typing(session_id, is_typing=True)
    ctx = get_context(session_id)
    orch_response: OrchestratorResponse = _orchestrator.process_message(ctx, body.message)
    await push_ai_typing(session_id, is_typing=False)

    # 3. Save the AI message
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
        # Reset context for next interaction
        reset_context(session_id)

    # Update session title from first meaningful intent
    if session.title == "New Chat" and orch_response.intent:
        entity = (
            orch_response.intent
            .replace("ADD_", "New ")
            .replace("LOG_", "Log ")
            .replace("UPDATE_", "Update ")
            .replace("_", " ")
            .title()
        )
        name = orch_response.extracted_data.get("name", "")
        session.title = f"{entity}: {name}" if name else entity

    # Update session timestamp
    session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(ai_msg)

    return ChatSendResponse(
        session_id=session_id,
        user_message=ChatMessageRead.model_validate(user_msg),
        ai_message=ChatMessageRead.model_validate(ai_msg),
        session_state=orch_response.session_state.value,
        intent=orch_response.intent,
        extracted_data=orch_response.extracted_data,
        missing_fields=orch_response.missing_fields,
        ready_to_save=orch_response.ready_to_save,
    )


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
        if intent in ("ADD_CONTACT", "UPDATE_CONTACT"):
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

        elif intent in ("ADD_DEAL", "UPDATE_DEAL"):
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
