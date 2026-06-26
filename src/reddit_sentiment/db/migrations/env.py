from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from reddit_sentiment.core.config import get_settings
from reddit_sentiment.db import models  # noqa: F401
from reddit_sentiment.db.base import Base

config = context.config
settings = get_settings()
sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
config.set_main_option("sqlalchemy.url", sync_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "connect_timeout": 10,
            "options": "-c lock_timeout=10000 -c statement_timeout=60000",
        },
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
