"""Workspace behavior, session recovery, object scope and workflow regressions."""
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from backend import database
from backend.models import Audit, Org, Shift, User, UserSession
from backend.utils import pwd_hash
from backend.tests.test_api import client, login, post, assign_and_accept


def test_session_recovers_csrf_without_rotation_and_can_submit(client):
    headers = login(client, 'resepsionis')
    cookie = client.cookies.get('nam_session')
    for _ in range(2):
        restored = client.get('/api/me')
        assert restored.status_code == 200
        assert restored.json()['csrf'] == headers['X-CSRF-Token']
        assert restored.json()['org_id'] == 1
        assert client.cookies.get('nam_session') == cookie
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(UserSession)) == 1
    restored_headers = {'X-CSRF-Token': restored.json()['csrf']}
    post(client, '/api/daily-reports', restored_headers, {'summary': 'Catatan setelah muat ulang'})
    assert client.post('/api/daily-reports', json={'summary':'Tanpa token'}).status_code == 403
    assert client.post('/api/logout', headers={**headers, 'Origin':'https://untrusted.invalid'}).status_code == 403
    assert client.get('/api/me').status_code == 200
    post(client, '/api/logout', restored_headers)
    assert client.get('/api/me').status_code == 401
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(UserSession)) == 0
        assert db.scalar(select(Audit).where(Audit.event == 'auth.logout'))


def test_relogin_revokes_previous_session(client):
    login(client, 'resepsionis')
    old_cookie = client.cookies.get('nam_session')
    login(client, 'dokter')
    assert client.get('/api/me').json()['role'] == 'dentist'
    client.cookies.clear()
    client.cookies.set('nam_session', old_cookie)
    assert client.get('/api/me').status_code == 401


@pytest.mark.parametrize('username,allowed,clinical', [
    ('resepsionis',True,False), ('dokter',True,True), ('lab',True,True),
    ('teknisi',False,False), ('qc',True,True), ('fat',True,False),
    ('direktur',True,False), ('pasien',True,False), ('mitra',False,False),
    ('it',False,False), ('dokter2',False,False), ('perawat',False,False),
    ('cadcam',False,False), ('cs',False,False), ('gudang',False,False),
    ('purchasing',False,False), ('hr',False,False), ('marketing',False,False),
])
def test_order_detail_role_and_field_matrix(client,username,allowed,clinical):
    login(client, username)
    response = client.get('/api/orders/1')
    assert response.status_code == (200 if allowed else 404)
    if allowed:
        data = response.json()
        assert ('instruction' in data['order']) is clinical
        assert not any(key in data['order'] for key in ('phone','password_hash','csrf'))
        assert set(data) == {'order','activity','initial_due'}


def test_detail_is_scoped_audited_and_does_not_expose_raw_audit(client):
    assign_and_accept(client)
    login(client, 'pasien')
    response = client.get('/api/orders/1')
    assert response.status_code == 200
    assert [row['event'] for row in response.json()['activity']] == ['lab_order.lead_assigned','lab_order.accepted']
    assert all(set(row) == {'event','at'} for row in response.json()['activity'])
    assert client.get('/api/orders/2').status_code == 404
    login(client, 'mitra')
    assert client.get('/api/orders/2').status_code == 200
    assert client.get('/api/orders/1').status_code == 404
    with database.SessionLocal() as db:
        views = db.scalars(select(Audit).where(Audit.event == 'order.viewed')).all()
        assert len(views) == 2
        assert {row.entity_id for row in views} == {1,2}


def test_second_partner_cannot_read_other_tenant(client):
    with database.SessionLocal() as db:
        db.add(Org(id=3,name='Mitra terpisah (DEMO)',kind='partner'))
        db.add(User(username='mitra-lain',display_name='Mitra lain',role='partner',org_id=3,
                    password_hash=pwd_hash('DemoNAM2026!'),active=True))
        db.commit()
    login(client,'mitra-lain')
    assert client.get('/api/orders').json() == []
    assert client.get('/api/orders/2').status_code == 404
    assert client.get('/api/patients').json() == []
    assert client.get('/api/invoices').json() == []
    assert client.get('/api/notifications').json() == []
    assert client.get('/api/appointments').status_code == 403
    assert client.get('/api/roster').status_code == 403


