"""Alembic environment: the ledger's metadata and the URL from the config or the command line."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from review_assistant.ledger.db import Base

config = context.config
target_metadata = Base.metadata

# The URL comes from, in order: `-x url=...` on the command line, REVIEW_LEDGER_URL, then alembic.ini.
_override = context.get_x_argument(as_dictionary=True).get("url") or os.environ.get("REVIEW_LEDGER_URL")
if _override:
    config.set_main_option("sqlalchemy.url", _override)


def run_migrations_offline() -> None:
    """Emit SQL without a connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run the migrations against the configured database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
