"""Forecasts never reveal other patients or silently finish clinical visits."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,time,timedelta,timezone
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func,select
from backend import database
from backend.models import Appointment,Audit,Patient,PatientUpdate,User,VisitTiming,WhatsappOutbox
from backend.modules import visit_queue as queue
from backend.modules.patient_visits import WIB
from backend.tests.test_api import appmod,client,login,post
from backend.tests.test_patient_portal import patient_login
from backend.tests.test_patient_visits import add_patient
from backend.utils import utcnow

@pytest.fixture()
def schedule(client,monkeypatch):
    day=utcnow().astimezone(WIB).date()
    clock=[datetime.combine(day,time(9),WIB).astimezone(timezone.utc)]
    monkeypatch.setattr(queue,'utcnow',lambda:clock[0])
    _,pid=add_patient()
    with database.SessionLocal() as db:
        db.get(Patient,pid).display_name='OTHER-PATIENT-PRIVATE'
        a=Appointment(patient_id=1,dentist_id=2,scheduled_at=clock[0],status='confirmed')
        b=Appointment(patient_id=pid,dentist_id=2,scheduled_at=clock[0]+timedelta(minutes=30),status='confirmed')
        db.add_all([a,b]);db.commit()
        return a.id,b.id,pid,clock

def command(action,rev=0,minutes=None,**extra):
    return {'action':action,'expected_revision':rev,'minutes':minutes,'reason':'Catatan waktu pengujian fiktif',
            'request_key':uuid.uuid4().hex,**extra}

def timing(c,h,aid,body,status=200):return post(c,f'/api/appointments/{aid}/timing',h,body,status)

def test_forecast_lifecycle_and_private_notifications_and_report(client,schedule):
    a,b,pid,clock=schedule;h=login(client,'dokter');start=command('start',minutes=45)
    first=timing(client,h,a,start)
    assert timing(client,h,a,start)==first
    patient_login(client,'another')
    rows=client.get('/api/patient/appointments').json();own=next(r for r in rows if r['id']==b)
    assert own['timing']['delay_minutes']==15
    assert datetime.fromisoformat(own['timing']['estimated_start_at'])==clock[0]+timedelta(minutes=45)
    assert datetime.fromisoformat(own['timing']['estimated_end_at'])==clock[0]+timedelta(minutes=75)
    assert not {'patient_id','previous_patient','doctor_notes'}&set(own['timing'])
    notices=client.get('/api/patient/notifications').json()
    assert len(notices)==1 and all(n['appointment_id']==b for n in notices)
    clock[0]+=timedelta(minutes=50)
    timing(client,h,a,command('finish',rev=1))
    next_visit=next(r for r in client.get('/api/patient/appointments').json() if r['id']==b)
    assert next_visit['timing']['delay_minutes']==20
    assert datetime.fromisoformat(next_visit['scheduled_at'])==clock[0]-timedelta(minutes=20)
    report=client.get('/api/appointments/timing-report',params={'day':str(clock[0].astimezone(WIB).date())}).json()
    assert next(r for r in report['rows'] if r['kunjungan']==a)['durasi_aktual_menit']==50
    exported=client.get('/api/appointments/timing-report',params={'day':report['day'],'format':'csv'})
    assert exported.status_code==200 and 'attachment' in exported.headers['content-disposition']
    assert 'OTHER-PATIENT-PRIVATE' not in exported.text
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='visit.start'))==1
        assert db.get(Appointment,b).scheduled_at.replace(tzinfo=timezone.utc)==clock[0]-timedelta(minutes=20)

def test_overtime_needs_update_and_revised_estimate(client,schedule):
    a,b,_,clock=schedule;h=login(client,'dokter')
    timing(client,h,a,command('start',minutes=30))
    clock[0]+=timedelta(minutes=31)
    patient_login(client,'another')
    own=next(r for r in client.get('/api/patient/appointments').json() if r['id']==b)
    assert own['timing']['estimated_start_at'] is None and own['timing']['state']=='needs_update'
    timing(client,h,a,command('estimate',rev=1,minutes=15))
    own=next(r for r in client.get('/api/patient/appointments').json() if r['id']==b)
    assert own['timing']['delay_minutes']==16 and own['timing']['estimated_end_at']
    assert all('OTHER-PATIENT-PRIVATE' not in n['message'] for n in client.get('/api/patient/notifications').json())

@pytest.mark.parametrize('name',['resepsionis','it','direktur','lab','qc','fat','cs','mitra','pasien'])
def test_only_assigned_doctor_records_service_times(client,schedule,name):
    a,_,_,_=schedule;h=login(client,name)
    timing(client,h,a,command('start'),403)
    if name not in ('resepsionis','direktur'):
        assert client.get('/api/appointments/timing-report?day=2026-10-30').status_code==403

def test_scope_csrf_and_state_guards(client,schedule):
    a,b,_,clock=schedule;h=login(client,'dokter2')
    timing(client,h,a,command('start'),404)
    h=login(client,'dokter')
    assert client.post(f'/api/appointments/{a}/timing',json=command('start')).status_code==403
    timing(client,h,a,command('finish'),409)
    timing(client,h,a,command('start',minutes=2),422)
    timing(client,h,a,command('start',patient_id=1),422)
    start=command('start',minutes=30);timing(client,h,a,start)
    timing(client,h,a,{**start,'minutes':45},409)
    timing(client,h,a,command('estimate',rev=0,minutes=15),409)
    timing(client,h,b,command('start'),409)
    timing(client,h,a,command('finish',rev=1))
    timing(client,h,a,command('start',rev=2),409)
    with database.SessionLocal() as db:
        db.get(User,2).org_id=2;db.commit()
    timing(client,h,b,command('start'),403)

def test_no_show_and_started_visit_cannot_be_cancelled_or_reassigned(client,schedule):
    a,b,_,clock=schedule;h=login(client,'resepsionis')
    timing(client,h,b,command('not_attended'),409)
    timing(client,h,a,command('not_attended'))
    doctor=login(client,'dokter');timing(client,doctor,a,command('start',rev=1),409)
    with database.SessionLocal() as db:
        db.get(Appointment,b).patient_id=1;db.commit()
    timing(client,doctor,b,command('start',minutes=45)) # Clinician explicitly starts an early, same-day visit.
    h=login(client,'resepsionis')
    timing(client,h,b,command('not_attended',rev=1),409)
    patient=patient_login(client)
    assert not next(r for r in client.get('/api/patient/appointments').json() if r['id']==b)['can_cancel']
    post(client,f'/api/patient/appointments/{b}/cancel',patient,{'reason':'Tes pembatalan','request_key':uuid.uuid4().hex},409)
    post(client,f'/api/appointments/{b}/replacement',h,{'dentist_id':11},409)

def test_concurrent_starts_only_one_active_visit(client,schedule):
    a,b,_,_=schedule;h=login(client,'dokter');other=TestClient(appmod.app);other.cookies.update(client.cookies)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs=[pool.submit(c.post,f'/api/appointments/{aid}/timing',json=command('start'),headers=h) for c,aid in ((client,a),(other,b))]
        assert sorted(f.result().status_code for f in fs)==[200,409]
    other.close()
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(VisitTiming).where(VisitTiming.state=='in_service'))==1

@pytest.mark.parametrize('preference,consent,verified,expected',[
    ('portal',True,True,0),('whatsapp',False,True,0),('whatsapp',True,False,0),('whatsapp',True,True,2)])
def test_whatsapp_preparation_never_sends_and_preserves_consent(client,schedule,preference,consent,verified,expected):
    a,b,pid,_=schedule
    with database.SessionLocal() as db:
        for ident in (1,pid):
            p=db.get(Patient,ident);p.preferred_channel=preference;p.service_consent=consent;p.contact_verified=verified
        db.commit()
    h=login(client,'dokter');body=command('start',minutes=45)
    timing(client,h,a,body);timing(client,h,a,body)
    with database.SessionLocal() as db:
        rows=db.scalars(select(WhatsappOutbox)).all()
        assert len(rows)==expected and all(r.status=='awaiting_configuration' for r in rows)
    login(client,'resepsionis')
    assert len(client.get('/api/whatsapp/outbox').json())==expected
    assert not client.get('/api/whatsapp/status').json()['enabled']
    login(client,'it');assert client.get('/api/whatsapp/outbox').status_code==403

def test_foreign_rows_cannot_affect_eta_or_outbox(client,schedule):
    a,b,_,clock=schedule
    with database.SessionLocal() as db:
        bad=Appointment(patient_id=2,dentist_id=2,scheduled_at=clock[0]-timedelta(minutes=10),status='confirmed')
        db.add(bad);db.commit();bad_id=bad.id
    h=login(client,'dokter');timing(client,h,bad_id,command('start'),404)
    timing(client,h,a,command('start',minutes=30))
    patient_login(client,'another')
    own=next(r for r in client.get('/api/patient/appointments').json() if r['id']==b)
    assert own['timing']['delay_minutes']==0

def test_future_day_no_stale_carry_and_no_unconfirmed_start(client,schedule):
    a,b,_,clock=schedule
    with database.SessionLocal() as db:
        row=db.get(Appointment,b);row.scheduled_at=clock[0]+timedelta(days=1);db.commit()
    h=login(client,'dokter');timing(client,h,b,command('start'),409)
    timing(client,h,a,command('start',minutes=30));clock[0]+=timedelta(minutes=31)
    patient_login(client,'another')
    own=next(r for r in client.get('/api/patient/appointments').json() if r['id']==b)
    assert own['timing']['state']=='not_started' and own['timing']['delay_minutes']==0
    with database.SessionLocal() as db:
        db.get(Appointment,b).status='awaiting_patient';db.commit()
    timing(client,h,b,command('start'),409)
