"""User ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    plan: Mapped[str] = mapped_column(String(20), nullable=False, server_default="free")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=datetime.utcnow, nullable=False
    )

    # relationships
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    pipeline_stages = relationship("PipelineStage", back_populates="user", cascade="all, delete-orphan")
