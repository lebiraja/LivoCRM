"""In-memory analytics cache with async recompute.

Stores pre-computed dashboard stats so the WebSocket endpoint can push
snapshots instantly.  Recomputation runs on a timer or can be triggered
on-demand after entity mutations.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.activity import Activity


class AnalyticsCache:
    """Per-user analytics snapshot."""

    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}
        self._last_computed: dict[str, datetime] = {}
        self._ttl = timedelta(seconds=30)

    # -- public API --------------------------------------------------------

    async def get(self, user_id: str | UUID) -> dict:
        """Return cached stats, recomputing if stale."""
        uid = str(user_id)
        now = datetime.now(timezone.utc)
        last = self._last_computed.get(uid)
        if last is None or (now - last) > self._ttl:
            await self._recompute(uid)
        return self._cache.get(uid, self._empty())

    async def invalidate(self, user_id: str | UUID) -> dict:
        """Force recompute and return fresh stats."""
        uid = str(user_id)
        await self._recompute(uid)
        return self._cache[uid]

    # -- internal ----------------------------------------------------------

    async def _recompute(self, user_id: str) -> None:
        """Run aggregate queries and cache the results."""
        async with async_session_factory() as db:
            stats = await self._query_stats(db, user_id)
        self._cache[user_id] = stats
        self._last_computed[user_id] = datetime.now(timezone.utc)

    @staticmethod
    async def _query_stats(db: AsyncSession, user_id: str) -> dict:
        """Execute the aggregate queries."""
        uid = UUID(user_id)

        # Total contacts
        total_contacts = (
            await db.execute(
                select(func.count()).select_from(Contact).where(Contact.owner_id == uid)
            )
        ).scalar() or 0

        # Total deals + pipeline value
        deals_result = await db.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Deal.value), 0),
            )
            .select_from(Deal)
            .where(Deal.owner_id == uid)
        )
        deals_row = deals_result.one()
        total_deals = deals_row[0] or 0
        pipeline_value = float(deals_row[1] or 0)

        # Won deals
        won_deals = (
            await db.execute(
                select(func.count())
                .select_from(Deal)
                .where(Deal.owner_id == uid, Deal.stage == "won")
            )
        ).scalar() or 0

        # Recent activities (last 7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_activities = (
            await db.execute(
                select(func.count())
                .select_from(Activity)
                .where(Activity.owner_id == uid, Activity.created_at >= week_ago)
            )
        ).scalar() or 0

        return {
            "total_contacts": total_contacts,
            "total_deals": total_deals,
            "pipeline_value": pipeline_value,
            "won_deals": won_deals,
            "win_rate": round(won_deals / total_deals * 100, 1) if total_deals else 0.0,
            "recent_activities": recent_activities,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _empty() -> dict:
        return {
            "total_contacts": 0,
            "total_deals": 0,
            "pipeline_value": 0.0,
            "won_deals": 0,
            "win_rate": 0.0,
            "recent_activities": 0,
            "computed_at": None,
        }


# Singleton
analytics_cache = AnalyticsCache()
