"""Private visit forecasts and a disabled WhatsApp integration outbox."""
from alembic import op
import sqlalchemy as sa

revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('visit_timings',
        sa.Column('appointment_id',sa.Integer(),sa.ForeignKey('appointments.id'),primary_key=True),
        sa.Column('org_id',sa.Integer(),sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('state',sa.String(24),nullable=False),
        sa.Column('started_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('finished_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('expected_finish_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('revision',sa.Integer(),nullable=False),
        sa.CheckConstraint("state IN ('not_started','in_service','finished','not_attended')",name='ck_visit_timing_state'))
    op.create_table('whatsapp_outbox',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('update_id',sa.Integer(),sa.ForeignKey('patient_updates.id'),nullable=False,unique=True),
        sa.Column('patient_id',sa.Integer(),sa.ForeignKey('patients.id'),nullable=False),
        sa.Column('appointment_id',sa.Integer(),sa.ForeignKey('appointments.id'),nullable=False),
        sa.Column('org_id',sa.Integer(),sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('template_key',sa.String(60),nullable=False),
        sa.Column('payload',sa.Text(),nullable=False),
        sa.Column('status',sa.String(32),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("status = 'awaiting_configuration'",name='ck_whatsapp_not_enabled'))

def downgrade():
    op.drop_table('whatsapp_outbox')
    op.drop_table('visit_timings')
