"""Original public login design with a separate cookie gate for temporary demo data."""
import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
import json

import pytest
from sqlalchemy import func, select

from backend import database
from backend.models import Audit, UserSession
from backend.runtime import DEMO_COOKIE, _signature, gate_cookie
from backend.tests.test_api import appmod, client
from backend.tests.test_temporary_hosting import configured


def setup(client,monkeypatch):
    runtime=configured()
    monkeypatch.setattr(appmod,'runtime',runtime)
    client.base_url='https://testserver'
    return runtime


def unlock(client,runtime):
    return client.post('/api/demo/access',json={'access_key':runtime.access_password},headers={'Origin':'https://testserver'})


def test_original_login_and_patient_design_are_directly_available(client,monkeypatch):
    runtime=setup(client,monkeypatch)
    page=client.get('/')
    assert page.status_code==200 and '/static/styles.css' in page.text
    assert 'www-authenticate' not in page.headers
    assert 'Demo Naraya Aurentis</h1>' not in page.text
    assert '/static/app.js' in page.text
    assert 'Manajemen Klinik' in client.get('/static/app.js').text
    patient=client.get('/pasien')
    assert patient.status_code==200 and '/static/portal.js' in patient.text
    assert '/static/app.js' not in patient.text
    assert runtime.access_password not in page.text + patient.text
    assert client.get('/static/assets/naraya-aurentis-transparent.png').status_code==200
    assert client.get('/api/patient/orders').status_code==401
    assert client.get('/api/training').status_code==401
    for path in ['/','/pasien','/static/app.js','/api/demo/status']:
        assert client.post(path,json={}).status_code==401


@pytest.mark.parametrize('origin,fetch_site',[(None,None),('https://foreign.test',None),('https://testserver','cross-site')])
def test_demo_cookie_cannot_be_set_cross_site_or_without_origin(client,monkeypatch,origin,fetch_site):
    runtime=setup(client,monkeypatch)
    headers={}
    if origin:headers['Origin']=origin
    if fetch_site:headers['Sec-Fetch-Site']=fetch_site
    response=client.post('/api/demo/access',json={'access_key':runtime.access_password},headers=headers)
    assert response.status_code==403
    assert 'set-cookie' not in response.headers
    assert DEMO_COOKIE not in client.cookies


def test_wrong_key_is_not_reflected_or_persisted(client,monkeypatch,caplog):
    runtime=setup(client,monkeypatch)
    with caplog.at_level('INFO',logger='nam.demo'):
        r=client.post('/api/demo/access',json={'access_key':'private-but-wrong-key'},headers={'Origin':'https://testserver'})
    assert r.status_code==401 and 'www-authenticate' not in r.headers
    assert 'private-but-wrong-key' not in r.text + caplog.text
    assert runtime.access_password not in caplog.text
    assert DEMO_COOKIE not in client.cookies
    assert client.get('/api/demo/status').json()['authorized'] is False


def test_successful_unlock_uses_secure_cookie_without_granting_a_role(client,monkeypatch,caplog):
    runtime=setup(client,monkeypatch)
    with caplog.at_level('INFO',logger='nam.demo'):
        r=unlock(client,runtime)
    assert r.status_code==200 and r.json()=={'authorized':True}
    cookie=SimpleCookie();cookie.load(r.headers['set-cookie'])
    entry=cookie[DEMO_COOKIE]
    assert entry['secure'] and entry['httponly'] and entry['samesite']=='strict' and entry['path']=='/'
    assert 0<int(entry['max-age'])<=8*3600
    assert runtime.access_password not in entry.value + caplog.text + r.text
    assert client.get('/api/demo/status').json()['authorized'] is True
    assert client.get('/api/health').status_code==200
    assert client.get('/api/me').status_code==401
    assert client.get('/api/patient/orders').status_code==401
    original=client.cookies.get(DEMO_COOKIE)
    assert unlock(client,runtime).status_code==200
    assert client.cookies.get(DEMO_COOKIE)==original
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(UserSession))==0
        assert db.scalar(select(func.count()).select_from(Audit))==0
    login=client.post('/api/patient/login',json={'username':'DEMO-P-001','password':'DemoNAM2026!'},headers={'Origin':'https://testserver'})
    assert login.status_code==200
    assert client.get('/api/patient/orders').status_code==200
    assert client.get('/api/patient/orders/2').status_code==404
    assert client.get('/api/organization').status_code==401
    assert client.post('/api/patient/logout').status_code==403
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='auth.login'))==1


@pytest.mark.parametrize('change',['signature','expired','too_long','audience','deployment'])
def test_tampering_and_wrong_cookie_scope_are_rejected(client,monkeypatch,change):
    runtime=setup(client,monkeypatch)
    token,_=gate_cookie(runtime)
    encoded,signature=token.split('.')
    if change=='signature':
        signature='0'*64
    else:
        data=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
        if change=='expired':data['exp']=int(datetime.now(timezone.utc).timestamp())-1
        if change=='too_long':data['exp']=int((runtime.expires_at+timedelta(days=1)).timestamp())
        if change=='audience':data['aud']='workspace'
        if change=='deployment':data['deployment']='another.vercel.app'
        encoded=base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip('=')
        signature=_signature(runtime,encoded)
    client.cookies.set(DEMO_COOKIE,encoded+'.'+signature)
    assert client.get('/api/health').status_code==401
    assert not client.get('/api/demo/status').json()['authorized']


def test_gate_cookie_is_not_an_application_session_and_expiry_still_blocks(client,monkeypatch):
    runtime=setup(client,monkeypatch)
    assert unlock(client,runtime).status_code==200
    token=client.cookies.get(DEMO_COOKIE)
    client.cookies.set('nam_session',token)
    client.cookies.set('nam_patient_session',token,path='/api/patient')
    assert client.get('/api/me').status_code==401
    assert client.get('/api/patient/me').status_code==401
    monkeypatch.setattr(appmod,'runtime',replace(runtime,expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)))
    assert client.get('/').status_code==200
    assert client.get('/api/health').status_code==410
    assert unlock(client,runtime).status_code==410
    assert not client.get('/api/demo/status').json()['available']
