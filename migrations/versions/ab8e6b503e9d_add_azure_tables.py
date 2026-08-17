"""add_azure_tables

Revision ID: ab8e6b503e9d
Revises: 3ff40ad317b8
Create Date: 2026-08-17 00:00:00.000000

Crea las tablas de Azure (azure_accounts, azure_resource_inventory,
azure_findings), equivalentes a las de AWS pero completamente
independientes: no se toca ninguna tabla/columna AWS existente.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ab8e6b503e9d'
down_revision = '3ff40ad317b8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'azure_accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('subscription_id', sa.String(length=36), nullable=False),
        sa.Column('subscription_name', sa.String(length=100), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('app_client_id', sa.String(length=36), nullable=False),
        sa.Column('client_secret', sa.String(length=512), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('audit_status', sa.String(length=20), server_default='idle'),
        sa.Column('audit_started_at', sa.DateTime(), nullable=True),
        sa.Column('audit_finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'azure_resource_inventory',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('azure_account_id', sa.Integer(), sa.ForeignKey('azure_accounts.id'), nullable=False),
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
        sa.UniqueConstraint('client_id', 'resource_id', name='uq_azure_client_resource'),
    )
    op.create_index('idx_azure_inventory_client_id', 'azure_resource_inventory', ['client_id'])
    op.create_index('idx_azure_inventory_client_active', 'azure_resource_inventory', ['client_id', 'is_active'])
    op.create_index('idx_azure_inventory_type', 'azure_resource_inventory', ['client_id', 'resource_type'])
    op.create_index(
        'idx_azure_inventory_client_service', 'azure_resource_inventory', ['client_id', 'service_name'],
        postgresql_where=sa.text('is_active = true')
    )

    op.create_table(
        'azure_findings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('azure_account_id', sa.Integer(), sa.ForeignKey('azure_accounts.id'), nullable=False),
        sa.Column('resource_id', sa.String(length=300), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('region', sa.String(length=50), nullable=True),
        sa.Column('azure_service', sa.String(length=50), nullable=False),
        sa.Column('finding_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('estimated_monthly_savings', sa.Numeric(10, 2), default=0),
        sa.Column('resolved', sa.Boolean(), default=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('client_id', 'resource_id', 'finding_type', name='uq_azure_client_resource_type'),
    )
    op.create_index('idx_azure_findings_client_resolved', 'azure_findings', ['client_id', 'resolved'])
    op.create_index('idx_azure_findings_resource_client', 'azure_findings', ['resource_id', 'client_id'])
    op.create_index(
        'idx_azure_findings_resource_client_resolved', 'azure_findings',
        ['resource_id', 'client_id', 'resolved']
    )


def downgrade():
    op.drop_index('idx_azure_findings_resource_client_resolved', table_name='azure_findings')
    op.drop_index('idx_azure_findings_resource_client', table_name='azure_findings')
    op.drop_index('idx_azure_findings_client_resolved', table_name='azure_findings')
    op.drop_table('azure_findings')

    op.drop_index(
        'idx_azure_inventory_client_service', table_name='azure_resource_inventory',
        postgresql_where=sa.text('is_active = true')
    )
    op.drop_index('idx_azure_inventory_type', table_name='azure_resource_inventory')
    op.drop_index('idx_azure_inventory_client_active', table_name='azure_resource_inventory')
    op.drop_index('idx_azure_inventory_client_id', table_name='azure_resource_inventory')
    op.drop_table('azure_resource_inventory')

    op.drop_table('azure_accounts')
