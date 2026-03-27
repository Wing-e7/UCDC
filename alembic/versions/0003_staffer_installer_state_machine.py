"""staffer installer onboarding state machine

Revision ID: 0003
Revises: 0002_manifest_v2_entitlements
Create Date: 2026-03-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_staffer_installer_sm"
down_revision: Union[str, None] = "0002_manifest_v2_entitlements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_events",
        sa.Column("staffer_installer_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_audit_events_staffer_installer_id"),
        "audit_events",
        ["staffer_installer_id"],
        unique=False,
    )

    op.create_table(
        "staffer_installers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("launch_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_staffer_installers_state"), "staffer_installers", ["state"], unique=False)

    op.create_table(
        "staffer_approvals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("staffer_installer_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "staffer_installer_id",
            "idempotency_key",
            name="uq_staffer_approval_idempotency",
        ),
    )
    op.create_index(
        op.f("ix_staffer_approvals_staffer_installer_id"),
        "staffer_approvals",
        ["staffer_installer_id"],
        unique=False,
    )

    op.create_table(
        "staffer_launch_validations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("staffer_installer_id", sa.String(length=36), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staffer_installer_id"),
    )
    op.create_index(
        op.f("ix_staffer_launch_validations_staffer_installer_id"),
        "staffer_launch_validations",
        ["staffer_installer_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_staffer_launch_validations_staffer_installer_id"),
        table_name="staffer_launch_validations",
    )
    op.drop_table("staffer_launch_validations")

    op.drop_index(op.f("ix_staffer_approvals_staffer_installer_id"), table_name="staffer_approvals")
    op.drop_table("staffer_approvals")

    op.drop_index(op.f("ix_staffer_installers_state"), table_name="staffer_installers")
    op.drop_table("staffer_installers")

    op.drop_index(op.f("ix_audit_events_staffer_installer_id"), table_name="audit_events")
    op.drop_column("audit_events", "staffer_installer_id")