@pytest.mark.parametrize('username', ['resepsionis','dokter','lab','qc','fat','direktur','teknisi'])
def test_internal_role_from_wrong_organization_does_not_get_staff_access(client,username):
    login(client,username)
    with database.SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        user.org_id = 2
        db.commit()
    assert client.get('/api/orders').json() == []
    assert client.get('/api/orders/1').status_code == 404
    assert client.get('/api/roster').status_code == 403
    assert client.get('/api/patients').status_code == 403
    assert client.get('/api/invoices').status_code == 403
    assert client.get('/api/daily-reports').status_code == 403


def test_roster_uses_active_scoped_technicians(client):
    login(client, 'lab')
    assert any(row['id'] == 4 and row['role'] == 'technician' for row in client.get('/api/roster').json())
    with database.SessionLocal() as db:
        db.get(User,4).active = False
        db.commit()
    assert all(row['id'] != 4 for row in client.get('/api/roster').json())


@pytest.mark.parametrize('invalid', ['organization','inactive','shift'])
def test_planning_rejects_ineligible_technician(client,invalid):
    headers = assign_and_accept(client)
    with database.SessionLocal() as db:
        technician = db.get(User,4)
        if invalid == 'organization': technician.org_id = 2
        if invalid == 'inactive': technician.active = False
        if invalid == 'shift':
            shift = db.scalar(select(Shift).where(Shift.user_id==4,Shift.shift_day==date.today()))
            shift.available = False
        db.commit()
    post(client,'/api/orders/1/plan',headers,{'technician_id':4,'due':str(date.today()+timedelta(days=12))},expected=409 if invalid == 'shift' else 400)
    assert client.get('/api/orders/1').json()['order']['status'] == 'accepted'


def test_delay_cannot_be_overwritten_replayed_or_approved_from_stale_form(client):
    headers = assign_and_accept(client)
    original = client.get('/api/orders/1').json()['order']['promised_due']
    first = str(date.today()+timedelta(days=14))
    second = str(date.today()+timedelta(days=18))
    post(client,'/api/orders/1/delay',headers,{'new_due':first,'reason':'Kendala material simulasi'})
    post(client,'/api/orders/1/delay',headers,{'new_due':second,'reason':'Usulan menimpa simulasi'},expected=409)
    patient = login(client,'pasien')
    post(client,'/api/orders/1/delay/respond',patient,{'approved':True,'expected_due':second},expected=409)
    assert client.get('/api/orders/1').json()['order']['promised_due'] == original
    post(client,'/api/orders/1/delay/respond',patient,{'approved':False,'expected_due':first})
    headers = login(client,'lab')
    post(client,'/api/orders/1/delay',headers,{'new_due':second,'reason':'Revisi setelah penolakan'})
    patient = login(client,'pasien')
    post(client,'/api/orders/1/delay/respond',patient,{'approved':True,'expected_due':first},expected=409)
    post(client,'/api/orders/1/delay/respond',patient,{'approved':True,'expected_due':second})
    post(client,'/api/orders/1/delay/respond',patient,{'approved':True,'expected_due':second},expected=409)
    detail = client.get('/api/orders/1').json()
    assert detail['initial_due'] == original
    assert detail['order']['promised_due'] == second
    assert sum(row['event'] == 'lab_order.delay_proposed' for row in detail['activity']) == 2
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='lab_order.delay_decided')) == 2


def test_frontend_assets_and_security_headers(client):
    home = client.get('/')
    assert home.status_code == 200
    assert 'script-src \'self\'' in home.headers['content-security-policy']
    for name in ('app.js','views.js','actions.js','styles.css','assets/naraya-aurentis-logo.png'):
        assert client.get('/static/'+name).status_code == 200
    assert 'lang="id"' in home.text
    assert 'style="' not in home.text
