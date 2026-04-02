"""Re-export all models so Alembic & the app can import them in one shot."""

from app.models.user import User
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.pipeline import PipelineStage

__all__ = ["User", "Contact", "Deal", "Activity", "PipelineStage"]
