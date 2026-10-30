"""Temporary hosting must fail closed and retain the application's business guards."""
import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from http.cookies import SimpleCookie

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend import database
from backend.models import Audit, ChatMessage, UserSession
from backend.modules import auth
from backend.runtime import DemoRuntime
from backend.tests.test_api import appmod, client, login, post


def configured():
    return DemoRuntime(hosted=True, opted_in=True, access_password='test-access-key-long-enough-001',
                       expires_at=datetime.now(timezone.utc)+timedelta(days=7), deployment='test.vercel.app')


def credentials(password=None):
    value = ('demo:' + (password or configured().access_password)).encode()
    return 'Basic ' + base64.b64encode(value).decode()


def test_runtime_defaults_and_temporary_database_are_isolated():
    local = DemoRuntime.from_env({})
    assert not local.hosted and local.problem() is None
    assert local.database_url('sqlite:///local.db') == 'sqlite:///local.db'
    runtime = configured()
    url = runtime.database_url('postgresql://must-never-be-opened')
    assert url.startswith('sqlite:///') and 'nam-demo-' in url
    assert 'must-never-be-opened' not in url
    assert url == runtime.database_url('sqlite:///other.db')
    assert url != replace(runtime, deployment='other.vercel.app').database_url('unused')
    assert url != replace(runtime, access_password='other-key-long-enough-12345').database_url('unused')
    assert runtime.access_password not in repr(runtime)
    assert runtime.access_password not in json.dumps(runtime.metadata())


@pytest.mark.parametrize('env,expected',[
    ({'VERCEL':'1'}, 'not_enabled'),
    ({'NAM_ONLINE_DEMO':'1'}, 'missing_access_key'),
    ({'NAM_ONLINE_DEMO':'1','NAM_DEMO_ACCESS_PASSWORD':'a'*24}, 'invalid_expiry'),
    ({'NAM_ONLINE_DEMO':'1','NAM_DEMO_ACCESS_PASSWORD':'a'*24,'NAM_DEMO_EXPIRES_AT':'2030-01-01'}, 'invalid_expiry'),
])
def test_hosted_configuration_fails_closed(env,expected):
    assert DemoRuntime.from_env(env).problem() == expected


def test_expiry_requires_a_bounded_future_timestamp():
    runtime = configured()
    assert runtime.problem() is None
    assert replace(runtime,expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)).problem() == 'expired'
    assert replace(runtime,expires_at=datetime.now(timezone.utc)+timedelta(days=32)).problem() == 'invalid_expiry'
    env={'VERCEL':'1','NAM_ONLINE_DEMO':'1','NAM_DEMO_ACCESS_PASSWORD':runtime.access_password,
         'NAM_DEMO_EXPIRES_AT':runtime.expires_at.isoformat()}
    assert DemoRuntime.from_env(env).problem() is None


def test_missing_configuration_skips_database_startup(monkeypatch):
    monkeypatch.setattr(appmod,'runtime',DemoRuntime(hosted=True))
    def forbidden():
        raise AssertionError('Blocked hosting must never open or migrate a database')
    monkeypatch.setattr(database,'upgrade_schema',forbidden)
    with TestClient(appmod.app) as c:
        assert c.get('/').status_code == 200
        assert c.get('/api/health').status_code == 503
        assert c.get('/static/app.js').status_code == 200
        assert not c.get('/api/demo/status').json()['available']


@pytest.mark.parametrize('header',['','Bearer ignored','Basic !!!','Basic ZGVtbw==',credentials('wrong'),'Basic '+'a'*3000])
def test_outer_gate_protects_data_and_mutations(client,monkeypatch,header):
    monkeypatch.setattr(appmod,'runtime',configured())
    headers={'Authorization':header} if header else {}
    for path in ['/api/health','/api/orders','/api/me','/api/patient/orders','/api/sop-reports','/api/organization','/static/not-public.txt']:
        r=client.get(path,headers=headers)
        assert r.status_code == 401
        assert 'www-authenticate' not in r.headers
        assert r.headers['cache-control'] == 'no-store'
        assert 'noindex' in r.headers['x-robots-tag']
        assert 'DemoNAM2026!' not in r.text
    assert client.post('/api/workspace/login',json={'username':'it','password':'DemoNAM2026!'},headers=headers).status_code==401
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(UserSession)) == 0


def test_valid_gate_does_not_grant_a_role_or_patient_data(client,monkeypatch):
    monkeypatch.setattr(appmod,'runtime',configured())
    monkeypatch.setattr(auth,'COOKIE_SECURE',True)
    client.base_url='https://testserver'
    client.headers['Authorization']=credentials()
    assert client.get('/').status_code==200
    assert client.get('/pasien').status_code==200
    assert client.get('/api/health').json()['storage']=='ephemeral_per_instance'
    assert client.get('/api/orders').status_code==401
    assert client.get('/output/Naraya_Aurentis_Alur_Lengkap_Demo_0.4.pptx').status_code==404
    r=client.post('/api/workspace/login',json={'username':'it','password':'DemoNAM2026!'},headers={'Origin':'https://testserver'})
    assert r.status_code==200
    cookie=SimpleCookie();cookie.load(r.headers['set-cookie'])
    assert cookie['nam_session']['secure'] and cookie['nam_session']['httponly']
    assert client.get('/api/orders').json()==[]
    assert client.get('/api/patient/orders').status_code==401
    assert client.post('/api/invoices',json={'order_id':1,'amount_idr':100},headers={'X-CSRF-Token':r.json()['csrf']}).status_code==403


