"""Patient self-service bookings and scoped inbox read state."""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('patient_visit_details',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('appointment_id', sa.Integer(), sa.ForeignKey('appointments.id'), nullable=False, unique=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('purpose', sa.String(24), nullable=False),
        sa.Column('interest', sa.String(24), nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('lab_orders.id'), nullable=True))
    op.create_table('patient_updates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('kind', sa.String(32), nullable=False),
        sa.Column('title', sa.String(120), nullable=False),
        sa.Column('message', sa.String(400), nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('lab_orders.id'), nullable=True),
        sa.Column('appointment_id', sa.Integer(), sa.ForeignKey('appointments.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('patient_notice_reads',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('source', sa.String(16), nullable=False),
        sa.Column('notice_id', sa.Integer(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('owner_id', 'source', 'notice_id', name='uq_patient_notice_read'),
        sa.CheckConstraint("source IN ('service','visit')", name='ck_patient_notice_source'))


def downgrade():
    op.drop_table('patient_notice_reads')
    op.drop_table('patient_updates')
    op.drop_table('patient_visit_details')
