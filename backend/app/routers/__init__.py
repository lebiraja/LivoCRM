"""Router barrel — makes it easy for main.py to import."""

from app.routers.auth import router as auth_router
from app.routers.contacts import router as contacts_router
from app.routers.deals import router as deals_router
from app.routers.activities import router as activities_router
from app.routers.analytics import router as analytics_router
from app.routers.ai import router as ai_router
from app.routers.chat import router as chat_router
from app.routers.websocket import router as ws_router

__all__ = [
    "auth_router",
    "contacts_router",
    "deals_router",
    "activities_router",
    "analytics_router",
    "ai_router",
    "chat_router",
    "ws_router",
]
