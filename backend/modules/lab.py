from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.security import current_user, role_only

router = APIRouter()

import secrets
import json
from datetime import date, timedelta
from typing import Literal
from pydantic import BaseModel, Field
from backend.constants import CATEGORIES
from backend.models import Audit, LabOrder, Patient, Shift, User
from backend.modules.audit import audit
from backend.modules.communication import queue_notice
from backend.schemas import DecisionIn
from backend.security import can_view_order, encode_order, require_order
from backend.utils import utcnow

@router.get('/api/orders')
def orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows=db.scalars(select(LabOrder).order_by(LabOrder.id.desc())).all()
    return [encode_order(db,user,o) for o in rows if can_view_order(user,o,db)]


@router.get('/api/orders/{oid}')
def order_detail(oid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """A scoped service timeline, with no raw audit payloads or clinical notes."""
    o = require_order(db, user, oid)
    visible_events = (
        'lab_order.submitted', 'lab_order.lead_assigned', 'lab_order.accepted',
        'lab_order.rejected', 'lab_order.plan_validated', 'lab_order.progress',
        'lab_order.qc_passed', 'lab_order.qc_failed', 'lab_order.delay_proposed',
        'lab_order.delay_decided',
    )
    events = db.scalars(select(Audit).where(Audit.entity == 'order', Audit.entity_id == o.id,
                                          Audit.event.in_(visible_events)).order_by(Audit.id)).all()
    timeline = []
    initial_due = str(o.promised_due) if o.promised_due else None
    for event in events:
        item = {'event': event.event, 'at': event.occurred_at.isoformat() + 'Z' if event.occurred_at.tzinfo is None else event.occurred_at.isoformat()}
        if event.event == 'lab_order.delay_proposed':
            detail = json.loads(event.detail)
            item.update(old_due=detail.get('old'), new_due=detail.get('new'))
            if not any(row['event'] == 'lab_order.delay_proposed' for row in timeline):
                initial_due = detail.get('old')
        timeline.append(item)
    audit(db, user, 'order.viewed', 'order', o.id)
    db.commit()
    return {'order': encode_order(db, user, o), 'activity': timeline, 'initial_due': initial_due}


class OrderIn(BaseModel):
    patient_id: int
    title: str=Field(min_length=3,max_length=120)
    instruction: str=Field(min_length=10,max_length=1500)
    category: Literal['crown','bridge','veneer','denture','implant','other']
    promised_due: date | None=None


@router.post('/api/orders')
def create_order(data: OrderIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'dentist','partner')
    patient=db.get(Patient,data.patient_id)
    if not patient or (user.role=='dentist' and patient.org_id!=1) or (user.role=='partner' and patient.org_id!=user.org_id):
        raise HTTPException(400,'Pasien tidak ada pada organisasi berwenang')
    o=LabOrder(code='LAB-'+secrets.token_hex(5).upper(),source='internal' if user.role=='dentist' else 'external',org_id=1 if user.role=='dentist' else user.org_id,patient_id=patient.id,dentist_id=user.id if user.role=='dentist' else None,title=data.title,instruction=data.instruction,category=data.category,status='submitted',promised_due=data.promised_due)
    db.add(o);db.flush();audit(db,user,'lab_order.submitted','order',o.id,source=o.source)
    queue_notice(db,o,'submitted','Permintaan pengerjaan gigi Anda sudah tercatat. Dokter dan tim Lab akan menindaklanjutinya.')
    db.commit();return {'id':o.id,'code':o.code,'status':o.status}


class AssignLeadIn(BaseModel):
    lead_id: int


@router.post('/api/orders/{oid}/assign-lead')
def assign_lead(oid: int, data: AssignLeadIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'reception')
    o=require_order(db,user,oid)
    if o.status not in ('submitted','rejected'):
        raise HTTPException(409,'Order tidak dapat ditugaskan pada status ini')
    lead=db.get(User,data.lead_id)
    if not lead or lead.role!='lab_supervisor' or lead.org_id!=1:
        raise HTTPException(400,'Penanggung Jawab Lab tidak valid')
    shift=db.scalar(select(Shift).where(Shift.user_id==lead.id,Shift.shift_day==date.today(),Shift.available==True))
    if not shift: raise HTTPException(409,'Penanggung Jawab Lab tidak masuk hari ini')
    o.lead_id=lead.id;o.status='assigned';o.updated_at=utcnow()
    audit(db,user,'lab_order.lead_assigned','order',o.id,lead_id=lead.id)
    db.commit();return {'status':o.status}


class ConfirmIn(BaseModel):
    accept: bool
    reason: str | None=Field(default=None,max_length=400)


@router.post('/api/orders/{oid}/confirm')
def confirm(oid: int, data: ConfirmIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'lab_supervisor')
    o=require_order(db,user,oid)
    if o.lead_id!=user.id or o.status!='assigned': raise HTTPException(409,'Order bukan penugasan Anda yang sedang menunggu')
    if not data.accept and not (data.reason or '').strip():raise HTTPException(400,'Alasan penolakan wajib')
    o.status='accepted' if data.accept else 'rejected';o.updated_at=utcnow()
    audit(db,user,'lab_order.accepted' if data.accept else 'lab_order.rejected','order',o.id,reason=data.reason)
    if data.accept: queue_notice(db,o,'accepted','Order laboratorium Anda sudah diterima dan akan diproses.')
    db.commit();return {'status':o.status}


def eta_suggestion(db:Session, o:LabOrder):
    active=db.scalar(select(func.count()).select_from(LabOrder).where(LabOrder.status.in_(['accepted','design','production','finishing','qc_pending','rework']),LabOrder.id!=o.id)) or 0
    days=CATEGORIES.get(o.category,5)+active//3
    return date.today()+timedelta(days=days)


@router.get('/api/orders/{oid}/eta-suggestion')
def eta(oid:int, user:User=Depends(current_user), db:Session=Depends(get_db)):
    role_only(user,'lab_supervisor','reception')
    o=require_order(db,user,oid)
    return {'recommended_due':str(eta_suggestion(db,o)),'note':'Heuristik demo, harus divalidasi supervisor. Belum berbasis kapasitas nyata.'}


class PlanIn(BaseModel):
    technician_id: int
    due: date
    override_reason: str | None=Field(default=None,max_length=400)


@router.post('/api/orders/{oid}/plan')
def plan(oid:int,data:PlanIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'lab_supervisor')
    o=require_order(db,user,oid)
    if o.lead_id!=user.id or o.status!='accepted':raise HTTPException(409,'Order harus diterima oleh Anda terlebih dahulu')
    tech=db.get(User,data.technician_id)
    if not tech or not tech.active or tech.role!='technician' or tech.org_id != user.org_id:
        raise HTTPException(400,'Teknisi tidak valid pada organisasi berwenang')
    if not db.scalar(select(Shift).where(Shift.user_id==tech.id, Shift.shift_day==date.today(), Shift.available==True)):
        raise HTTPException(409,'Teknisi tidak terjadwal hari ini')
    suggestion=eta_suggestion(db,o)
    if data.due < suggestion and not (data.override_reason or '').strip():raise HTTPException(400,'Estimasi lebih cepat dari rekomendasi memerlukan alasan')
    if data.due < date.today():raise HTTPException(400,'Tanggal estimasi sudah berlalu')
    o.technician_id=tech.id;o.estimated_due=data.due;o.promised_due=o.promised_due or data.due;o.status='production';o.updated_at=utcnow()
    audit(db,user,'lab_order.plan_validated','order',o.id,estimate=str(data.due),suggestion=str(suggestion),override=data.override_reason)
    queue_notice(db,o,'estimate','Estimasi pengerjaan order Anda telah diperbarui. Lihat portal untuk informasi terbaru.')
    db.commit();return {'status':o.status,'estimated_due':str(data.due)}


class ProgressIn(BaseModel):
    status: Literal['design','production','finishing','qc_pending']


@router.post('/api/orders/{oid}/progress')
def progress(oid:int,data:ProgressIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'technician')
    o=require_order(db,user,oid)
    allowed={'production':['design','finishing','qc_pending'], 'design':['production','finishing','qc_pending'], 'finishing':['qc_pending'],'rework':['design','production','finishing','qc_pending']}
    if data.status not in allowed.get(o.status,[]):raise HTTPException(409,'Perpindahan status produksi tidak valid')
    before=o.status;o.status=data.status;o.updated_at=utcnow();audit(db,user,'lab_order.progress','order',o.id,previous=before,new=data.status)
    stage={'design':'tahap desain','production':'tahap pengerjaan','finishing':'penyelesaian akhir','qc_pending':'pemeriksaan hasil'}[data.status]
    queue_notice(db,o,'progress',f'Pengerjaan gigi Anda masuk ke {stage}. Perkembangan terbaru tersedia di portal.')
    db.commit();return {'status':o.status}


class QcIn(BaseModel):
    passed: bool
    reason: str | None=Field(default=None,max_length=500)


@router.post('/api/orders/{oid}/qc')
def quality(oid:int,data:QcIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'qc')
    o=require_order(db,user,oid)
    if o.status!='qc_pending':raise HTTPException(409,'Order belum menunggu QC')
    if not data.passed and not (data.reason or '').strip():raise HTTPException(400,'Alasan gagal QC wajib')
    o.status='ready' if data.passed else 'rework';o.updated_at=utcnow()
    audit(db,user,'lab_order.qc_passed' if data.passed else 'lab_order.qc_failed','order',o.id,reason=data.reason)
    if data.passed: queue_notice(db,o,'ready','Pekerjaan laboratorium Anda telah selesai. Silakan lihat portal untuk informasi penyerahan.')
    else: queue_notice(db,o,'rework','Hasil sedang disempurnakan oleh tim Lab setelah pemeriksaan QC. Anda dapat melihat perkembangannya di portal.')
    db.commit();return {'status':o.status}


class DelayIn(BaseModel):
    new_due: date
    reason: str=Field(min_length=8,max_length=400)


@router.post('/api/orders/{oid}/delay')
def propose_delay(oid:int,data:DelayIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'lab_supervisor')
    o=require_order(db,user,oid)
    if o.lead_id!=user.id or o.status not in ('accepted','design','production','finishing','qc_pending','rework'):
        raise HTTPException(409,'Order tidak dapat direvisi oleh Anda')
    if o.delay_response == 'pending':
        raise HTTPException(409,'Usulan tanggal masih menunggu respons dan tidak dapat ditimpa')
    base=o.promised_due or o.estimated_due
    if not base or data.new_due <= base:raise HTTPException(400,'Tanggal baru harus lebih lambat dari komitmen yang tercatat')
    o.proposed_due=data.new_due;o.delay_reason=data.reason;o.delay_response='pending'
    # The original promise is never overwritten until an authorized party accepts.
    audit(db,user,'lab_order.delay_proposed','order',o.id,old=str(base),new=str(data.new_due),reason=data.reason)
    queue_notice(db,o,'delay','Ada usulan perubahan estimasi order Lab. Silakan buka portal untuk meninjau dan merespons.')
    db.commit();return {'response':'pending','original_due':str(base),'proposed_due':str(data.new_due)}


class DelayDecisionIn(DecisionIn):
    expected_due: date


@router.post('/api/orders/{oid}/delay/respond')
def respond_delay(oid:int,data:DelayDecisionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'patient','partner')
    o=require_order(db,user,oid)
    if o.delay_response!='pending' or not o.proposed_due:raise HTTPException(409,'Tidak ada revisi aktif')
    if data.expected_due != o.proposed_due:
        raise HTTPException(409,'Usulan tanggal telah berubah. Muat ulang untuk meninjau versi terbaru')
    if (user.role=='patient' and o.source!='internal') or (user.role=='partner' and o.source!='external'):
        raise HTTPException(403,'Bukan penerima persetujuan yang berwenang')
    if data.approved:
        o.promised_due=o.proposed_due;o.estimated_due=o.proposed_due
    o.delay_response='approved' if data.approved else 'rejected';o.proposed_due=None
    audit(db,user,'lab_order.delay_decided','order',o.id,approved=data.approved)
    db.commit();return {'response':o.delay_response,'promised_due':str(o.promised_due)}
