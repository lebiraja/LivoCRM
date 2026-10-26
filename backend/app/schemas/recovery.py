"""Recovery engine Pydantic schemas."""

from decimal import Decimal

from pydantic import BaseModel


class RecoveryRunResponse(BaseModel):
    created: int


class RecoverySummary(BaseModel):
    appointments: int
    no_shows: int
    no_show_rate: float
    pending_tasks: int
    messages_sent: int
    recovered_inr: Decimal
    recovered_count: int


class DemoSeedResponse(BaseModel):
    contacts: int
    appointments: int
