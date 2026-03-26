"""add cost_explorer_cache table

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a1b2
Create Date: 2026-03-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'd5e6f7a8b9c0'
down_revision = 'c3d4e5f6a1b2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cost_explorer_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aws_account_id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(length=30), nullable=False),
        sa.Column('data_json', sa.Text(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['aws_account_id'], ['aws_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aws_account_id', 'cache_key', name='uq_ce_cache_account_key'),
    )
    op.create_index('ix_ce_cache_account', 'cost_explorer_cache', ['aws_account_id'])


def downgrade():
    op.drop_index('ix_ce_cache_account', table_name='cost_explorer_cache')
    op.drop_table('cost_explorer_cache')
