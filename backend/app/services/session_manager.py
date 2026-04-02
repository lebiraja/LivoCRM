"""In-memory session context manager for the AI orchestrator.

Stores SessionContext objects keyed by chat session UUID.
In production, swap for Redis-backed storage. The interface stays the same.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.services.ai_engine.orchestrator import SessionContext

logger = logging.getLogger(__name__)

# Simple in-memory store; works for single-instance deployments.
# For multi-instance, replace with Redis-backed dict.
_context_store: dict[UUID, SessionContext] = {}


def get_context(session_id: UUID) -> SessionContext:
    """Get or create a SessionContext for a chat session."""
    if session_id not in _context_store:
        _context_store[session_id] = SessionContext()
    return _context_store[session_id]


def clear_context(session_id: UUID) -> None:
    """Remove a session context (e.g., when session is closed)."""
    _context_store.pop(session_id, None)


def reset_context(session_id: UUID) -> SessionContext:
    """Reset a session context to IDLE (start fresh)."""
    ctx = SessionContext()
    _context_store[session_id] = ctx
    return ctx
