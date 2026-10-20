"""Database lifecycle and request-scoped sessions for the local demo."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db


def upgrade_schema():
    """The local demo runs its versioned migrations before loading synthetic fixtures."""
    from alembic import command
    from alembic.config import Config
    from backend.config import BASE_DIR
    config = Config(str(BASE_DIR / 'alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
