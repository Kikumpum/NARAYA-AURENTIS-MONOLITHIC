"""Separate patient portal sessions from staff workspace sessions."""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    if 'audience' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('sessions')}:
        op.add_column('sessions', sa.Column('audience', sa.String(16), nullable=False, server_default='workspace'))


def downgrade():
    op.drop_column('sessions', 'audience')
