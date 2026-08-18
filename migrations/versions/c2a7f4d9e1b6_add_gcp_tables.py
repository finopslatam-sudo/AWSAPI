"""add_gcp_tables

Revision ID: c2a7f4d9e1b6
Revises: ab8e6b503e9d
Create Date: 2026-08-18 00:00:00.000000

Crea las tablas de GCP (gcp_accounts, gcp_resource_inventory,
gcp_findings), equivalentes a las de AWS/Azure pero completamente
independientes: no se toca ninguna tabla/columna AWS o Azure existente.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2a7f4d9e1b6'
down_revision = 'ab8e6b503e9d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'gcp_accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('project_id', sa.String(length=100), nullable=False),
        sa.Column('project_name', sa.String(length=150), nullable=False),
        sa.Column('service_account_email', sa.String(length=255), nullable=False),
        sa.Column('service_account_key', sa.String(length=4096), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('audit_status', sa.String(length=20), server_default='idle'),
        sa.Column('audit_started_at', sa.DateTime(), nullable=True),
        sa.Column('audit_finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'gcp_resource_inventory',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('gcp_account_id', sa.Integer(), sa.ForeignKey('gcp_accounts.id'), nullable=False),
        sa.Column('service_name', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=300), nullable=False),
        sa.Column('region', sa.String(length=50), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('resource_metadata', sa.JSON(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('client_id', 'resource_id', name='uq_gcp_client_resource'),
    )
    op.create_index('idx_gcp_inventory_client_id', 'gcp_resource_inventory', ['client_id'])
    op.create_index('idx_gcp_inventory_client_active', 'gcp_resource_inventory', ['client_id', 'is_active'])
    op.create_index('idx_gcp_inventory_type', 'gcp_resource_inventory', ['client_id', 'resource_type'])
    op.create_index(
        'idx_gcp_inventory_client_service', 'gcp_resource_inventory', ['client_id', 'service_name'],
        postgresql_where=sa.text('is_active = true')
    )

    op.create_table(
        'gcp_findings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('gcp_account_id', sa.Integer(), sa.ForeignKey('gcp_accounts.id'), nullable=False),
        sa.Column('resource_id', sa.String(length=300), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('region', sa.String(length=50), nullable=True),
        sa.Column('gcp_service', sa.String(length=50), nullable=False),
        sa.Column('finding_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('estimated_monthly_savings', sa.Numeric(10, 2), default=0),
        sa.Column('resolved', sa.Boolean(), default=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('client_id', 'resource_id', 'finding_type', name='uq_gcp_client_resource_type'),
    )
    op.create_index('idx_gcp_findings_client_resolved', 'gcp_findings', ['client_id', 'resolved'])
    op.create_index('idx_gcp_findings_resource_client', 'gcp_findings', ['resource_id', 'client_id'])
    op.create_index(
        'idx_gcp_findings_resource_client_resolved', 'gcp_findings',
        ['resource_id', 'client_id', 'resolved']
    )


def downgrade():
    op.drop_index('idx_gcp_findings_resource_client_resolved', table_name='gcp_findings')
    op.drop_index('idx_gcp_findings_resource_client', table_name='gcp_findings')
    op.drop_index('idx_gcp_findings_client_resolved', table_name='gcp_findings')
    op.drop_table('gcp_findings')

    op.drop_index(
        'idx_gcp_inventory_client_service', table_name='gcp_resource_inventory',
        postgresql_where=sa.text('is_active = true')
    )
    op.drop_index('idx_gcp_inventory_type', table_name='gcp_resource_inventory')
    op.drop_index('idx_gcp_inventory_client_active', table_name='gcp_resource_inventory')
    op.drop_index('idx_gcp_inventory_client_id', table_name='gcp_resource_inventory')
    op.drop_table('gcp_resource_inventory')

    op.drop_table('gcp_accounts')
