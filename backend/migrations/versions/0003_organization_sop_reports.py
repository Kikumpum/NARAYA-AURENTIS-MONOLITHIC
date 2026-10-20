"""Organization, versioned SOP reports and private evidence (local demo)."""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    # Frozen schema; checkfirst also supports test fixtures that already created current metadata.
    metadata = sa.MetaData()
    for name in ('organizations','users','lab_orders'):
        sa.Table(name, metadata, sa.Column('id',sa.Integer,primary_key=True))
    sa.Table('organization_positions', metadata,
        sa.Column('id',sa.Integer,primary_key=True), sa.Column('org_id',sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('code',sa.String(60),nullable=False),sa.Column('name',sa.String(120),nullable=False),
        sa.Column('parent_code',sa.String(60)),sa.Column('division',sa.String(100),nullable=False),
        sa.Column('allowed_roles',sa.Text,nullable=False),sa.UniqueConstraint('org_id','code',name='uq_org_position'))
    sa.Table('user_positions',metadata,
        sa.Column('id',sa.Integer,primary_key=True),sa.Column('user_id',sa.ForeignKey('users.id'),nullable=False,unique=True),
        sa.Column('position_id',sa.ForeignKey('organization_positions.id'),nullable=False),
        sa.Column('org_id',sa.ForeignKey('organizations.id'),nullable=False),sa.Column('revision',sa.Integer,nullable=False))
    sa.Table('sop_reports',metadata,
        sa.Column('id',sa.Integer,primary_key=True),sa.Column('author_id',sa.ForeignKey('users.id'),nullable=False),
        sa.Column('org_id',sa.ForeignKey('organizations.id'),nullable=False,index=True),
        sa.Column('position_name',sa.String(120),nullable=False),sa.Column('division',sa.String(100),nullable=False),
        sa.Column('sop_code',sa.String(30),nullable=False),sa.Column('sop_snapshot',sa.Text,nullable=False),
        sa.Column('order_id',sa.ForeignKey('lab_orders.id')),sa.Column('order_state',sa.String(32)),
        sa.Column('report_day',sa.Date,nullable=False),sa.Column('summary',sa.Text,nullable=False),
        sa.Column('results',sa.Text,nullable=False),sa.Column('status',sa.String(20),nullable=False),
        sa.Column('revision',sa.Integer,nullable=False),sa.Column('review_note',sa.Text,nullable=False),
        sa.Column('reviewed_by',sa.ForeignKey('users.id')),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("status IN ('draft','submitted','reviewed','returned')",name='ck_sop_report_status'))
    sa.Table('sop_report_versions',metadata,
        sa.Column('id',sa.Integer,primary_key=True),sa.Column('report_id',sa.ForeignKey('sop_reports.id'),nullable=False),
        sa.Column('revision',sa.Integer,nullable=False),sa.Column('snapshot',sa.Text,nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('report_id','revision',name='uq_sop_report_version'))
    sa.Table('report_attachments',metadata,
        sa.Column('id',sa.Integer,primary_key=True),sa.Column('report_id',sa.ForeignKey('sop_reports.id'),nullable=False,index=True),
        sa.Column('org_id',sa.ForeignKey('organizations.id'),nullable=False),sa.Column('uploaded_by',sa.ForeignKey('users.id'),nullable=False),
        sa.Column('item_key',sa.String(60),nullable=False),sa.Column('filename',sa.String(160),nullable=False),
        sa.Column('media_type',sa.String(60),nullable=False),sa.Column('sha256',sa.String(64),nullable=False),
        sa.Column('size',sa.Integer,nullable=False),sa.Column('content',sa.LargeBinary,nullable=False),
        sa.Column('removed',sa.Boolean,nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    sa.Table('workflow_receipts',metadata,
        sa.Column('id',sa.Integer,primary_key=True),sa.Column('actor_id',sa.ForeignKey('users.id'),nullable=False),
        sa.Column('request_key',sa.String(100),nullable=False),sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('response',sa.Text,nullable=False),sa.UniqueConstraint('actor_id','request_key',name='uq_workflow_request'))
    names=['organization_positions','user_positions','sop_reports','sop_report_versions','report_attachments','workflow_receipts']
    metadata.create_all(op.get_bind(),tables=[metadata.tables[n] for n in names],checkfirst=True)


def downgrade():
    for name in ('workflow_receipts','report_attachments','sop_report_versions','sop_reports','user_positions','organization_positions'):
        op.drop_table(name)
