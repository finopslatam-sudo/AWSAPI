"""add mfa support

Revision ID: e4f9a1b7c2d3
Revises: 8439560cdab6
Create Date: 2026-04-09 15:25:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e4f9a1b7c2d3"
down_revision = "8439560cdab6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "clients",
        sa.Column("mfa_policy", sa.String(length=30), nullable=False, server_default="disabled"),
    )
    op.add_column(
        "clients",
        sa.Column("mfa_updated_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("mfa_pending_secret_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("mfa_confirmed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("mfa_recovery_codes_hash", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("mfa_last_used_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("mfa_failed_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("mfa_locked_until", sa.DateTime(), nullable=True),
    )

    op.alter_column("clients", "mfa_policy", server_default=None)
    op.alter_column("users", "mfa_enabled", server_default=None)
    op.alter_column("users", "mfa_failed_attempts", server_default=None)


def downgrade():
    op.drop_column("users", "mfa_locked_until")
    op.drop_column("users", "mfa_failed_attempts")
    op.drop_column("users", "mfa_last_used_at")
    op.drop_column("users", "mfa_recovery_codes_hash")
    op.drop_column("users", "mfa_confirmed_at")
    op.drop_column("users", "mfa_pending_secret_encrypted")
    op.drop_column("users", "mfa_secret_encrypted")
    op.drop_column("users", "mfa_enabled")

    op.drop_column("clients", "mfa_updated_at")
    op.drop_column("clients", "mfa_policy")
