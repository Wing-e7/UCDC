from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    resources: Mapped[Any] = mapped_column(JSON, nullable=False)
    manifest_version: Mapped[int] = mapped_column(default=1, nullable=False)
    resource_spec: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentEntitlement(Base):
    __tablename__ = "agent_entitlements"
    __table_args__ = (UniqueConstraint("user_id", "agent_id", name="uq_agent_entitlements_user_agent"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    max_concurrent_jobs: Mapped[int] = mapped_column(nullable=False, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    consent_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, default="scheduled")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    consent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    details: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

