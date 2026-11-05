"""Alembic runs this file for every migration command."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    url = get_settings().database_url
    if not url or url.startswith("replace_with"):
        raise RuntimeError("Set DATABASE_URL in backend/.env before running migrations.")
    return url


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql` prints the SQL instead of running it."""
    context.configure(url=get_database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
