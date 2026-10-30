"""Shared SQLAlchemy models; database schema preserved during extraction."""
from __future__ import annotations
from datetime import date, datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class Org(Base):
    __tablename__ = 'organizations'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(140))
    kind: Mapped[str] = mapped_column(String(20))  # internal / partner


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(140))
    password_hash: Mapped[str] = mapped_column(String(220))
    role: Mapped[str] = mapped_column(String(32))
    org_id: Mapped[int | None] = mapped_column(ForeignKey('organizations.id'), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserSession(Base):
    __tablename__ = 'sessions'
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    audience: Mapped[str] = mapped_column(String(16), default='workspace', server_default='workspace')


class Patient(Base):
    __tablename__ = 'patients'
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(30), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40))
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    contact_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    service_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_channel: Mapped[str] = mapped_column(String(20), default='portal')
    notification_level: Mapped[str] = mapped_column(String(20), default='standard')


class Shift(Base):
    __tablename__ = 'shifts'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    shift_day: Mapped[date] = mapped_column(Date)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    max_active_orders: Mapped[int] = mapped_column(Integer, default=4)
    __table_args__ = (UniqueConstraint('user_id', 'shift_day', name='uq_shift'),)


class Appointment(Base):
    __tablename__ = 'appointments'
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('patients.id'))
    dentist_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pending_dentist_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(25), default='confirmed')


class VisitTiming(Base):
    __tablename__ = 'visit_timings'
    appointment_id: Mapped[int] = mapped_column(ForeignKey('appointments.id'), primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    state: Mapped[str] = mapped_column(String(24), default='not_started')
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_finish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revision: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint("state IN ('not_started','in_service','finished','not_attended')", name='ck_visit_timing_state'),)


class WhatsappOutbox(Base):
    __tablename__ = 'whatsapp_outbox'
    id: Mapped[int] = mapped_column(primary_key=True)
    update_id: Mapped[int] = mapped_column(ForeignKey('patient_updates.id'), unique=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('patients.id'))
    appointment_id: Mapped[int] = mapped_column(ForeignKey('appointments.id'))
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    template_key: Mapped[str] = mapped_column(String(60))
    payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default='awaiting_configuration')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (CheckConstraint("status = 'awaiting_configuration'", name='ck_whatsapp_not_enabled'),)


class VisitDetails(Base):
    __tablename__ = 'patient_visit_details'
    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey('appointments.id'), unique=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    purpose: Mapped[str] = mapped_column(String(24))
    interest: Mapped[str] = mapped_column(String(24), default='general')
    order_id: Mapped[int | None] = mapped_column(ForeignKey('lab_orders.id'), nullable=True)


