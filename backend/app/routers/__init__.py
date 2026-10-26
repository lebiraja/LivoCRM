"""Router barrel — makes it easy for main.py to import."""

from app.routers.auth import router as auth_router
from app.routers.contacts import router as contacts_router
from app.routers.deals import router as deals_router
from app.routers.activities import router as activities_router
from app.routers.analytics import router as analytics_router
from app.routers.ai import router as ai_router
from app.routers.chat import router as chat_router
from app.routers.pipeline_stages import router as pipeline_stages_router
from app.routers.websocket import router as ws_router, ticket_router as ws_ticket_router
from app.routers.appointments import router as appointments_router
from app.routers.follow_ups import router as follow_ups_router
from app.routers.recovery import router as recovery_router
from app.routers.demo import router as demo_router

__all__ = [
    "auth_router",
    "contacts_router",
    "deals_router",
    "activities_router",
    "analytics_router",
    "ai_router",
    "chat_router",
    "pipeline_stages_router",
    "ws_router",
    "ws_ticket_router",
    "appointments_router",
    "follow_ups_router",
    "recovery_router",
    "demo_router",
]
