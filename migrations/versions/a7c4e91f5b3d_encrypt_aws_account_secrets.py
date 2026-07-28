"""encrypt_aws_account_secrets

Revision ID: a7c4e91f5b3d
Revises: 93bd8e505868
Create Date: 2026-07-28 00:00:00.000000

Cifra en reposo (Fernet) role_arn/external_id de aws_accounts y ensancha
las columnas por el overhead del ciphertext. Idempotente: si un valor ya
parece un token Fernet (empieza con 'gAAAAA', el byte de versión 0x80 en
base64), se salta. Requiere backup previo (pg_dump) antes de aplicar en
producción — ver runbook del proyecto.
"""
from alembic import op
import sqlalchemy as sa

from src.services.crypto_utils import get_fernet

# revision identifiers, used by Alembic.
revision = 'a7c4e91f5b3d'
down_revision = '93bd8e505868'
branch_labels = None
depends_on = None


def _looks_encrypted(value: str) -> bool:
    return bool(value) and value.startswith("gAAAAA")


def upgrade():
    op.alter_column(
        'aws_accounts', 'role_arn',
        existing_type=sa.String(length=255),
        type_=sa.String(length=512),
        existing_nullable=False,
    )
    op.alter_column(
        'aws_accounts', 'external_id',
        existing_type=sa.String(length=64),
        type_=sa.String(length=255),
        existing_nullable=False,
    )

    connection = op.get_bind()
    fernet = get_fernet(primary_env="AWS_SECRET_ENCRYPTION_KEY")

    accounts_table = sa.table(
        'aws_accounts',
        sa.column('id', sa.Integer),
        sa.column('role_arn', sa.String),
        sa.column('external_id', sa.String),
    )

    rows = connection.execute(
        sa.select(accounts_table.c.id, accounts_table.c.role_arn, accounts_table.c.external_id)
    ).fetchall()

    for row in rows:
        if _looks_encrypted(row.role_arn) and _looks_encrypted(row.external_id):
            continue

        new_role_arn = row.role_arn if _looks_encrypted(row.role_arn) else fernet.encrypt(
            row.role_arn.encode("utf-8")
        ).decode("utf-8")
        new_external_id = row.external_id if _looks_encrypted(row.external_id) else fernet.encrypt(
            row.external_id.encode("utf-8")
        ).decode("utf-8")

        connection.execute(
            accounts_table.update()
            .where(accounts_table.c.id == row.id)
            .values(role_arn=new_role_arn, external_id=new_external_id)
        )


def downgrade():
    connection = op.get_bind()
    fernet = get_fernet(primary_env="AWS_SECRET_ENCRYPTION_KEY")

    accounts_table = sa.table(
        'aws_accounts',
        sa.column('id', sa.Integer),
        sa.column('role_arn', sa.String),
        sa.column('external_id', sa.String),
    )

    rows = connection.execute(
        sa.select(accounts_table.c.id, accounts_table.c.role_arn, accounts_table.c.external_id)
    ).fetchall()

    for row in rows:
        if not _looks_encrypted(row.role_arn) and not _looks_encrypted(row.external_id):
            continue

        plain_role_arn = fernet.decrypt(row.role_arn.encode("utf-8")).decode("utf-8") \
            if _looks_encrypted(row.role_arn) else row.role_arn
        plain_external_id = fernet.decrypt(row.external_id.encode("utf-8")).decode("utf-8") \
            if _looks_encrypted(row.external_id) else row.external_id

        connection.execute(
            accounts_table.update()
            .where(accounts_table.c.id == row.id)
            .values(role_arn=plain_role_arn, external_id=plain_external_id)
        )

    op.alter_column(
        'aws_accounts', 'external_id',
        existing_type=sa.String(length=255),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
    op.alter_column(
        'aws_accounts', 'role_arn',
        existing_type=sa.String(length=512),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