class PatientUpdate(Base):
    __tablename__ = 'patient_updates'
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('patients.id'))
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    kind: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(String(400))
    order_id: Mapped[int | None] = mapped_column(ForeignKey('lab_orders.id'), nullable=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey('appointments.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PatientNoticeRead(Base):
    __tablename__ = 'patient_notice_reads'
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    source: Mapped[str] = mapped_column(String(16))
    notice_id: Mapped[int] = mapped_column(Integer)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint('owner_id', 'source', 'notice_id', name='uq_patient_notice_read'),
                      CheckConstraint("source IN ('service','visit')", name='ck_patient_notice_source'))


class LabOrder(Base):
    __tablename__ = 'lab_orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    source: Mapped[str] = mapped_column(String(20))  # internal or external
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    patient_id: Mapped[int] = mapped_column(ForeignKey('patients.id'))
    dentist_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    title: Mapped[str] = mapped_column(String(120))
    instruction: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30), default='crown')
    status: Mapped[str] = mapped_column(String(32), default='submitted')
    lead_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    estimated_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    promised_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    proposed_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    delay_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    delay_response: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Invoice(Base):
    __tablename__ = 'invoices'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('lab_orders.id'), unique=True)
    amount_idr: Mapped[int] = mapped_column(Integer)
    invoice_type: Mapped[str] = mapped_column(String(20))  # internal_cost / external_invoice
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Payment(Base):
    __tablename__ = 'payments'
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey('invoices.id'))
    method: Mapped[str] = mapped_column(String(30))
    amount_idr: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default='pending_verification')
    received_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    verified_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey('patients.id'), nullable=True)
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    order_id: Mapped[int] = mapped_column(ForeignKey('lab_orders.id'))
    channel: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(400))
    status: Mapped[str] = mapped_column(String(20), default='queued')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class DailyReport(Base):
    __tablename__ = 'daily_reports'
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    org_id: Mapped[int | None] = mapped_column(ForeignKey('organizations.id'), nullable=True)
    division: Mapped[str] = mapped_column(String(60))
    report_day: Mapped[date] = mapped_column(Date)
    summary: Mapped[str] = mapped_column(Text)
    blockers: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Audit(Base):
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    event: Mapped[str] = mapped_column(String(90))
    entity: Mapped[str] = mapped_column(String(35))
    entity_id: Mapped[int] = mapped_column(Integer)
    detail: Mapped[str] = mapped_column(Text, default='{}')
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ChatConversation(Base):
    __tablename__ = 'chat_conversations'
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    service_org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'), default=1)
    order_id: Mapped[int | None] = mapped_column(ForeignKey('lab_orders.id'), nullable=True)
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='assistant', index=True)
    request_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        UniqueConstraint('owner_id', 'request_id', name='uq_chat_start'),
        CheckConstraint("status IN ('assistant','waiting','human','closed')", name='ck_chat_status'),
    )


class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('chat_conversations.id'), index=True)
    sender: Mapped[str] = mapped_column(String(16))
    author_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    request_key: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        UniqueConstraint('conversation_id','request_key',name='uq_chat_message_request'),
        CheckConstraint("sender IN ('user','assistant','agent','system')",name='ck_chat_sender'),
    )


class OrganizationPosition(Base):
    __tablename__ = 'organization_positions'
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    code: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(120))
    parent_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    division: Mapped[str] = mapped_column(String(100))
    allowed_roles: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('org_id', 'code', name='uq_org_position'),)


class UserPosition(Base):
    __tablename__ = 'user_positions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True)
    position_id: Mapped[int] = mapped_column(ForeignKey('organization_positions.id'))
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    revision: Mapped[int] = mapped_column(Integer, default=1)


class SopReport(Base):
    __tablename__ = 'sop_reports'
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'), index=True)
    position_name: Mapped[str] = mapped_column(String(120))
    division: Mapped[str] = mapped_column(String(100))
    sop_code: Mapped[str] = mapped_column(String(30))
    sop_snapshot: Mapped[str] = mapped_column(Text)
    order_id: Mapped[int | None] = mapped_column(ForeignKey('lab_orders.id'), nullable=True)
    order_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    report_day: Mapped[date] = mapped_column(Date)
    summary: Mapped[str] = mapped_column(Text, default='')
    results: Mapped[str] = mapped_column(Text, default='[]')
    status: Mapped[str] = mapped_column(String(20), default='draft')
    revision: Mapped[int] = mapped_column(Integer, default=1)
    review_note: Mapped[str] = mapped_column(Text, default='')
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (CheckConstraint("status IN ('draft','submitted','reviewed','returned')", name='ck_sop_report_status'),)


class SopReportVersion(Base):
    __tablename__ = 'sop_report_versions'
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey('sop_reports.id'))
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint('report_id','revision', name='uq_sop_report_version'),)


class ReportAttachment(Base):
    __tablename__ = 'report_attachments'
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey('sop_reports.id'), index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    item_key: Mapped[str] = mapped_column(String(60))
    filename: Mapped[str] = mapped_column(String(160))
    media_type: Mapped[str] = mapped_column(String(60))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    removed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class WorkflowReceipt(Base):
    __tablename__ = 'workflow_receipts'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    request_key: Mapped[str] = mapped_column(String(100))
    fingerprint: Mapped[str] = mapped_column(String(64))
    response: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('actor_id','request_key',name='uq_workflow_request'),)
