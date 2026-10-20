"""Every explicit demo account works without changing business permissions."""
import pytest
from sqlalchemy import func, select

from backend import database
from backend.demo import seed_staff_accounts
from backend.demo_accounts import BASE_USERS, EXTRA_STAFF
from backend.models import Audit, OrganizationPosition, Patient, User
from backend.modules.organization import seed_structure
from backend.tests.test_api import client
from backend.utils import pwd_hash


STAFF_NAMES = [row[1] for row in BASE_USERS if row[3] != 'patient'] + [row[0] for row in EXTRA_STAFF]


@pytest.mark.parametrize('username', STAFF_NAMES)
def test_every_staff_login_accepts_uppercase_and_recovers_session(client,username):
    payload={'username':'  '+username.upper()+'  ','password':'DemoNAM2026!'}
    assert client.post('/api/access/resolve',json=payload).json()=={'portal':'workspace'}
    login=client.post('/api/workspace/login',json=payload)
    assert login.status_code==200
    me=client.get('/api/me')
    assert me.status_code==200 and me.json()['role']==login.json()['user']['role']
    assert client.get('/api/dashboard').status_code==200
    if username != 'mitra':
        for path in ('/api/training','/api/sops','/api/sop-reports','/api/organization'):
            assert client.get(path).status_code==200
    assert client.post('/api/logout').status_code==403
    assert client.post('/api/logout',headers={'X-CSRF-Token':me.json()['csrf']}).status_code==200
    assert client.get('/api/me').status_code==401
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='auth.login'))==1


@pytest.mark.parametrize('username', ['pasien',' PASIEN ','demo-p-001',' Demo-P-001 '])
def test_patient_identifiers_keep_their_audience_and_ownership(client,username):
    payload={'username':username,'password':'DemoNAM2026!'}
    assert client.post('/api/access/resolve',json=payload).json()=={'portal':'patient'}
    assert client.post('/api/patient/login',json=payload).status_code==200
    assert client.get('/api/patient/orders').status_code==200
    assert client.get('/api/patient/orders/2').status_code==404
    assert client.get('/api/organization').status_code==401


@pytest.mark.parametrize('username,expected', [('DIREKTUR UTAMA','chief_executive'),('DIRUT','chief_executive'),('IC / GA','general_affairs'),('KEPALA LAB','lab_supervisor'),('BRANCH HEAD','branch_manager')])
def test_explicit_title_aliases_select_existing_account_only(client,username,expected):
    r=client.post('/api/workspace/login',json={'username':username,'password':'DemoNAM2026!'})
    assert r.status_code==200 and r.json()['user']['role']==expected


@pytest.mark.parametrize('password',['demonam2026!','DEMONAM2026!',' DemoNAM2026!','DemoNAM2026! '])
def test_password_still_requires_exact_case_and_characters(client,password):
    assert client.post('/api/workspace/login',json={'username':'DIREKTUR','password':password}).status_code==401
    assert not client.cookies


def test_case_collision_fails_closed_across_tenants(client):
    with database.SessionLocal() as db:
        db.add(User(username='DIREKTUR',display_name='Konflik Demo',password_hash=pwd_hash('DemoNAM2026!'),role='partner',org_id=2,active=True))
        db.commit()
    assert client.post('/api/workspace/login',json={'username':'direktur','password':'DemoNAM2026!'}).status_code==401
    assert not client.cookies


def test_patient_reference_collision_fails_closed(client):
    with database.SessionLocal() as db:
        db.add(Patient(public_id='demo-p-001',display_name='Referensi konflik fiktif',phone='00000000',org_id=1,user_id=None))
        db.commit()
    assert client.post('/api/patient/login',json={'username':'DEMO-P-001','password':'DemoNAM2026!'}).status_code==401
    assert not client.cookies


def test_actual_username_takes_precedence_over_title_alias(client):
    with database.SessionLocal() as db:
        db.add(User(username='direktur utama',display_name='Nama Bentrok Demo',role='partner',org_id=2,password_hash=pwd_hash('SandiMitraDemo!'),active=True))
        db.commit()
    assert client.post('/api/workspace/login',json={'username':'DIREKTUR UTAMA','password':'DemoNAM2026!'}).status_code==401
    r=client.post('/api/workspace/login',json={'username':'DIREKTUR UTAMA','password':'SandiMitraDemo!'})
    assert r.status_code==200 and r.json()['user']['role']=='partner'


@pytest.mark.parametrize('username',['komisaris','direktur_utama','auditor','operation','branch_head','kepala_klinik'])
def test_chart_hierarchy_does_not_grant_clinical_or_financial_actions(client,username):
    r=client.post('/api/workspace/login',json={'username':username,'password':'DemoNAM2026!'})
    headers={'X-CSRF-Token':r.json()['csrf']}
    assert client.get('/api/orders').json()==[]
    assert client.get('/api/patient/orders').status_code==401
    assert client.post('/api/orders/1/qc',json={'passed':True},headers=headers).status_code in (403,404)
    assert client.post('/api/invoices',json={'order_id':1,'amount_idr':10000},headers=headers).status_code==403


def test_supplemental_fixtures_are_idempotent_and_preserve_existing_accounts(client):
    with database.SessionLocal() as db:
        user=db.scalar(select(User).where(User.username=='komisaris'))
        user.active=False;user.password_hash=pwd_hash('SandiIndividualDemo!');user.org_id=2;user.role='partner'
        db.commit()
        previous=(user.id,user.password_hash,user.org_id,user.role,user.active)
        before=db.scalar(select(func.count()).select_from(User))
        for _ in range(2):seed_staff_accounts(db);seed_structure(db)
        db.refresh(user)
        assert previous==(user.id,user.password_hash,user.org_id,user.role,user.active)
        assert db.scalar(select(func.count()).select_from(User))==before
        assert db.scalar(select(func.count()).select_from(Audit))==0
        # New vacancies/positions do not automatically provision credentials.
        db.add(OrganizationPosition(org_id=1,code='future_role',name='Posisi Masa Depan',parent_code=None,division='Demo',allowed_roles='["commissioner"]'))
        db.commit();seed_staff_accounts(db)
        assert db.scalar(select(func.count()).select_from(User))==before
