from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.security import current_user, role_only

router = APIRouter()

import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from pydantic import AwareDatetime, BaseModel, Field
from backend.models import Appointment, LabOrder, Patient, Shift, User
from backend.modules.audit import audit
from backend.schemas import DecisionIn

@router.get('/api/roster')
def roster(day: date | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'reception','lab_supervisor','director','dentist')
    day = day or date.today()
    shifts = db.scalars(select(Shift).where(Shift.shift_day==day, Shift.available==True)).all()
    out = []
    for sh in shifts:
        person = db.get(User, sh.user_id)
        if not person or not person.active or person.org_id != user.org_id or person.role not in ('dentist','lab_supervisor','technician'):
            continue
        owner = LabOrder.technician_id if person.role == 'technician' else LabOrder.lead_id
        active = db.scalar(select(func.count()).select_from(LabOrder).where(owner==person.id, LabOrder.status.notin_(['ready','completed','rejected']))) or 0
        out.append({'id':person.id,'name':person.display_name,'role':person.role,'active_orders':active,'capacity':sh.max_active_orders})
    return out


@router.get('/api/patients')
def patients(user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user, 'reception','dentist','director','partner')
    # Only pseudonymous patients created within the authenticated partner's own organization.
    ps = db.scalars(select(Patient).where(Patient.org_id == (user.org_id if user.role=='partner' else 1))).all()
    if user.role == 'dentist':
        ap_ids = set(db.scalars(select(Appointment.patient_id).where(Appointment.dentist_id==user.id)).all())
        order_ids = set(db.scalars(select(LabOrder.patient_id).where(LabOrder.dentist_id==user.id)).all())
        ps = [p for p in ps if p.id in ap_ids|order_ids]
    return [{'id':p.id,'public_id':p.public_id,'name':p.display_name,'contact_verified':p.contact_verified,'consent':p.service_consent,'channel':p.preferred_channel,'level':p.notification_level} for p in ps]


class PatientIn(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    phone: str = Field(min_length=8,max_length=40)
    channel: Literal['whatsapp','sms','email','portal'] = 'portal'
    level: Literal['minimal','standard','detail'] = 'standard'
    verified: bool = False
    consent: bool = False


@router.post('/api/patients')
def create_patient(data: PatientIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'reception')
    # Verified and consent toggles are DEMO assertions only; real flow requires OTP and consent evidence.
    p = Patient(public_id='DEMO-P-'+secrets.token_hex(4).upper(),display_name=data.name,phone=data.phone,org_id=1,preferred_channel=data.channel,notification_level=data.level,contact_verified=data.verified,service_consent=data.consent)
    db.add(p);db.flush()
    audit(db,user,'patient.registered','patient',p.id,consent=p.service_consent,channel=p.preferred_channel)
    db.commit()
    return {'id':p.id,'public_id':p.public_id}


class PartnerPatientIn(BaseModel):
    reference: str = Field(min_length=3,max_length=120)


@router.post('/api/partner/patients')
def register_partner_case(data: PartnerPatientIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'partner')
    # External lab needs case reference, not phone or full medical record.
    p=Patient(public_id='PARTNER-'+secrets.token_hex(4).upper(),display_name=data.reference,
              phone='NOT_COLLECTED',org_id=user.org_id,contact_verified=False,service_consent=False)
    db.add(p);db.flush()
    audit(db,user,'partner.patient_case_registered','patient',p.id)
    db.commit()
    return {'id':p.id,'public_id':p.public_id}


class AppointmentIn(BaseModel):
    patient_id: int
    dentist_id: int
    scheduled_at: AwareDatetime


WIB = timezone(timedelta(hours=7))


def appointment_day(value: datetime) -> date:
    # SQLite returns the UTC column without tzinfo. Shift eligibility is a WIB date.
    return value.replace(tzinfo=timezone.utc).astimezone(WIB).date() if value.tzinfo is None else value.astimezone(WIB).date()


@router.get('/api/appointments')
def appointments(user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'reception','dentist','director','patient')
    rows = db.scalars(select(Appointment).order_by(Appointment.scheduled_at.desc())).all()
    out = []
    for a in rows:
        p = db.get(Patient,a.patient_id)
        if user.role == 'patient' and p.user_id != user.id: continue
        if user.role == 'dentist' and a.dentist_id != user.id and a.pending_dentist_id != user.id: continue
        out.append({'id':a.id,'patient':p.display_name if user.role!='patient' else 'Saya','dentist':db.get(User,a.dentist_id).display_name,'scheduled_at':str(a.scheduled_at),'status':a.status,'pending_dentist_id':a.pending_dentist_id})
    return out


@router.post('/api/appointments')
def create_appointment(data: AppointmentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'reception')
    patient = db.get(Patient,data.patient_id)
    doctor = db.get(User,data.dentist_id)
    if not patient or patient.org_id!=user.org_id or not doctor or not doctor.active or doctor.role!='dentist' or doctor.org_id!=user.org_id:
        raise HTTPException(400,'Pasien atau dokter tidak valid')
    if not db.scalar(select(Shift).where(Shift.user_id==doctor.id,Shift.shift_day==appointment_day(data.scheduled_at),Shift.available==True)):
        raise HTTPException(409,'Dokter tidak bertugas pada tanggal tersebut')
    a=Appointment(patient_id=patient.id,dentist_id=doctor.id,scheduled_at=data.scheduled_at.astimezone(timezone.utc),status='confirmed')
    db.add(a);db.flush();audit(db,user,'appointment.created','appointment',a.id)
    db.commit();return {'id':a.id,'status':a.status}


class ReplacementIn(BaseModel):
    dentist_id: int


@router.post('/api/appointments/{aid}/replacement')
def replacement(aid: int, data: ReplacementIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'reception')
    a=db.get(Appointment,aid);target=db.get(User,data.dentist_id)
    if not a or not target or not target.active or target.org_id!=user.org_id or target.role!='dentist' or target.id==a.dentist_id:
        raise HTTPException(400,'Penggantian tidak valid')
    if not db.scalar(select(Shift).where(Shift.user_id==target.id,Shift.shift_day==appointment_day(a.scheduled_at),Shift.available==True)):
        raise HTTPException(409,'Dokter pengganti tidak tersedia')
    a.pending_dentist_id=target.id;a.status='awaiting_patient'
    audit(db,user,'appointment.replacement_requested','appointment',a.id,candidate=target.id)
    db.commit();return {'status':a.status}




@router.post('/api/appointments/{aid}/respond')
def appointment_response(aid: int, data: DecisionIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'patient')
    a=db.get(Appointment,aid)
    if not a or db.get(Patient,a.patient_id).user_id != user.id:
        raise HTTPException(404,'Jadwal tidak ditemukan')
    if a.status!='awaiting_patient' or not a.pending_dentist_id:
        raise HTTPException(409,'Tidak ada perubahan yang perlu disetujui')
    if data.approved: a.dentist_id=a.pending_dentist_id
    a.pending_dentist_id=None;a.status='confirmed' if data.approved else 'replacement_rejected'
    audit(db,user,'appointment.replacement_responded','appointment',a.id,approved=data.approved)
    db.commit();return {'status':a.status}
