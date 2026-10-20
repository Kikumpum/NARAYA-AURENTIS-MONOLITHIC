"""Patient booking, shared slot guards and private in-portal visit updates."""
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Appointment, LabOrder, Patient, PatientUpdate, Shift, User, VisitDetails
from backend.modules.audit import audit
from backend.security import current_patient, patient_record, require_order
from backend.utils import utcnow
from backend.workflow import finish, replay

router = APIRouter(prefix='/api/patient', tags=['Jadwal pasien'])
WIB = timezone(timedelta(hours=7))
PURPOSES = {'consultation':'Konsultasi', 'follow_up':'Kontrol perawatan', 'fitting':'Pemasangan hasil Lab'}
INTERESTS = {'general':'Perawatan umum', 'braces':'Behel', 'scaling':'Scaling', 'daily_care':'Perawatan gigi harian'}


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def lock_patient(db, patient):
    # SQLite ignores FOR UPDATE; serialize its local-demo writers explicitly.
    if db.bind.dialect.name == 'sqlite':
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    db.scalar(select(Patient).where(Patient.id == patient.id).with_for_update())


def valid_day(day):
    today = utcnow().astimezone(WIB).date()
    if not today < day <= today + timedelta(days=30):
        raise HTTPException(422, 'Pilih tanggal mulai besok hingga 30 hari ke depan.')


def doctor_for(db, org_id, doctor_id, locking=False):
    statement = select(User).where(User.id == doctor_id, User.org_id == org_id,
                                   User.role == 'dentist', User.active == True)
    doctor = db.scalar(statement.with_for_update() if locking else statement)
    if not doctor:
        raise HTTPException(404, 'Dokter tidak tersedia pada klinik Anda.')
    return doctor


def conflicting(db, patient_id, doctor_id, start, exclude=None):
    # Existing appointments are treated as 30-minute visits in this demo,
    # including older entries outside the self-service booking grid.
    query = select(Appointment).where(Appointment.status != 'cancelled',
        Appointment.scheduled_at > start - timedelta(minutes=30),
        Appointment.scheduled_at < start + timedelta(minutes=30),
        or_(Appointment.patient_id == patient_id, Appointment.dentist_id == doctor_id,
            Appointment.pending_dentist_id == doctor_id))
    if exclude is not None:
        query = query.where(Appointment.id != exclude)
    return db.scalar(query.limit(1)) is not None


def check_reservation(db, patient, doctor_id, start, exclude=None):
    doctor = doctor_for(db, patient.org_id, doctor_id, locking=True)
    day = utc(start).astimezone(WIB).date()
    shift = db.scalar(select(Shift).where(Shift.user_id == doctor.id, Shift.shift_day == day,
                                         Shift.available == True).with_for_update())
    if not shift:
        raise HTTPException(409, 'Dokter tidak bertugas pada tanggal tersebut.')
    if conflicting(db, patient.id, doctor.id, utc(start), exclude):
        raise HTTPException(409, 'Waktu tersebut sudah terisi. Silakan pilih waktu lain.')
    return doctor


def visit_update(db, patient, appointment, kind, title, message, order_id=None):
    # Essential in-portal service information only. No external sender is used.
    db.add(PatientUpdate(patient_id=patient.id, org_id=patient.org_id, appointment_id=appointment.id,
                         order_id=order_id, kind=kind, title=title, message=message))


def appointment_view(db, row):
    patient = db.get(Patient, row.patient_id)
    doctor = db.get(User, row.dentist_id)
    pending = db.get(User, row.pending_dentist_id) if row.pending_dentist_id else None
    details = db.scalar(select(VisitDetails).where(VisitDetails.appointment_id == row.id,
        VisitDetails.org_id == patient.org_id, VisitDetails.owner_id == patient.user_id))
    order = db.get(LabOrder, details.order_id) if details and details.order_id else None
    if order and (order.patient_id != patient.id or order.org_id != patient.org_id or order.source != 'internal'):
        order = None
    return {'id':row.id, 'dentist':doctor.display_name if doctor and doctor.org_id == patient.org_id and doctor.role == 'dentist' else 'Dokter perlu dikonfirmasi', 'scheduled_at':utc(row.scheduled_at).isoformat(),
            'status':row.status, 'proposed_dentist':pending.display_name if pending and pending.org_id == patient.org_id and pending.role == 'dentist' else None,
            'purpose':details.purpose if details else 'consultation',
            'interest':details.interest if details else 'general',
            'order_id':order.id if order else None, 'order_code':order.code if order else None,
            'can_cancel':row.status != 'cancelled' and utc(row.scheduled_at) > utcnow()}


@router.get('/doctors')
def doctors(user: User = Depends(current_patient), db: Session = Depends(get_db)):
    today = utcnow().astimezone(WIB).date()
    rows = db.scalars(select(User).join(Shift, Shift.user_id == User.id).where(
        User.org_id == user.org_id, User.role == 'dentist', User.active == True,
        Shift.available == True, Shift.shift_day > today, Shift.shift_day <= today + timedelta(days=30))
        .distinct().order_by(User.display_name)).all()
    return [{'id':row.id, 'name':row.display_name, 'service':'Dokter gigi klinik'} for row in rows]


@router.get('/appointment-slots')
def slots(doctor_id: int, day: date, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    patient = patient_record(db, user)
    valid_day(day)
    doctor = doctor_for(db, user.org_id, doctor_id)
    shift = db.scalar(select(Shift).where(Shift.user_id == doctor.id, Shift.shift_day == day, Shift.available == True))
    result = []
    if shift:
        start = datetime.combine(day, time(9), WIB)
        for offset in range(16):
            value = (start + timedelta(minutes=offset*30)).astimezone(timezone.utc)
            result.append({'starts_at':value.isoformat(), 'label':value.astimezone(WIB).strftime('%H.%M'),
                           'available':not conflicting(db, patient.id, doctor.id, value)})
    return {'day':str(day), 'doctor_id':doctor.id, 'timezone':'Asia/Jakarta', 'duration_minutes':30,
            'slots':result, 'note':'Jam latihan 09.00–17.00 WIB. Jadwal klinik sebenarnya belum diaktifkan.'}


class BookingIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    doctor_id: int
    scheduled_at: AwareDatetime
    purpose: Literal['consultation','follow_up','fitting'] = 'consultation'
    interest: Literal['general','braces','scaling','daily_care'] = 'general'
    order_id: int | None = None
    request_key: str = Field(min_length=12, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')


@router.post('/appointments')
def book(data: BookingIn, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    patient = patient_record(db, user)
    lock_patient(db, patient)
    fingerprint, prior = replay(db, user, 'patient.visit.book', data.model_dump(mode='json'))
    if prior is not None:
        return prior
    local = data.scheduled_at.astimezone(WIB)
    valid_day(local.date())
    if local.hour < 9 or local.hour >= 17 or local.minute not in (0,30) or local.second or local.microsecond:
        raise HTTPException(422, 'Pilih salah satu waktu kunjungan yang tersedia.')
    order = require_order(db, user, data.order_id) if data.order_id is not None else None
    if order and (order.source != 'internal' or order.patient_id != patient.id or order.org_id != user.org_id):
        raise HTTPException(404, 'Pengerjaan tidak ditemukan.')
    if data.purpose == 'fitting' and (not order or order.status != 'ready'):
        raise HTTPException(409, 'Jadwal pemasangan dapat dipilih setelah hasil Lab lolos QC dan siap diserahkan.')
    if order and order.dentist_id != data.doctor_id:
        raise HTTPException(409, 'Untuk pengerjaan ini, pilih dokter klinik yang menangani perawatan Anda.')
    doctor = check_reservation(db, patient, data.doctor_id, data.scheduled_at)
    row = Appointment(patient_id=patient.id, dentist_id=doctor.id, scheduled_at=utc(data.scheduled_at), status='confirmed')
    db.add(row); db.flush()
    db.add(VisitDetails(appointment_id=row.id, owner_id=user.id, org_id=user.org_id, purpose=data.purpose,
                        interest=data.interest, order_id=order.id if order else None))
    stamp = local.strftime('%d/%m/%Y pukul %H.%M WIB')
    visit_update(db, patient, row, 'appointment_booked', 'Jadwal kunjungan tersimpan',
                 f'{PURPOSES[data.purpose]} bersama {doctor.display_name}, {stamp}.', data.order_id)
    audit(db, user, 'patient.appointment_booked', 'appointment', row.id,
          doctor_id=doctor.id, purpose=data.purpose, order_id=data.order_id)
    return finish(db, user, data.request_key, fingerprint, {'id':row.id, 'status':row.status})


class CancelIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reason: str = Field(min_length=5, max_length=300)
    request_key: str = Field(min_length=12, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')


@router.post('/appointments/{aid}/cancel')
def cancel(aid: int, data: CancelIn, user: User = Depends(current_patient), db: Session = Depends(get_db)):
    patient = patient_record(db, user)
    lock_patient(db, patient)
    row = db.scalar(select(Appointment).where(Appointment.id == aid, Appointment.patient_id == patient.id).with_for_update())
    if not row:
        raise HTTPException(404, 'Jadwal tidak ditemukan.')
    fingerprint, prior = replay(db, user, 'patient.visit.cancel', {**data.model_dump(), 'appointment_id':aid})
    if prior is not None:
        return prior
    if row.status != 'cancelled':
        if utc(row.scheduled_at) <= utcnow():
            raise HTTPException(409, 'Kunjungan yang sudah lewat perlu ditinjau petugas.')
        row.status = 'cancelled'; row.pending_dentist_id = None
        visit_update(db, patient, row, 'appointment_cancelled', 'Kunjungan dibatalkan',
                     'Pembatalan jadwal Anda sudah dicatat. Anda dapat memilih jadwal baru.')
        audit(db, user, 'patient.appointment_cancelled', 'appointment', row.id, reason=data.reason)
    return finish(db, user, data.request_key, fingerprint, {'id':row.id, 'status':row.status})
