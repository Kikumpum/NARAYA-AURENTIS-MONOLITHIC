"""A patient's service and visit inbox; reading never grants consent."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Appointment, LabOrder, Notification, PatientNoticeRead, PatientUpdate, User
from backend.modules.audit import audit
from backend.modules.patient_visits import lock_patient, utc
from backend.security import current_patient, patient_record
from backend.utils import utcnow

router = APIRouter(prefix='/api/patient/notifications', tags=['Pemberitahuan pasien'])
TITLES = {'submitted':'Permintaan pengerjaan tercatat', 'accepted':'Pengerjaan diterima tim Lab',
          'estimate':'Estimasi pengerjaan diperbarui', 'progress':'Kabar dari tim Lab',
          'ready':'Hasil Lab siap diserahkan', 'rework':'Hasil sedang disempurnakan',
          'delay':'Tinjau usulan perubahan tanggal', 'delay_decision':'Respons Anda tercatat'}


def inbox(db, user):
    patient = patient_record(db, user)
    orders = {o.id:o for o in db.scalars(select(LabOrder).where(
        LabOrder.patient_id == patient.id, LabOrder.org_id == user.org_id, LabOrder.source == 'internal'))}
    appointments = {a.id:a for a in db.scalars(select(Appointment).where(Appointment.patient_id == patient.id))}
    reads = {(r.source,r.notice_id):r.read_at for r in db.scalars(select(PatientNoticeRead).where(
        PatientNoticeRead.owner_id == user.id, PatientNoticeRead.org_id == user.org_id))}
    result = []
    sources = (
        ('service',db.scalars(select(Notification).where(Notification.patient_id == patient.id,
            Notification.org_id == user.org_id).order_by(Notification.id.desc()).limit(100)).all()),
        ('visit',db.scalars(select(PatientUpdate).where(PatientUpdate.patient_id == patient.id,
            PatientUpdate.org_id == user.org_id).order_by(PatientUpdate.id.desc()).limit(100)).all()),
    )
    for source, rows in sources:
        for row in rows:
            if row.order_id is not None and row.order_id not in orders:
                continue
            appointment_id = row.appointment_id if source == 'visit' else None
            if appointment_id is not None and appointment_id not in appointments:
                continue
            order = orders.get(row.order_id)
            appointment = appointments.get(appointment_id)
            requires_action = bool((order and order.delay_response == 'pending' and row.kind == 'delay')
                or (appointment and appointment.status == 'awaiting_patient' and row.kind == 'appointment_change'))
            read_at = reads.get((source,row.id))
            result.append({'id':row.id, 'key':f'{source}/{row.id}', 'source':source, 'kind':row.kind,
                'category':'schedule' if source=='visit' else 'service',
                'title':row.title if source=='visit' else TITLES.get(row.kind,'Pembaruan layanan Anda'),
                'message':row.message, 'order_id':row.order_id, 'appointment_id':appointment_id,
                'requires_action':requires_action, 'created_at':utc(row.created_at).isoformat(),
                'read_at':utc(read_at).isoformat() if read_at else None})
    return sorted(result,key=lambda n:(n['created_at'],n['id']),reverse=True)


@router.get('')
def list_notices(user: User = Depends(current_patient), db: Session = Depends(get_db)):
    return inbox(db,user)


def record_read(db,user,notice):
    previous = db.scalar(select(PatientNoticeRead).where(PatientNoticeRead.owner_id == user.id,
        PatientNoticeRead.org_id == user.org_id, PatientNoticeRead.source == notice['source'],
        PatientNoticeRead.notice_id == notice['id']))
    if previous:
        return utc(previous.read_at).isoformat(), False
    value = utcnow()
    db.add(PatientNoticeRead(owner_id=user.id,org_id=user.org_id,source=notice['source'],notice_id=notice['id'],read_at=value))
    return value.isoformat(), True


@router.post('/read-all')
def read_all(user: User = Depends(current_patient), db: Session = Depends(get_db)):
    patient = patient_record(db,user); lock_patient(db,patient)
    changed = 0
    for notice in inbox(db,user):
        _, added = record_read(db,user,notice); changed += added
    if changed:
        audit(db,user,'patient.notifications_read','patient',patient.id,count=changed)
    db.commit()
    return {'marked':changed}


@router.post('/{source}/{notice_id}/read')
def read_notice(source: Literal['service','visit'], notice_id: int,
                user: User = Depends(current_patient), db: Session = Depends(get_db)):
    patient = patient_record(db,user); lock_patient(db,patient)
    notice = next((n for n in inbox(db,user) if n['source']==source and n['id']==notice_id),None)
    if not notice:
        raise HTTPException(404,'Pemberitahuan tidak ditemukan.')
    value, added = record_read(db,user,notice)
    if added:
        audit(db,user,'patient.notification_read','notification',notice_id,source=source)
    db.commit()
    return {'key':notice['key'],'read_at':value}
