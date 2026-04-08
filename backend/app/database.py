"""SQLAlchemy async engine, session factory, and declarative Base."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Alias used by analytics_cache for standalone session creation
async_session_factory = async_session


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass
