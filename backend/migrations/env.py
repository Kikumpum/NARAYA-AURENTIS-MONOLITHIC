"""Run migrations with the application engine or an explicitly supplied connection."""
from alembic import context
from sqlalchemy import create_engine
from backend.config import DATABASE_URL
from backend.models import Base

config = context.config
target_metadata = Base.metadata


def migrate(connection):
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get('connection') is not None:
    migrate(config.attributes['connection'])
else:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        migrate(connection)
