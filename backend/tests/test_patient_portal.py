"""Independent patient UI/session, minimal data, ownership and patient-only support."""
from datetime import date, timedelta
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from backend import database
from backend.models import Audit, Appointment, LabOrder, Notification, Patient, User, UserSession
from backend.tests.test_api import appmod, client, login, post, assign_and_accept
from backend.utils import pwd_hash


def patient_login(c, username='DEMO-P-001'):
    r=c.post('/api/patient/login',json={'username':username,'password':'DemoNAM2026!'})
    assert r.status_code==200,r.text
    return {'X-CSRF-Token':r.json()['csrf']}


def test_portal_has_independent_bundle_and_no_employee_account_picker(client):
    page=client.get('/pasien')
    assert page.status_code==200 and '/static/portal.js' in page.text
    assert '/static/app.js' not in page.text and '/static/sop.js' not in page.text
    script=client.get('/static/portal.js').text
    assert 'Akun divisi' not in script and 'roleNames' not in script
    assert '/organization' not in script and '/sop-reports' not in script
    assert 'Akun divisi' not in client.get('/static/app.js').text


def test_separate_sessions_csrf_and_logout(client):
    staff=login(client,'it')
    patient=patient_login(client)
    assert set(client.get('/api/patient/me').json())=={'name','reference','csrf'}
    assert client.get('/api/me').json()['role']=='it_admin'
    assert client.post('/api/patient/logout').status_code==403
    assert client.post('/api/patient/logout',headers=staff).status_code==403
    assert client.post('/api/patient/logout',headers=patient).status_code==200
    assert client.get('/api/patient/me').status_code==401
    assert client.get('/api/me').json()['role']=='it_admin'


@pytest.mark.parametrize('name',['resepsionis','dokter','lab','teknisi','qc','fat','direktur','mitra','it','perawat','cadcam','cs','gudang','purchasing','hr','marketing','dokter2','lab2'])
def test_nonpatients_cannot_log_into_patient_portal_or_start_personal_chat(client,name):
    assert client.post('/api/patient/login',json={'username':name,'password':'DemoNAM2026!'}).status_code==403
    h=login(client,name)
    assert client.get('/api/patient/orders').status_code==401
    post(client,'/api/chat/conversations',h,{'request_id':'not-a-patient-0001'},403)
    assert client.get('/api/chat/conversations').status_code==403


def test_patient_cannot_enter_workspace_login_or_staff_apis(client):
    assert client.post('/api/workspace/login',json={'username':'pasien','password':'DemoNAM2026!'}).status_code==403
    h=patient_login(client)
    for path in ('/api/me','/api/organization','/api/sop-reports','/api/training','/api/chat/queue','/api/admin/audits'):
        assert client.get(path).status_code==401
    # Audience is enforced even when a cookie is manually copied to the other name.
    token=client.cookies.get('nam_patient_session')
    other=TestClient(appmod.app);other.cookies.set('nam_session',token)
    assert other.get('/api/me').status_code==401
    other.close()
    staff=TestClient(appmod.app);login(staff,'it')
    other=TestClient(appmod.app);other.cookies.set('nam_patient_session',staff.cookies.get('nam_session'),path='/api/patient')
    assert other.get('/api/patient/me').status_code==401
    staff.close();other.close()
    post(client,'/api/patient/chat/conversations',h,{'request_id':'valid-portal-0001'})
    login(client,'pasien')
    legacy=client.get('/api/orders/1').json()['order']
    assert not {'lead_id','technician_id','customer','instruction'} & set(legacy)


@pytest.mark.parametrize('invalid',['tenant','unlinked','inactive'])
def test_invalid_patient_account_is_denied(client,invalid):
    with database.SessionLocal() as db:
        user=db.get(User,9)
        if invalid=='tenant':user.org_id=2
        if invalid=='unlinked':db.get(Patient,1).user_id=None
        if invalid=='inactive':user.active=False
        db.commit()
    r=client.post('/api/patient/login',json={'username':'pasien','password':'DemoNAM2026!'})
    assert r.status_code in (401,403)
    assert not client.cookies.get('nam_patient_session')


def test_patient_service_data_is_minimal_and_ownership_checked(client):
    patient_login(client)
    orders=client.get('/api/patient/orders').json()
    assert [o['id'] for o in orders]==[1]
    assert not set(orders[0]) & {'title','instruction','lead_id','technician_id','org_id','customer','patient_ref'}
    assert client.get('/api/patient/orders/2').status_code==404
    detail=client.get('/api/patient/orders/1').json()
    assert 'history' in detail and all('actor' not in h for h in detail['history'])
    with database.SessionLocal() as db:
        other=User(username='patient2',display_name='Pasien Lain Fiktif',role='patient',org_id=1,password_hash=pwd_hash('DemoNAM2026!'),active=True)
        db.add(other);db.flush()
        db.add(Patient(id=3,public_id='DEMO-P-003',display_name='Pasien Lain Fiktif',phone='00000000',org_id=1,user_id=other.id))
        db.add(Notification(patient_id=1,org_id=2,order_id=1,channel='portal',kind='test',message='Tenant salah',status='queued'))
        db.commit()
    assert 'Tenant salah' not in client.get('/api/patient/notifications').text
    h=patient_login(client,'patient2')
    assert client.get('/api/patient/orders').json()==[]
    assert client.get('/api/patient/orders/1').status_code==404
    post(client,'/api/patient/appointments/1/respond',h,{'approved':True},404)
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='patient_portal.service_viewed'))==1


