"""add audit_log table, 2FA and SSO columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("is_2fa_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("sso_provider", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("sso_id", sa.String(256), nullable=True))

    op.create_index("idx_users_sso", "users", ["sso_provider", "sso_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("action", sa.String(64), nullable=False, index=True),
        sa.Column("resource", sa.String(128), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_index("idx_users_sso", table_name="users")
    op.drop_column("users", "sso_id")
    op.drop_column("users", "sso_provider")
    op.drop_column("users", "is_2fa_enabled")
    op.drop_column("users", "totp_secret")
