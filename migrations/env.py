import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# --------------------------------------------------
# Path del proyecto (IMPORTANTE)
# --------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

# --------------------------------------------------
# Config Alembic
# --------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --------------------------------------------------
# Cargar DB (NO app.py)
# --------------------------------------------------
from src.models.database import db  # ✅ CORRECTO
from src.models.client import Client
from src.models.plan import Plan
from src.models.subscription import ClientSubscription

target_metadata = db.metadata

# --------------------------------------------------
# Obtener URL DB desde ENV
# --------------------------------------------------
def get_database_url():
    url = os.getenv("SQLALCHEMY_DATABASE_URI")
    if not url:
        raise RuntimeError("❌ SQLALCHEMY_DATABASE_URI no definida")
    return url


def run_migrations_offline():
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        {
            "sqlalchemy.url": get_database_url()
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
