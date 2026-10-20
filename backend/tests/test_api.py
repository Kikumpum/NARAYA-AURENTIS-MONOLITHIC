"""Acceptance tests for demo business controls. Synthetic data only."""
from datetime import date, timedelta
import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

appmod = importlib.import_module('backend.app')
from backend import database
from backend.modules import auth


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path}/test.db', connect_args={'check_same_thread': False})
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(database, 'engine', engine)
    monkeypatch.setattr(database, 'SessionLocal', Session)
    auth._failed_logins.clear()
    with TestClient(appmod.app) as test:
        yield test
    engine.dispose()


def login(c, name):
    response = c.post('/api/login', json={'username': name, 'password': 'DemoNAM2026!'})
    assert response.status_code == 200, response.text
    return {'X-CSRF-Token': response.json()['csrf']}


def post(c, path, csrf, data=None, expected=200):
    r = c.post(path, json=data, headers=csrf)
    assert r.status_code == expected, (path, r.status_code, r.text)
    return r.json()


def assign_and_accept(c):
    head = login(c,'resepsionis')
    post(c, '/api/orders/1/assign-lead', head, {'lead_id': 3})
    head = login(c, 'lab')
    post(c, '/api/orders/1/confirm', head, {'accept': True})
    return head


def test_health_and_login(client):
    assert client.get('/api/health').json()['real_data_allowed'] is False
    assert client.get('/api/orders').status_code == 401
    hdr = login(client,'resepsionis')
    assert client.get('/api/roster').status_code == 200
    assert client.post('/api/daily-reports', json={'summary':'Ada 3 pasien fiktif'}).status_code == 403  # CSRF
    assert post(client,'/api/daily-reports',hdr,{'summary':'Laporan fiktif shift pagi'})['id'] > 0


def test_lab_lifecycle_and_role_split(client):
    hdr=login(client,'resepsionis')
    assert post(client,'/api/orders/1/assign-lead',hdr,{'lead_id':3})['status']=='assigned'
    hdr=login(client,'dokter')
    post(client,'/api/orders/1/confirm',hdr,{'accept':True},expected=403)
    hdr=login(client,'lab')
    assert post(client,'/api/orders/1/confirm',hdr,{'accept':True})['status']=='accepted'
    post(client,'/api/orders/1/plan',hdr,{'technician_id':4,'due':str(date.today()+timedelta(days=12))})
    hdr=login(client,'teknisi')
    assert len(client.get('/api/orders').json())==1
    assert post(client,'/api/orders/1/progress',hdr,{'status':'qc_pending'})['status']=='qc_pending'
    hdr=login(client,'qc')
    assert post(client,'/api/orders/1/qc',hdr,{'passed':True})['status']=='ready'
    hdr=login(client,'pasien')
    assert any(n['kind']=='ready' for n in client.get('/api/notifications').json())


def test_delay_must_be_approved_by_patient(client):
    hdr=assign_and_accept(client)
    post(client,'/api/orders/1/plan',hdr,{'technician_id':4,'due':str(date.today()+timedelta(days=12))})
    new=str(date.today()+timedelta(days=16))
    post(client,'/api/orders/1/delay',hdr,{'new_due':new,'reason':'Antrian produksi tertunda; simulasi'})
    before=client.get('/api/orders').json()[0]
    assert before['promised_due']!=new
    hdr=login(client,'resepsionis')
    post(client,'/api/orders/1/delay/respond',hdr,{'approved':True,'expected_due':new},expected=403)
    hdr=login(client,'pasien')
    assert post(client,'/api/orders/1/delay/respond',hdr,{'approved':True,'expected_due':new})['promised_due']==new


