"""Database lifecycle and request-scoped sessions for the local demo."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from backend.config import DATABASE_URL

options = ({'connect_args': {'check_same_thread': False}} if DATABASE_URL.startswith('sqlite') else
           {'poolclass': NullPool, 'connect_args': {'connect_timeout': 15}})
engine = create_engine(DATABASE_URL, **options, pool_pre_ping=True, hide_parameters=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db


def upgrade_schema(connection=None):
    """The local demo runs its versioned migrations before loading synthetic fixtures."""
    from alembic import command
    from alembic.config import Config
    from backend.config import BASE_DIR
    config = Config(str(BASE_DIR / 'alembic.ini'))
    config.set_main_option('script_location', str(BASE_DIR / 'backend' / 'migrations'))
    if connection is not None:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
    else:
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, 'head')


def bootstrap_demo(seed, seed_structure):
    """Serialize shared database initialization across Vercel instances.

    The transaction-scoped advisory lock also works through Neon's transaction
    pooler. Migrations and synthetic fixtures commit together; retries preserve
    existing sessions, workflow data and audit history.
    """
    if engine.dialect.name != 'postgresql':
        upgrade_schema()
        with SessionLocal() as db:
            seed(db)
            seed_structure(db)
        return
    with engine.begin() as connection:
        connection.execute(text('SELECT pg_advisory_xact_lock(734061992014)'))
        upgrade_schema(connection)
        with Session(bind=connection, expire_on_commit=False) as db:
            fresh = seed(db)
            if fresh:
                # Synthetic fixtures specify some IDs. Advance their sequences
                # before regular inserts, otherwise PostgreSQL would reuse ID 1.
                for table in ('organizations', 'users', 'patients', 'lab_orders', 'appointments'):
                    quoted = engine.dialect.identifier_preparer.quote(table)
                    connection.execute(text(
                        "SELECT setval(pg_get_serial_sequence(:table, 'id'), "
                        f'COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {quoted}'
                    ), {'table': table})
            seed_structure(db)
