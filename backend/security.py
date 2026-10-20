"""Central authentication and object-level authorization."""
from __future__ import annotations
import hashlib
import hmac
from datetime import timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import LabOrder, Org, Patient, User, UserSession
from backend.utils import utcnow

def session_csrf(session: UserSession, raw_token: str) -> str:
    """Stable per-session synchronizer token; no plaintext CSRF value is persisted."""
    return hmac.new(bytes.fromhex(session.csrf_token_hash),
                    ('nam-csrf:' + raw_token).encode(), hashlib.sha256).hexdigest()

def authenticate_session(request: Request, db: Session, cookie: str, audience: str) -> User:
    token = request.cookies.get(cookie, '')
    if not token:
        raise HTTPException(401, 'Silakan masuk terlebih dahulu')
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    if not session or session.audience != audience or session.expires_at.replace(tzinfo=timezone.utc) < utcnow():
        raise HTTPException(401, 'Sesi tidak berlaku')
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, 'Akun tidak aktif')
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            raise HTTPException(403, 'Asal permintaan tidak diizinkan')
        csrf = request.headers.get('x-csrf-token', '')
        if not hmac.compare_digest(csrf, session_csrf(session, token)):
            raise HTTPException(403, 'CSRF token tidak valid')
    return user


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return authenticate_session(request, db, 'nam_session', 'workspace')


def patient_record(db: Session, user: User) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.user_id == user.id, Patient.org_id == 1))
    if user.role != 'patient' or user.org_id != 1 or not patient:
        raise HTTPException(403, 'Akun tidak memiliki akses portal pasien')
    return patient


def current_patient(request: Request, db: Session = Depends(get_db)) -> User:
    user = authenticate_session(request, db, 'nam_patient_session', 'patient')
    patient_record(db, user)
    return user


def role_only(user: User, *roles: str):
    if user.role not in roles:
        raise HTTPException(403, 'Akses divisi tidak diizinkan')
    if user.role not in ('partner', 'patient') and user.org_id != 1:
        raise HTTPException(403, 'Akses organisasi tidak diizinkan')

def get_order(db: Session, order_id: int) -> LabOrder:
    order = db.get(LabOrder, order_id)
    if not order:
        raise HTTPException(404, 'Order tidak ditemukan')
    return order


def can_view_order(user: User, order: LabOrder, db: Session) -> bool:
    if user.role not in ('partner', 'patient') and user.org_id != 1:
        return False
    if user.role in ('director','reception','lab_supervisor','qc') and user.org_id == 1:
        return True
    if user.role == 'finance' and user.org_id == 1:
        return True  # financial fields only; serializer hides clinical instructions
    if user.role == 'technician':
        return order.technician_id == user.id
    if user.role == 'dentist':
        return order.source == 'internal' and order.dentist_id == user.id
    if user.role == 'partner':
        return order.source == 'external' and order.org_id == user.org_id
    if user.role == 'patient':
        patient = db.get(Patient, order.patient_id)
        return bool(patient and patient.user_id == user.id and patient.org_id == user.org_id
                    and order.org_id == user.org_id and order.source == 'internal')
    return False  # IT never gets automatic access to clinical content


def require_order(db: Session, user: User, order_id: int) -> LabOrder:
    order = get_order(db, order_id)
    if not can_view_order(user, order, db):
        raise HTTPException(404, 'Order tidak ditemukan')
    return order


def encode_order(db: Session, user: User, o: LabOrder):
    partner = db.get(Org, o.org_id)
    result = {
        'id':o.id,'code':o.code,'source':o.source,'customer':partner.name if partner else '',
        'title':o.title if user.role not in ('finance','patient') else 'Order Lab',
        'category':o.category if user.role != 'finance' else None,
        'status':o.status,'lead_id':o.lead_id,'technician_id':o.technician_id,
        'estimated_due':str(o.estimated_due) if o.estimated_due else None,
        'promised_due':str(o.promised_due) if o.promised_due else None,
        'proposed_due':str(o.proposed_due) if o.proposed_due else None,
        'delay_response':o.delay_response,
    }
    if user.role in ('dentist','lab_supervisor','technician','qc','partner'):
        result['instruction'] = o.instruction
    if user.role in ('patient','partner','lab_supervisor','dentist'):
        result['delay_reason'] = o.delay_reason
    if user.role in ('reception','dentist','director'):
        patient = db.get(Patient,o.patient_id)
        result['patient'] = patient.display_name if patient else ''
    if user.role in ('lab_supervisor','qc','technician','partner','reception','dentist'):
        result['patient_ref'] = db.get(Patient,o.patient_id).public_id
    if user.role == 'patient':
        # The legacy demo API must also avoid exposing internal employee references.
        for key in ('lead_id', 'technician_id', 'customer'):
            result.pop(key, None)
    return result