def test_finance_requires_independent_verification(client):
    hdr=login(client,'resepsionis')
    inv=post(client,'/api/invoices',hdr,{'order_id':1,'amount_idr':500000})
    pid=post(client,f"/api/invoices/{inv['id']}/payments",hdr,{'method':'qris','amount_idr':500000,'reference':'ref-qris-demo'})['id']
    post(client,f"/api/invoices/{inv['id']}/payments",hdr,{'method':'qris','amount_idr':500000,'reference':'ref-qris-demo'},expected=409)
    snap=client.get('/api/invoices').json()[0]
    assert snap['paid_idr']==0 and snap['pending_idr']==500000
    post(client,f'/api/payments/{pid}/verify',hdr,expected=403)
    hdr=login(client,'fat')
    post(client,f'/api/payments/{pid}/verify',hdr)
    assert client.get('/api/invoices').json()[0]['status']=='paid'


def test_partner_scoping_and_minimal_patient(client):
    hdr=login(client,'mitra')
    external=client.get('/api/orders').json()
    assert len(external)==1 and external[0]['source']=='external'
    post(client,'/api/orders/1/assign-lead',hdr,{'lead_id':3},expected=403)
    record=post(client,'/api/partner/patients',hdr,{'reference':'CASE-ONLY-42'})
    created=post(client,'/api/orders',hdr,{'patient_id':record['id'],'title':'Crown mitra demo','instruction':'Pekerjaan contoh tanpa identitas pasien','category':'crown'})
    assert created['status']=='submitted'
    orders=client.get('/api/orders').json()
    assert all(x['source']=='external' for x in orders) and len(orders)==2
    hdr=login(client,'pasien')
    assert all(x['source']=='internal' for x in client.get('/api/orders').json())
    hdr=login(client,'it')
    assert client.get('/api/orders').json()==[]
    assert client.get('/api/admin/audits').status_code==403


def test_patient_accepts_dentist_replacement(client):
    hdr=login(client,'resepsionis')
    post(client,'/api/appointments/1/replacement',hdr,{'dentist_id':11})
    hdr=login(client,'pasien')
    assert client.get('/api/appointments').json()[0]['status']=='awaiting_patient'
    assert post(client,'/api/appointments/1/respond',hdr,{'approved':True})['status']=='confirmed'
    assert client.get('/api/appointments').json()[0]['dentist']=='Dokter Klinik 2 Demo'


def test_user_input_does_not_change_authority(client):
    hdr=login(client,'mitra')
    post(client,'/api/orders',hdr,{'patient_id':1,'title':'Invalid attempt','instruction':'Never share internal records','category':'crown'},expected=400)
    hdr=login(client,'dokter')
    post(client,'/api/orders',hdr,{'patient_id':2,'title':'Invalid attempt','instruction':'Never share partner records','category':'crown'},expected=400)


def test_external_delay_approval_belongs_to_partner(client):
    hdr=login(client,'resepsionis')
    post(client,'/api/orders/2/assign-lead',hdr,{'lead_id':3})
    hdr=login(client,'lab')
    post(client,'/api/orders/2/confirm',hdr,{'accept':True})
    post(client,'/api/orders/2/plan',hdr,{'technician_id':4,'due':str(date.today()+timedelta(days=15))})
    new=str(date.today()+timedelta(days=19))
    post(client,'/api/orders/2/delay',hdr,{'new_due':new,'reason':'Material dental belum tersedia (simulasi)'})
    hdr=login(client,'pasien')
    assert client.get('/api/orders').json()[0]['source']=='internal'
    post(client,'/api/orders/2/delay/respond',hdr,{'approved':True,'expected_due':new},expected=404)
    hdr=login(client,'mitra')
    assert post(client,'/api/orders/2/delay/respond',hdr,{'approved':True,'expected_due':new})['promised_due']==new
    assert all(n['channel']=='partner_portal' for n in client.get('/api/notifications').json())


def test_daily_reports_available_to_other_divisions(client):
    hdr=login(client,'hr')
    response=post(client,'/api/daily-reports',hdr,{'summary':'Absensi shift tim fiktif','blockers':'Tidak ada'})
    assert response['id']>0
    assert len(client.get('/api/daily-reports').json())==1
    hdr=login(client,'direktur')
    rows=client.get('/api/daily-reports').json()
    assert any(r['division']=='hr' for r in rows)