def test_delay_response_state_scope_and_audit(client):
    h=assign_and_accept(client)
    due=str(date.today()+timedelta(days=16))
    post(client,'/api/orders/1/delay',h,{'new_due':due,'reason':'Simulasi waktu tambahan'})
    patient=patient_login(client)
    assert client.get('/api/patient/orders/1').json()['delay_response']=='pending'
    post(client,'/api/patient/orders/2/delay/respond',patient,{'approved':True,'expected_due':due},404)
    post(client,'/api/patient/orders/1/delay/respond',patient,{'approved':True,'expected_due':str(date.today())},409)
    data={'approved':True,'expected_due':due}
    assert client.post('/api/patient/orders/1/delay/respond',json=data,headers={**patient,'Origin':'https://elsewhere.invalid'}).status_code==403
    post(client,'/api/patient/orders/1/delay/respond',patient,data)
    post(client,'/api/patient/orders/1/delay/respond',patient,data,409)
    with database.SessionLocal() as db:
        assert str(db.get(LabOrder,1).promised_due)==due
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='lab_order.delay_decided'))==1


def test_replacement_patient_view_hides_employee_ids_and_requires_live_state(client):
    staff=login(client,'resepsionis')
    post(client,'/api/appointments/1/replacement',staff,{'dentist_id':11})
    h=patient_login(client)
    a=client.get('/api/patient/appointments').json()[0]
    assert a['proposed_dentist']=='Dokter Klinik 2 Demo'
    assert 'pending_dentist_id' not in a and 'patient' not in a
    post(client,'/api/patient/appointments/1/respond',h,{'approved':True})
    post(client,'/api/patient/appointments/1/respond',h,{'approved':True},409)


def test_patient_chat_handoff_idempotency_and_operator_inbox(client):
    h=patient_login(client)
    payload={'request_id':'portal-conversation-001','order_id':1}
    c=post(client,'/api/patient/chat/conversations',h,payload)
    assert post(client,'/api/patient/chat/conversations',h,payload)['id']==c['id']
    path='/api/patient/chat/conversations/'+c['id']
    msg={'request_id':'portal-message-001','body':'Bagaimana jadwal kunjungan saya?'}
    post(client,path+'/messages',h,msg)
    assert post(client,path+'/messages',h,msg)['duplicate']
    assert 'Front Office' not in client.get(path).text and 'Pasien & jadwal' not in client.get(path).text
    post(client,path+'/handoff',h);post(client,path+'/handoff',h)
    cs=login(client,'cs');base='/api/chat/conversations/'+c['id']
    assert client.get('/api/chat/queue').json()[0]['id']==c['id']
    post(client,base+'/claim',cs)
    post(client,base+'/messages',cs,{'request_id':'operator-reply-001','body':'Kami bantu periksa jadwal latihan Anda.'})
    assert client.get(path).json()['messages'][-1]['sender']=='agent'
    post(client,path+'/close',h);post(client,path+'/close',h)
    post(client,path+'/messages',h,{'request_id':'closed-message-001','body':'Pesan baru'},409)
    with database.SessionLocal() as db:
        for event in ('chat.started','chat.handoff_requested','chat.claimed','chat.closed'):
            assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event==event))==1


def test_training_role_scope_repeat_read_and_audit(client):
    h=login(client,'it')
    catalog=client.get('/api/training').json()
    assert catalog['draft'] and catalog['divisions']
    code=catalog['modules'][0]['code']
    a=client.get('/api/training/'+code).json()
    assert client.get('/api/training/'+code).json()==a
    assert a['steps'] and a['evidence_examples'] and 'kewenangan' in a['review']
    assert client.get('/api/training/LAB-01').status_code==404
    assert client.get('/api/orders/1').status_code==404
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='training.opened'))==2
        db.get(User,10).org_id=2;db.commit()
    assert client.get('/api/training').status_code==403
    for name in ('pasien','mitra'):
        login(client,name)
        assert client.get('/api/training').status_code==403


def test_session_migration_preserves_legacy_values_and_is_repeatable(client):
    with database.engine.begin() as connection:
        for table in ('whatsapp_outbox','visit_timings','patient_notice_reads','patient_updates','patient_visit_details'):
            connection.execute(text('DROP TABLE '+table))
        connection.execute(text('ALTER TABLE sessions DROP COLUMN audience'))
        connection.execute(text("UPDATE alembic_version SET version_num='0003'"))
        connection.execute(text("INSERT INTO sessions (token_hash,csrf_token_hash,user_id,expires_at) VALUES (:t,:c,10,'2099-01-01 00:00:00')"),{'t':'a'*64,'c':'b'*64})
    database.upgrade_schema();database.upgrade_schema()
    with database.SessionLocal() as db:
        session=db.scalar(select(UserSession).where(UserSession.token_hash=='a'*64))
        assert session.audience=='workspace' and session.user_id==10
