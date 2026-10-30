"""Conservative service forecasts. Actual completion is always recorded by a doctor."""
import csv
import io
import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Appointment, Patient, PatientUpdate, Shift, User, VisitTiming, WhatsappOutbox
from backend.modules.audit import audit
from backend.modules.patient_visits import WIB, doctor_for, lock_patient, utc
from backend.security import current_user, role_only
from backend.utils import utcnow
from backend.workflow import dumps, finish, replay

router=APIRouter(tags=['Perkiraan kunjungan'])

def iso(value):return utc(value).isoformat() if value else None

def queue_map(db,doctor_id,org_id,day,now=None):
    now=now or utcnow()
    lo=datetime.combine(day,time.min,WIB).astimezone(timezone.utc);hi=lo+timedelta(days=1)
    same_day=and_(Appointment.scheduled_at>=lo,Appointment.scheduled_at<hi)
    # An unfinished visit from yesterday is uncertain today, never silently finished.
    include=or_(same_day,VisitTiming.state=='in_service',and_(VisitTiming.finished_at>=lo,VisitTiming.finished_at<hi)) if day==now.astimezone(WIB).date() else same_day
    rows=db.execute(select(Appointment,VisitTiming).join(Patient,Patient.id==Appointment.patient_id)
        .outerjoin(VisitTiming,and_(VisitTiming.appointment_id==Appointment.id,VisitTiming.org_id==org_id))
        .where(Appointment.dentist_id==doctor_id,Patient.org_id==org_id,include)
        .order_by(Appointment.scheduled_at,Appointment.id)).all()
    active=[(a,t) for a,t in rows if a.status!='cancelled' and t and t.state=='in_service']
    running=active[0] if len(active)==1 else None
    cursor=utc(running[1].expected_finish_at) if running and running[1].expected_finish_at else None
    uncertain=bool(active and (len(active)!=1 or not cursor or cursor<=now))
    result={}
    for a,t in rows:
        scheduled=utc(a.scheduled_at);state=t.state if t else 'not_started'
        start=end=None
        if a.status=='cancelled':state='cancelled'
        elif state=='finished':
            start=utc(t.started_at);end=utc(t.finished_at)
            if end:cursor=max(cursor,end) if cursor else end
            if not active and end:uncertain=False
        elif state=='not_attended':pass
        elif state=='in_service':
            start=utc(t.started_at)
            end=utc(t.expected_finish_at) if t.expected_finish_at and utc(t.expected_finish_at)>now else None
            if not end:state='needs_update'
        elif a.status=='awaiting_patient':state='awaiting_confirmation'
        elif running and (scheduled,a.id)<(utc(running[0].scheduled_at),running[0].id):
            state='needs_update' # An older, unstarted visit needs a staff decision.
        elif uncertain:state='needs_update'
        else:
            start=max(scheduled,cursor) if cursor else scheduled
            if day<=now.astimezone(WIB).date() and start<now:
                start=None;uncertain=True;state='needs_update'
            else:
                end=start+timedelta(minutes=30);cursor=end
        delay=max(0,math.ceil((start-scheduled).total_seconds()/60)) if start else None
        result[a.id]={'state':state,'estimated_start_at':iso(start),'estimated_end_at':iso(end),
            'delay_minutes':delay,'started_at':iso(t.started_at) if t else None,
            'finished_at':iso(t.finished_at) if t else None,'revision':t.revision if t else 0,
            'updated_at':iso(t.updated_at) if t else None,
            'note':'Perkiraan dapat berubah. Jadwal awal tetap tersimpan; hubungi petugas sebelum mengubah waktu kedatangan.'}
    return result

def forecast(db,row,org_id,now=None):
    return queue_map(db,row.dentist_id,org_id,utc(row.scheduled_at).astimezone(WIB).date(),now).get(row.id)

def timing_active(db,aid):
    row=db.get(VisitTiming,aid)
    return bool(row and row.state!='not_started')

