"""
Alembic migration environment.

Run migrations:
    alembic upgrade head          # apply all pending migrations
    alembic downgrade -1          # roll back one migration
    alembic revision --autogenerate -m "description"  # generate new migration

The database URL is read from FORGE_DB_URL environment variable,
or falls back to the default local development URL.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make forge_bridge importable from the migration environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from forge_bridge.store.models import Base
from forge_bridge.store.session import get_sync_db_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with our env-aware helper
config.set_main_option("sqlalchemy.url", get_sync_db_url())

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generate SQL without connecting."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
