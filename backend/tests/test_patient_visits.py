"""Patient self-service: shared slots, private inbox, receipts and clinical boundaries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta, timezone
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from backend import database
from backend.models import Appointment, Audit, LabOrder, Notification, Org, Patient, PatientNoticeRead, PatientUpdate, Shift, User, VisitDetails
from backend.modules.communication import queue_notice
from backend.modules.patient_visits import WIB
from backend.runtime import DemoRuntime
from backend.tests.test_api import appmod, client, login, post, assign_and_accept
from backend.tests.test_patient_portal import patient_login
from backend.utils import pwd_hash, utcnow


def payload(offset=1, hour=9, doctor=2, **extra):
    day=utcnow().astimezone(WIB).date()+timedelta(days=offset)
    return {'doctor_id':doctor,'scheduled_at':datetime.combine(day,time(hour),WIB).isoformat(),
            'request_key':f'patient-book-{offset}-{hour}-{doctor}',**extra}


def add_patient(org=1):
    with database.SessionLocal() as db:
        if not db.get(Org,org): db.add(Org(id=org,name='Autre clinique fictive',kind='internal'));db.flush()
        u=User(username='another',display_name='Pasien Tambahan Demo',role='patient',org_id=org,
               active=True,password_hash=pwd_hash('DemoNAM2026!'))
        db.add(u);db.flush()
        p=Patient(public_id='DEMO-P-X',display_name=u.display_name,phone='0000000000',org_id=org,user_id=u.id)
        db.add(p);db.commit();return u.id,p.id


def test_booking_doctor_visibility_receipts_and_clinic_connection(client):
    h=patient_login(client)
    assert {d['id'] for d in client.get('/api/patient/doctors').json()}=={2,11}
    body=payload(interest='braces')
    day=body['scheduled_at'][:10]
    slots=client.get(f'/api/patient/appointment-slots?doctor_id=2&day={day}').json()
    assert len(slots['slots'])==16 and slots['timezone']=='Asia/Jakarta'
    result=post(client,'/api/patient/appointments',h,body)
    assert post(client,'/api/patient/appointments',h,body)==result
    post(client,'/api/patient/appointments',h,{**body,'interest':'scaling'},409)
    post(client,'/api/patient/appointments',h,{**body,'request_key':'new-key-same-slot'},409)
    assert not client.get(f'/api/patient/appointment-slots?doctor_id=2&day={day}').json()['slots'][0]['available']
    visits=client.get('/api/patient/appointments').json()
    visit=next(a for a in visits if a['id']==result['id'])
    assert visit['interest']=='braces' and visit['can_cancel'] and visit['scheduled_at'].endswith('+00:00')
    login(client,'dokter')
    assert result['id'] in {a['id'] for a in client.get('/api/appointments').json()}
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='patient.appointment_booked'))==1
        assert db.scalar(select(func.count()).select_from(PatientUpdate))==1
        assert db.scalar(select(func.count()).select_from(VisitDetails))==1


@pytest.mark.parametrize('extra,status',[
    ({'offset':0},422),({'offset':31},422),({'hour':8},422),({'hour':17},422),
    ({'doctor':3},404),({'doctor':99999},404),({'org_id':2},422),
    ({'patient_id':2},422),({'scheduled_at':'2026-10-22T09:00:00'},422),
    ({'purpose':'fitting'},409),({'order_id':2},404),({'order_id':1,'doctor':11},409),
])
def test_booking_rejects_invalid_time_scope_clinical_choice(client,extra,status):
    h=patient_login(client)
    post(client,'/api/patient/appointments',h,payload(**extra),status)
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(VisitDetails))==0


def test_csrf_audience_tenant_shift_and_fitting_gate(client):
    login(client,'resepsionis')
    assert client.get('/api/patient/doctors').status_code==401
    assert client.post('/api/patient/appointments',json=payload()).status_code==401
    h=patient_login(client)
    assert client.post('/api/patient/appointments',json=payload()).status_code==403
    assert client.post('/api/patient/appointments',json=payload(),headers={**h,'Origin':'https://foreign.invalid'}).status_code==403
    post(client,'/api/patient/appointments',h,payload(order_id=1,purpose='fitting'),409)
    with database.SessionLocal() as db:
        db.get(LabOrder,1).status='ready'
        shift=db.scalar(select(Shift).where(Shift.user_id==2,Shift.shift_day==payload()['scheduled_at'][:10]))
        shift.available=False;db.commit()
    post(client,'/api/patient/appointments',h,payload(order_id=1,purpose='fitting'),409)
    post(client,'/api/patient/appointments',h,payload(offset=2,order_id=1,purpose='fitting'))
    with database.SessionLocal() as db:
        db.get(User,11).org_id=2;db.commit()
    assert {d['id'] for d in client.get('/api/patient/doctors').json()}=={2}
    assert client.get('/api/patient/appointment-slots?doctor_id=11&day='+payload()['scheduled_at'][:10]).status_code==404
    post(client,'/api/patient/appointments',h,payload(doctor=11),404)
    add_patient(org=3)
    assert client.post('/api/patient/login',json={'username':'another','password':'DemoNAM2026!'}).status_code==403


def test_shared_reservations_reception_overlap_pending_replacement_and_cancel(client):
    h=patient_login(client);body=payload()
    visit=post(client,'/api/patient/appointments',h,body)
    post(client,'/api/patient/appointments',h,payload(doctor=11),409) # Same patient, different doctor.
    reception=login(client,'resepsionis')
    post(client,'/api/appointments',reception,{'patient_id':1,'dentist_id':2,'scheduled_at':body['scheduled_at']},409)
    post(client,f"/api/appointments/{visit['id']}/replacement",reception,{'dentist_id':11})
    add_patient();other=patient_login(client,'another')
    post(client,'/api/patient/appointments',other,payload(doctor=11),409) # Pending candidate is reserved.
    post(client,f"/api/patient/appointments/{visit['id']}/cancel",other,{'reason':'Tidak bisa hadir','request_key':'foreign-cancel-key'},404)
    h=patient_login(client)
    cancel={'reason':'Ada perubahan jadwal pribadi','request_key':'cancel-first-visit'}
    path=f"/api/patient/appointments/{visit['id']}/cancel"
    assert post(client,path,h,cancel)['status']=='cancelled'
    post(client,path,h,cancel)
    post(client,path,h,{**cancel,'request_key':'cancel-second-key'})
    post(client,f"/api/patient/appointments/{visit['id']}/respond",h,{'approved':True},409)
    post(client,'/api/patient/appointments',h,{**body,'request_key':'book-after-cancel'})
    with database.SessionLocal() as db:
        assert db.get(Appointment,visit['id']).pending_dentist_id is None
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='patient.appointment_cancelled'))==1


def test_concurrent_patients_cannot_take_same_slot(client):
    add_patient();other=TestClient(appmod.app)
    first=patient_login(client);second=patient_login(other,'another')
    body=payload()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(c.post,'/api/patient/appointments',json=body,headers=h) for c,h in ((client,first),(other,second))]
        assert sorted(f.result().status_code for f in futures)==[200,409]
    other.close()
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(VisitDetails))==1


def test_past_cancellation_and_tenant_staff_list(client):
    with database.SessionLocal() as db:
        db.get(Appointment,1).scheduled_at=utcnow()-timedelta(days=1);db.commit()
    h=patient_login(client)
    post(client,'/api/patient/appointments/1/cancel',h,{'reason':'Jadwal sudah lewat','request_key':'cancel-old-visit'},409)
    with database.SessionLocal() as db:
        db.get(User,1).org_id=2;db.commit()
    login(client,'resepsionis')
    assert client.get('/api/appointments').status_code==403


def test_notifications_private_read_idempotent_and_not_consent(client):
    lab=assign_and_accept(client)
    due=str(utcnow().date()+timedelta(days=16))
    post(client,'/api/orders/1/delay',lab,{'new_due':due,'reason':'Simulasi perubahan jadwal Lab'})
    reception=login(client,'resepsionis');post(client,'/api/appointments/1/replacement',reception,{'dentist_id':11})
    with database.SessionLocal() as db:
        foreign=Notification(patient_id=1,org_id=1,order_id=2,channel='portal',kind='delay',message='FOREIGN',status='queued')
        db.add(foreign);db.flush();foreign_id=foreign.id
        db.add(PatientUpdate(patient_id=1,org_id=2,kind='bad',title='FOREIGN',message='FOREIGN'))
        db.commit()
        original_due=db.get(LabOrder,1).promised_due
    h=patient_login(client)
    rows=client.get('/api/patient/notifications').json()
    assert 'FOREIGN' not in str(rows)
    assert sum(n['requires_action'] for n in rows)==2
    notice=rows[0];path='/api/patient/notifications/'+notice['key']+'/read'
    a=post(client,path,h);assert post(client,path,h)==a
    post(client,f'/api/patient/notifications/service/{foreign_id}/read',h,None,404)
    assert post(client,'/api/patient/notifications/read-all',h)['marked']==len(rows)-1
    assert post(client,'/api/patient/notifications/read-all',h)['marked']==0
    assert all(n['read_at'] for n in client.get('/api/patient/notifications').json())
    with database.SessionLocal() as db:
        assert db.get(LabOrder,1).delay_response=='pending' and db.get(LabOrder,1).promised_due==original_due
        assert db.get(Appointment,1).status=='awaiting_patient'
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='patient.notification_read'))==1
        assert db.scalar(select(func.count()).select_from(PatientNoticeRead))==len(rows)
    add_patient();other=patient_login(client,'another')
    post(client,path,other,None,404)
    assert client.get('/api/patient/notifications').json()==[]


def test_lab_updates_and_minimal_preference_keep_critical_and_partner_messages(client):
    with database.SessionLocal() as db:
        p=db.get(Patient,1);p.notification_level='minimal'
        internal=db.get(LabOrder,1);external=db.get(LabOrder,2)
        queue_notice(db,internal,'progress','ROUTINE')
        queue_notice(db,internal,'ready','CRITICAL')
        db.get(Patient,2).notification_level='minimal'
        queue_notice(db,external,'progress','PARTNER')
        db.commit()
        rows=db.scalars(select(Notification)).all()
        assert {r.message for r in rows}=={'CRITICAL','PARTNER'}
        partner=next(r for r in rows if r.message=='PARTNER')
        assert partner.patient_id is None and partner.org_id==2
    patient_login(client)
    assert [n['message'] for n in client.get('/api/patient/notifications').json()]==['CRITICAL']


def test_direct_migration_url_must_match_authorized_demo():
    common={'hosted':True,'shared_database_enabled':True,'shared_database_url':'postgresql://demo:password@ep-nam-pooler.example/db?sslmode=require'}
    good=DemoRuntime(**common,direct_database_url='postgresql://demo:password@ep-nam.example/db?sslmode=require')
    assert 'ep-nam.example' in good.migration_url()
    for url in ('','postgresql://demo:password@foreign.example/db?sslmode=require','postgresql://demo:password@ep-nam.example/other?sslmode=require'):
        with pytest.raises(RuntimeError):DemoRuntime(**common,direct_database_url=url).migration_url()
