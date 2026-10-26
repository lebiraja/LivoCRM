"""Re-export all models so Alembic & the app can import them in one shot."""

from app.models.user import User
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.pipeline import PipelineStage
from app.models.chat import ChatSession, ChatMessage, ChatAction
from app.models.appointment import Appointment
from app.models.follow_up import FollowUpTask
from app.models.outbound_message import OutboundMessage

__all__ = [
    "User", "Contact", "Deal", "Activity", "PipelineStage",
    "ChatSession", "ChatMessage", "ChatAction",
    "Appointment", "FollowUpTask", "OutboundMessage",
]
