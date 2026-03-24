"""add alert policies table

Revision ID: 9f1c3bf8d2de
Revises: f7e51164c8b9
Create Date: 2026-03-23 21:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f1c3bf8d2de'
down_revision = 'f7e51164c8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'alert_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('aws_account_id', sa.Integer(), nullable=True),
        sa.Column('policy_id', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('threshold_type', sa.String(length=10), nullable=True),
        sa.Column('period', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['aws_account_id'], ['aws_accounts.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_policies_aws_account_id'), 'alert_policies', ['aws_account_id'], unique=False)
    op.create_index(op.f('ix_alert_policies_client_id'), 'alert_policies', ['client_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_alert_policies_client_id'), table_name='alert_policies')
    op.drop_index(op.f('ix_alert_policies_aws_account_id'), table_name='alert_policies')
    op.drop_table('alert_policies')

