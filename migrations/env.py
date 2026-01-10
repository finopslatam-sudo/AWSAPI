import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Alembic Config object
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -------------------------------------------------
# DATABASE URL (FUENTE ÚNICA)
# -------------------------------------------------
DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URI")

if not DATABASE_URL:
    raise RuntimeError(
        "❌ SQLALCHEMY_DATABASE_URI no está definida en el entorno"
    )

config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.replace("%", "%%")
)

# -------------------------------------------------
# IMPORTAR MODELOS (MUY IMPORTANTE)
# -------------------------------------------------
# ⚠️ Ajusta el import si tu app se llama distinto
from app import db  # noqa: E402

target_metadata = db.metadata


# -------------------------------------------------
# MIGRATIONS OFFLINE
# -------------------------------------------------
def run_migrations_offline():
    """Run migrations in offline mode."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# -------------------------------------------------
# MIGRATIONS ONLINE
# -------------------------------------------------
def run_migrations_online():
    """Run migrations in online mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# -------------------------------------------------
# ENTRYPOINT
# -------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
