"""merge_branches

Revision ID: 9ff469be13eb
Revises: c1da99ff64ca, d5e6f7a8b9c0
Create Date: 2026-03-30 16:34:00.503208

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9ff469be13eb'
down_revision = ('c1da99ff64ca', 'd5e6f7a8b9c0')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
