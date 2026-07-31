"""unify_clients_to_enterprise_plan

Revision ID: 3ff40ad317b8
Revises: a7c4e91f5b3d
Create Date: 2026-07-30 00:00:00.000000

Ya no existe diferenciación comercial entre planes: todo cliente activo
pasa a FinOps Enterprise. Actualiza las ClientSubscription activas para
apuntar al plan_id de código 'FINOPS_ENTERPRISE'.

downgrade() es intencionalmente un no-op: el plan original de cada
cliente (Foundation/Professional) se pierde y no hay forma de
reconstruirlo desde la BD una vez aplicado el upgrade. Si se necesita
revertir, restaurar desde el pg_dump previo a esta migración.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3ff40ad317b8'
down_revision = 'a7c4e91f5b3d'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    plans_table = sa.table(
        'plans',
        sa.column('id', sa.Integer),
        sa.column('code', sa.String),
    )
    subscriptions_table = sa.table(
        'client_subscriptions',
        sa.column('id', sa.Integer),
        sa.column('plan_id', sa.Integer),
        sa.column('is_active', sa.Boolean),
    )

    enterprise_plan = connection.execute(
        sa.select(plans_table.c.id).where(plans_table.c.code == 'FINOPS_ENTERPRISE')
    ).first()

    if enterprise_plan is None:
        raise RuntimeError(
            "No existe un plan con code='FINOPS_ENTERPRISE' en la tabla plans. "
            "Crear el plan antes de aplicar esta migración."
        )

    enterprise_plan_id = enterprise_plan.id

    connection.execute(
        subscriptions_table.update()
        .where(subscriptions_table.c.is_active.is_(True))
        .where(subscriptions_table.c.plan_id != enterprise_plan_id)
        .values(plan_id=enterprise_plan_id)
    )


def downgrade():
    # No-op intencional — ver docstring del módulo.
    pass
