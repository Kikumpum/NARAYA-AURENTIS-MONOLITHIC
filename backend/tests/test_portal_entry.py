"""Neutral entry resolves authenticated accounts without merging portal access."""
import hashlib
from dataclasses import replace
from sqlalchemy import func, select
import pytest

from backend import database
from backend.models import Audit, Patient, User, UserSession
from backend.runtime import DemoRuntime
from backend.tests.test_api import client, login
from backend.tests.test_temporary_hosting import configured


def resolve(client, username, **extra):
    return client.post('/api/access/resolve', json={'username':username,'password':'DemoNAM2026!',**extra})


@pytest.mark.parametrize('username,portal', [('resepsionis','workspace'),('it','workspace'),('mitra','workspace'),('DEMO-P-001','patient'),('pasien','patient')])
def test_portal_is_chosen_from_verified_account_without_creating_session(client,username,portal):
    for _ in range(2):
        response=resolve(client,username,role='director',org_id=2)
        assert response.status_code==200 and response.json()=={'portal':portal}
    assert client.get('/api/me').status_code==401
    assert client.get('/api/patient/me').status_code==401
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(UserSession))==0
        assert db.scalar(select(func.count()).select_from(Audit))==0


def test_patient_entry_preserves_audience_scope_csrf_and_relogin_revocation(client):
    assert resolve(client,'DEMO-P-001').json()=={'portal':'patient'}
    response=client.post('/api/patient/login',json={'username':'DEMO-P-001','password':'DemoNAM2026!'})
    assert response.status_code==200
    old=client.cookies.get('nam_patient_session')
    assert client.get('/api/patient/orders').status_code==200
    assert client.get('/api/patient/orders/2').status_code==404
    assert client.get('/api/organization').status_code==401
    assert client.post('/api/patient/logout').status_code==403
    assert resolve(client,'DEMO-P-001').status_code==200
    again=client.post('/api/patient/login',json={'username':'DEMO-P-001','password':'DemoNAM2026!'})
    assert again.status_code==200 and client.cookies.get('nam_patient_session')!=old
    with database.SessionLocal() as db:
        assert not db.scalar(select(UserSession).where(UserSession.token_hash==hashlib.sha256(old.encode()).hexdigest()))
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='auth.login'))==2
    assert client.post('/api/patient/logout',headers={'X-CSRF-Token':again.json()['csrf']}).status_code==200


@pytest.mark.parametrize('invalid', ['password','inactive','tenant','unlinked'])
def test_invalid_credentials_or_patient_link_do_not_resolve(client,invalid):
    with database.SessionLocal() as db:
        if invalid=='inactive':db.get(User,9).active=False
        if invalid=='tenant':db.get(User,9).org_id=2
        if invalid=='unlinked':db.get(Patient,1).user_id=None
        db.commit()
    response=resolve(client,'DEMO-P-001',**({'password':'wrong'} if invalid=='password' else {}))
    assert response.status_code in (401,403)
    assert 'portal' not in response.json()
    assert not client.cookies


def test_resolve_rejects_cross_origin_without_replacing_existing_session(client):
    login(client,'resepsionis')
    old=client.cookies.get('nam_session')
    response=client.post('/api/access/resolve',json={'username':'pasien','password':'DemoNAM2026!'},headers={'Origin':'https://foreign.invalid'})
    assert response.status_code==403
    assert client.cookies.get('nam_session')==old
    assert client.get('/api/me').json()['role']=='reception'


def test_shared_database_is_explicit_tls_demo_only_and_not_public():
    url='postgresql://demo:private-password@demo.example/demo?sslmode=require'
    runtime=replace(configured(),shared_database_enabled=True,shared_database_url=url)
    assert runtime.problem() is None
    assert runtime.database_url('postgresql://production-do-not-use')==url.replace('postgresql:','postgresql+psycopg:',1)
    assert runtime.metadata()['storage']=='shared_postgresql'
    assert 'private-password' not in repr(runtime)+str(runtime.metadata())
    assert replace(runtime,deployment='new-deployment').database_url('ignored')==runtime.database_url('ignored')
    assert not replace(runtime,shared_database_enabled=False).database_url('ignored').startswith('postgres')
    assert DemoRuntime().database_url('sqlite:///local.db')=='sqlite:///local.db'


@pytest.mark.parametrize('url', ['', 'sqlite:///wrong.db','postgresql://user:password@host/demo',
                                  'postgresql://user:password@host/demo?sslmode=disable','https://foreign.invalid'])
def test_invalid_shared_database_fails_closed_without_external_fallback(url):
    runtime=replace(configured(),shared_database_enabled=True,shared_database_url=url)
    assert runtime.problem()=='invalid_shared_database'
    assert runtime.database_url('postgresql://must-not-open').startswith('sqlite:')
