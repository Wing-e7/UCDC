"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-26

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("resources", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("consent_hash", sa.String(length=64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consents_agent_id"), "consents", ["agent_id"], unique=False)
    op.create_index(op.f("ix_consents_consent_hash"), "consents", ["consent_hash"], unique=False)
    op.create_index(op.f("ix_consents_user_id"), "consents", ["user_id"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("consent_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_agent_id"), "jobs", ["agent_id"], unique=False)
    op.create_index(op.f("ix_jobs_consent_id"), "jobs", ["consent_id"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("consent_id", sa.String(length=36), nullable=True),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_consent_id"), "audit_events", ["consent_id"], unique=False)
    op.create_index(op.f("ix_audit_events_event_type"), "audit_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_audit_events_job_id"), "audit_events", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_events_job_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_event_type"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_consent_id"), table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index(op.f("ix_jobs_consent_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_agent_id"), table_name="jobs")
    op.drop_table("jobs")

    op.drop_index(op.f("ix_consents_user_id"), table_name="consents")
    op.drop_index(op.f("ix_consents_consent_hash"), table_name="consents")
    op.drop_index(op.f("ix_consents_agent_id"), table_name="consents")
    op.drop_table("consents")
