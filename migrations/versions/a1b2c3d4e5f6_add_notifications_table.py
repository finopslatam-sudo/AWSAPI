"""add notifications table

Revision ID: a1b2c3d4e5f6
Revises: 9f1c3bf8d2de
Create Date: 2026-03-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9f1c3bf8d2de'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'notifications',
        sa.Column('id',         sa.Integer(),     nullable=False),
        sa.Column('user_id',    sa.Integer(),     nullable=False),
        sa.Column('type',       sa.String(64),    nullable=False),
        sa.Column('title',      sa.String(255),   nullable=False),
        sa.Column('message',    sa.Text(),        nullable=False),
        sa.Column('is_read',    sa.Boolean(),     nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(),    nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])


def downgrade():
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