class TimingIn(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    action:Literal['start','estimate','finish','not_attended']
    minutes:int|None=Field(default=None,ge=5,le=180)
    reason:str=Field(min_length=5,max_length=300)
    expected_revision:int=Field(ge=0)
    request_key:str=Field(min_length=12,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')

def publish(db,rows,before,after):
    for a in rows:
        previous,current=before.get(a.id),after.get(a.id)
        if not current or current==previous or a.status=='cancelled':continue
        # Revision timestamps alone do not create duplicate patient messages.
        fields=('state','estimated_start_at','estimated_end_at')
        if previous and all(previous[k]==current[k] for k in fields):continue
        if current['state']=='finished':message='Kunjungan Anda telah ditandai selesai oleh dokter.'
        elif current['state']=='not_attended':message='Petugas mencatat Anda belum hadir pada jadwal ini. Hubungi klinik untuk tindak lanjut.'
        elif not current['estimated_end_at']:
            message='Perkiraan waktu kunjungan Anda perlu diperbarui petugas. Silakan periksa portal atau hubungi klinik sebelum berangkat.'
        else:
            stamp=lambda value:datetime.fromisoformat(value).astimezone(WIB).strftime('%d/%m/%Y %H.%M WIB')
            message=f"Perkiraan mulai kunjungan Anda {stamp(current['estimated_start_at'])}, selesai {stamp(current['estimated_end_at'])}. Waktu dapat berubah; jadwal awal tidak diganti otomatis."
        p=db.get(Patient,a.patient_id)
        notice=PatientUpdate(patient_id=p.id,org_id=p.org_id,appointment_id=a.id,kind='visit_timing',
            title='Pembaruan waktu kunjungan',message=message)
        db.add(notice);db.flush()
        if p.org_id==1 and p.preferred_channel=='whatsapp' and p.contact_verified and p.service_consent:
            # No external calls. Provider credentials and verified opt-in must be set up first.
            db.add(WhatsappOutbox(update_id=notice.id,patient_id=p.id,appointment_id=a.id,org_id=p.org_id,
                template_key='nam_visit_estimate_update',payload=dumps({'message':message}),status='awaiting_configuration'))

@router.post('/api/appointments/{aid}/timing')
def update_timing(aid:int,data:TimingIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'dentist','reception')
    a=db.get(Appointment,aid);p=db.get(Patient,a.patient_id) if a else None
    if not a or not p or p.org_id!=user.org_id or (user.role=='dentist' and a.dentist_id!=user.id):
        raise HTTPException(404,'Kunjungan tidak ditemukan dalam penugasan Anda.')
    if user.role=='reception' and data.action!='not_attended':
        raise HTTPException(403,'Waktu tindakan dan selesai kunjungan dicatat dokter yang menangani.')
    lock_patient(db,p);doctor_for(db,user.org_id,a.dentist_id,locking=True);db.refresh(a)
    fp,prior=replay(db,user,'visit.timing',{**data.model_dump(),'appointment_id':aid})
    if prior is not None:return prior
    now=utcnow();day=utc(a.scheduled_at).astimezone(WIB).date()
    days={day,now.astimezone(WIB).date()} if day<now.astimezone(WIB).date() else {day}
    before={key:value for d in sorted(days) for key,value in queue_map(db,a.dentist_id,user.org_id,d,now).items()}
    t=db.get(VisitTiming,aid)
    if t and t.org_id!=user.org_id:raise HTTPException(404,'Kunjungan tidak ditemukan.')
    if (t.revision if t else 0)!=data.expected_revision:raise HTTPException(409,'Kunjungan telah diperbarui. Muat ulang terlebih dahulu.')
    state=t.state if t else 'not_started'
    if a.status not in ('confirmed','replacement_rejected'):
        raise HTTPException(409,'Konfirmasi jadwal dan dokter harus diselesaikan terlebih dahulu.')
    if data.action in ('start','not_attended') and state!='not_started':
        raise HTTPException(409,'Kunjungan ini sudah diproses.')
    if data.action in ('estimate','finish') and state!='in_service':
        raise HTTPException(409,'Kunjungan belum dimulai atau sudah selesai.')
    if data.action=='start':
        if day!=now.astimezone(WIB).date():raise HTTPException(409,'Kunjungan hanya dapat dimulai pada hari jadwalnya.')
        shift=db.scalar(select(Shift).where(Shift.user_id==a.dentist_id,Shift.shift_day==day,Shift.available==True))
        if not shift:raise HTTPException(409,'Dokter tidak tercatat bertugas hari ini.')
        busy=db.scalar(select(VisitTiming).join(Appointment,Appointment.id==VisitTiming.appointment_id).where(
            Appointment.dentist_id==a.dentist_id,VisitTiming.org_id==user.org_id,VisitTiming.state=='in_service'))
        if busy:raise HTTPException(409,'Selesaikan kunjungan yang masih berlangsung terlebih dahulu.')
    if data.action=='not_attended' and utc(a.scheduled_at)>now:
        raise HTTPException(409,'Jadwal mendatang belum dapat ditandai tidak hadir.')
    if data.action=='estimate' and data.minutes is None:raise HTTPException(422,'Isi perkiraan menit tersisa.')
    if data.action in ('finish','not_attended') and data.minutes is not None:raise HTTPException(422,'Tindakan ini tidak memakai perkiraan menit.')
    if not t:t=VisitTiming(appointment_id=aid,org_id=user.org_id,revision=0);db.add(t)
    if data.action=='start':
        t.state='in_service';t.started_at=now;t.expected_finish_at=now+timedelta(minutes=data.minutes or 30)
    elif data.action=='estimate':t.expected_finish_at=now+timedelta(minutes=data.minutes)
    elif data.action=='finish':t.state='finished';t.finished_at=now
    else:t.state='not_attended'
    t.revision+=1;t.updated_at=now;db.flush()
    after={key:value for d in sorted(days) for key,value in queue_map(db,a.dentist_id,user.org_id,d,now).items()}
    rows=db.scalars(select(Appointment).join(Patient,Patient.id==Appointment.patient_id).where(
        Appointment.id.in_(tuple(after)),Patient.org_id==user.org_id)).all()
    publish(db,rows,before,after)
    audit(db,user,'visit.'+data.action,'appointment',aid,reason=data.reason,minutes=data.minutes,revision=t.revision,
        scheduled_at=iso(a.scheduled_at),started_at=iso(t.started_at),finished_at=iso(t.finished_at),expected_finish_at=iso(t.expected_finish_at))
    return finish(db,user,data.request_key,fp,{'id':aid,'timing':after[aid]})

@router.get('/api/appointments/timing-report')
def timing_report(day:date,format:Literal['json','csv']='json',user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'dentist','reception','director')
    lo=datetime.combine(day,time.min,WIB).astimezone(timezone.utc);hi=lo+timedelta(days=1)
    query=select(Appointment,VisitTiming).join(Patient,Patient.id==Appointment.patient_id).outerjoin(
        VisitTiming,and_(VisitTiming.appointment_id==Appointment.id,VisitTiming.org_id==user.org_id)).where(
        Patient.org_id==user.org_id,Appointment.scheduled_at>=lo,Appointment.scheduled_at<hi)
    if user.role=='dentist':query=query.where(Appointment.dentist_id==user.id)
    rows=[]
    for a,t in db.execute(query.order_by(Appointment.scheduled_at,Appointment.id)):
        wait=max(0,round((utc(t.started_at)-utc(a.scheduled_at)).total_seconds()/60,1)) if t and t.started_at else None
        duration=round((utc(t.finished_at)-utc(t.started_at)).total_seconds()/60,1) if t and t.finished_at and t.started_at else None
        rows.append({'kunjungan':a.id,'jadwal_utc':iso(a.scheduled_at),'mulai_utc':iso(t.started_at) if t else None,
            'selesai_utc':iso(t.finished_at) if t else None,'keterlambatan_mulai_menit':wait,'durasi_aktual_menit':duration,
            'status':('cancelled' if a.status=='cancelled' else t.state if t else 'not_started')})
    audit(db,user,'visit.timing_report_exported' if format=='csv' else 'visit.timing_report_viewed','user',user.id,day=str(day),count=len(rows));db.commit()
    if format=='json':return {'day':str(day),'timezone':'UTC','rows':rows,'note':'Waktu aktual berasal dari pencatatan dokter, bukan jaminan durasi klinis.'}
    output=io.StringIO();writer=csv.DictWriter(output,fieldnames=('kunjungan','jadwal_utc','mulai_utc','selesai_utc','keterlambatan_mulai_menit','durasi_aktual_menit','status'))
    writer.writeheader();writer.writerows(rows)
    return Response(('\ufeff'+output.getvalue()).encode('utf-8'),media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition':f'attachment; filename="NAM-Waktu-Kunjungan-{day}.csv"'})

@router.get('/api/whatsapp/status')
def whatsapp_status(user:User=Depends(current_user)):
    role_only(user,'reception','customer_service','director','it_admin')
    return {'enabled':False,'status':'awaiting_configuration','message':'WhatsApp belum aktif. Pesan belum dikirim.',
        'required':['Nomor WhatsApp Business API','Penyedia layanan','Template notifikasi yang disetujui','Kredensial melalui secret environment','Kontak dan izin penerima tervalidasi']}

@router.get('/api/whatsapp/outbox')
def whatsapp_outbox(user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'reception','customer_service')
    rows=db.execute(select(WhatsappOutbox,PatientUpdate).join(PatientUpdate,PatientUpdate.id==WhatsappOutbox.update_id)
        .join(Patient,Patient.id==WhatsappOutbox.patient_id).join(Appointment,Appointment.id==WhatsappOutbox.appointment_id)
        .where(WhatsappOutbox.org_id==user.org_id,Patient.org_id==user.org_id,PatientUpdate.org_id==user.org_id,
            PatientUpdate.patient_id==Patient.id,Appointment.patient_id==Patient.id,
            PatientUpdate.appointment_id==Appointment.id).order_by(WhatsappOutbox.id.desc()).limit(100)).all()
    return [{'id':o.id,'appointment_id':o.appointment_id,'status':o.status,'message':n.message,'created_at':iso(o.created_at)} for o,n in rows]
