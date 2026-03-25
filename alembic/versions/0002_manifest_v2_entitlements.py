"""manifest v2 + agent entitlements

Revision ID: 0002
Revises: 0001_initial
Create Date: 2026-03-26

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_manifest_v2_entitlements"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "consents",
        sa.Column("manifest_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "consents",
        sa.Column("resource_spec", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.alter_column("consents", "manifest_version", server_default=None)
    op.alter_column("consents", "resource_spec", server_default=None)

    op.create_table(
        "agent_entitlements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("max_concurrent_jobs", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "agent_id", name="uq_agent_entitlements_user_agent"),
    )
    op.create_index(op.f("ix_agent_entitlements_agent_id"), "agent_entitlements", ["agent_id"], unique=False)
    op.create_index(op.f("ix_agent_entitlements_user_id"), "agent_entitlements", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_entitlements_user_id"), table_name="agent_entitlements")
    op.drop_index(op.f("ix_agent_entitlements_agent_id"), table_name="agent_entitlements")
    op.drop_table("agent_entitlements")

    op.drop_column("consents", "resource_spec")
    op.drop_column("consents", "manifest_version")
