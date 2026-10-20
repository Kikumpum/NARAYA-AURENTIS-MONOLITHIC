"""Patient-only boundary with its own session and minimal service serializers."""
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Appointment, Audit, LabOrder, Notification, Patient, User, UserSession
from backend.modules import auth, chat, clinic, lab
from backend.modules.audit import audit
from backend.schemas import DecisionIn
from backend.security import current_patient, patient_record, require_order, session_csrf

router = APIRouter(prefix='/api/patient', tags=['Portal pasien'])
COOKIE = 'nam_patient_session'
PATH = '/api/patient'


def profile(db, user):
    patient = patient_record(db, user)
    return {'name': patient.display_name, 'reference': patient.public_id}


@router.post('/login')
def login(payload: auth.LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    # A patient reference is an identifier, never an authentication secret.
    user = auth.verify_credentials(auth.patient_credentials(payload, db), request, db)
    patient_record(db, user)
    csrf = auth.issue_session(user, request, response, db, cookie=COOKIE, audience='patient', path=PATH)
    return {**profile(db, user), 'csrf': csrf, 'demo': True}


@router.get('/me')
def me(request: Request, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    token = request.cookies[COOKIE]
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    return {**profile(db, user), 'csrf': session_csrf(session, token)}


@router.post('/logout')
def logout(request: Request, response: Response, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    digest = hashlib.sha256(request.cookies[COOKIE].encode()).hexdigest()
    session = db.scalar(select(UserSession).where(UserSession.token_hash == digest, UserSession.audience == 'patient'))
    if session:
        db.delete(session)
    audit(db, user, 'auth.logout', 'user', user.id, audience='patient')
    db.commit()
    response.delete_cookie(COOKIE, path=PATH)
    return {'ok': True}


def service_view(o):
    return {'id':o.id, 'code':o.code, 'category':o.category, 'status':o.status,
            'estimated_due':str(o.estimated_due) if o.estimated_due else None,
            'promised_due':str(o.promised_due) if o.promised_due else None,
            'proposed_due':str(o.proposed_due) if o.proposed_due else None,
            'delay_response':o.delay_response, 'delay_reason':o.delay_reason,
            'updated_at':chat.timestamp(o.updated_at)}


@router.get('/orders')
def orders(user: User = Depends(current_patient), db: Session = Depends(get_db)):
    patient = patient_record(db, user)
    rows = db.scalars(select(LabOrder).where(LabOrder.patient_id == patient.id, LabOrder.org_id == user.org_id,
                                           LabOrder.source == 'internal').order_by(LabOrder.id.desc())).all()
    return [service_view(o) for o in rows]


@router.get('/orders/{oid}')
def order_detail(oid: int, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    order = require_order(db, user, oid)
    # Explicit allowlist: no employee identities, clinical instructions, or raw audit JSON.
    labels = {'lab_order.submitted':'Permintaan layanan tercatat', 'lab_order.accepted':'Pengerjaan diterima',
              'lab_order.plan_validated':'Estimasi pengerjaan ditetapkan', 'lab_order.progress':'Pengerjaan diperbarui',
              'lab_order.qc_passed':'Pemeriksaan hasil selesai', 'lab_order.qc_failed':'Hasil sedang diperbaiki',
              'lab_order.delay_proposed':'Usulan perubahan tanggal', 'lab_order.delay_decided':'Respons perubahan tanggal dicatat'}
    rows = db.scalars(select(Audit).where(Audit.entity == 'order', Audit.entity_id == oid,
                    Audit.event.in_(tuple(labels))).order_by(Audit.id)).all()
    history = []
    for row in rows:
        detail = json.loads(row.detail)
        item = {'label':labels[row.event], 'at':chat.timestamp(row.occurred_at)}
        if row.event == 'lab_order.delay_proposed':
            item.update(previous_due=detail.get('old'), proposed_due=detail.get('new'))
        if row.event == 'lab_order.delay_decided':
            item['approved'] = detail.get('approved')
        history.append(item)
    audit(db, user, 'patient_portal.service_viewed', 'order', oid)
    db.commit()
    return {**service_view(order), 'history':history}


@router.post('/orders/{oid}/delay/respond')
def delay_response(oid: int, data: lab.DelayDecisionIn, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    return lab.respond_delay(oid, data, user, db)


def own_appointment(db, user, aid):
    patient = patient_record(db, user)
    appointment = db.get(Appointment, aid)
    if not appointment or appointment.patient_id != patient.id:
        raise HTTPException(404, 'Jadwal tidak ditemukan')
    return appointment


@router.get('/appointments')
def appointments(user: User = Depends(current_patient), db: Session = Depends(get_db)):
    patient = patient_record(db, user)
    rows = db.scalars(select(Appointment).where(Appointment.patient_id == patient.id).order_by(Appointment.scheduled_at.desc())).all()
    result = []
    for row in rows:
        doctor = db.get(User, row.dentist_id)
        pending = db.get(User, row.pending_dentist_id) if row.pending_dentist_id else None
        result.append({'id':row.id, 'dentist':doctor.display_name, 'scheduled_at':chat.timestamp(row.scheduled_at),
                       'status':row.status, 'proposed_dentist':pending.display_name if pending else None})
    return result


@router.post('/appointments/{aid}/respond')
def appointment_response(aid: int, data: DecisionIn, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    own_appointment(db, user, aid)
    return clinic.appointment_response(aid, data, user, db)


@router.get('/notifications')
def notifications(user: User = Depends(current_patient), db: Session = Depends(get_db)):
    patient = patient_record(db, user)
    rows = db.scalars(select(Notification).where(Notification.patient_id == patient.id, Notification.org_id == user.org_id)
                      .order_by(Notification.id.desc()).limit(100)).all()
    return [{'id':n.id, 'order_id':n.order_id, 'message':n.message, 'created_at':chat.timestamp(n.created_at)} for n in rows]


@router.get('/chat/conversations')
def conversations(user: User = Depends(current_patient), db: Session = Depends(get_db)):
    return chat.list_conversations(user, db)


@router.post('/chat/conversations')
def start(data: chat.StartIn, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    return chat.start_conversation(data, user, db)


@router.get('/chat/conversations/{ident}')
def read(ident: str, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    return chat.read_conversation(ident, user, db)


@router.post('/chat/conversations/{ident}/messages')
def message(ident: str, data: chat.MessageIn, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    return chat.send_message(ident, data, user, db)


@router.post('/chat/conversations/{ident}/handoff')
def handoff(ident: str, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    return chat.handoff(ident, user, db)


@router.post('/chat/conversations/{ident}/close')
def close(ident: str, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    return chat.close_conversation(ident, user, db)