def test_online_patient_keeps_scope_csrf_idempotency_and_audit(client,monkeypatch):
    monkeypatch.setattr(appmod,'runtime',configured())
    client.headers['Authorization']=credentials()
    response=client.post('/api/patient/login',json={'username':'DEMO-P-001','password':'DemoNAM2026!'})
    assert response.status_code==200
    csrf={'X-CSRF-Token':response.json()['csrf']}
    assert client.get('/api/patient/orders/2').status_code==404
    assert client.get('/api/organization').status_code==401
    assert client.post('/api/patient/chat/conversations',json={'request_id':'online-no-csrf-001'}).status_code==403
    request={'request_id':'online-request-0001','order_id':1}
    first=post(client,'/api/patient/chat/conversations',csrf,request)
    again=post(client,'/api/patient/chat/conversations',csrf,request)
    assert first['id']==again['id']
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ChatMessage))==1
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='chat.started'))==1
    post(client,'/api/patient/chat/conversations/'+first['id']+'/handoff',csrf,{'request_id':'online-handoff-0001'})
    # A gateway key alone does not turn a receptionist into CS or FAT.
    staff=login(client,'resepsionis')
    assert client.get('/api/chat/queue').status_code==403
    post(client,'/api/orders/1/qc',staff,{'passed':True},403)
    assert client.post('/api/patient/logout',headers={**csrf,'Origin':'https://wrong.example'}).status_code==403


def test_expiry_blocks_existing_sessions_without_deleting_audit(client,monkeypatch):
    runtime=configured()
    monkeypatch.setattr(appmod,'runtime',runtime)
    client.headers['Authorization']=credentials()
    login(client,'it')
    monkeypatch.setattr(appmod,'runtime',replace(runtime,expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)))
    assert client.get('/api/me').status_code==410
    assert client.get('/').status_code==200
    assert not client.get('/api/demo/status').json()['available']
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='auth.login'))==1


def test_hosted_config_always_enables_secure_cookies_and_keeps_production_blocked():
    import os
    env={**os.environ,'VERCEL':'1','COOKIE_SECURE':'false','NAM_ENV':'demo'}
    root=Path(__file__).resolve().parents[2]
    result=subprocess.run([sys.executable,'-c','from backend.config import COOKIE_SECURE, DATABASE_URL; assert COOKIE_SECURE; assert "nam-demo-" in DATABASE_URL'],env=env,cwd=root,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    result=subprocess.run([sys.executable,'-c','import backend.config'],env={**env,'NAM_ENV':'production'},cwd=root,capture_output=True,text=True)
    assert result.returncode!=0 and 'intentionally blocked in production' in result.stderr


def test_real_cloud_entrypoint_cold_start_from_another_directory(tmp_path):
    """Exercise real config, scratch DB, migrations, fixtures, static files and HTTPS login."""
    import os
    runtime=configured()
    root=Path(__file__).resolve().parents[2]
    env={**os.environ,'PYTHONPATH':str(root),'VERCEL':'1','VERCEL_URL':tmp_path.name+'.vercel.app',
         'NAM_ENV':'demo','NAM_ONLINE_DEMO':'1','NAM_DEMO_ACCESS_PASSWORD':runtime.access_password,
         'NAM_DEMO_EXPIRES_AT':runtime.expires_at.isoformat(),'DATABASE_URL':'postgresql://do-not-connect',
         'TEMP':str(tmp_path),'TMP':str(tmp_path),'COOKIE_SECURE':'false'}
    script='''
from app import app
from fastapi.testclient import TestClient
from backend.config import runtime, DATABASE_URL
from backend import database
from sqlalchemy import text
with TestClient(app,base_url='https://testserver') as c:
    assert c.get('/').status_code==200
    c.auth=('demo',runtime.access_password)
    assert c.get('/').status_code==200
    assert c.get('/static/runtime.js').status_code==200
    assert c.get('/api/health').json()['storage']=='ephemeral_per_instance'
    response=c.post('/api/patient/login',json={'username':'DEMO-P-001','password':'DemoNAM2026!'})
    assert response.status_code==200,response.text
    assert c.get('/api/patient/me').status_code==200
    assert c.get('/api/me').status_code==401
    assert c.get('/api/patient/orders/2').status_code==404
    with database.engine.connect() as connection:
        assert connection.scalar(text('select version_num from alembic_version'))=='0006'
assert 'do-not-connect' not in DATABASE_URL
'''
    result=subprocess.run([sys.executable,'-c',script],env=env,cwd=tmp_path,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    assert list(tmp_path.glob('nam-demo-*.sqlite3'))
