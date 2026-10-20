"""Synthetic data only: organization, checklist workflow, private evidence and exports."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import io
import json
import uuid
import zipfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_api import client, login, post, assign_and_accept, appmod
from backend import database
from backend.models import Audit, LabOrder, Org, OrganizationPosition, ReportAttachment, SopReport, SopReportVersion, User, UserPosition
from backend.modules.sop_reports import MAX_FILE
from backend.organization_catalog import ADDITIONAL_ROLES
from backend.sop_catalog import BY_CODE, CATALOG
from backend.utils import pwd_hash


def key():return uuid.uuid4().hex


def create(c,headers,code='IT-01',order=None):
    data={'sop_code':code,'report_day':str(date.today()),'order_id':order,'request_key':key()}
    return post(c,'/api/sop-reports',headers,data),data


def answers(report,**change):
    rows=[dict(key=i['key'],result='ok',note='',action='',owner='',due=None) for i in report['sop']['items']]
    if change:rows[0].update(change)
    return rows


def save(c,h,r,rows=None,summary='Pemeriksaan teknis fiktif selesai'):
    data={'expected_revision':r['revision'],'summary':summary,'results':rows or answers(r),'request_key':key()}
    return post(c,f"/api/sop-reports/{r['id']}/save",h,data),data


def upload(c,h,r,item=None,body=b'Bukti sintetis untuk pengujian.',filename='bukti-demo.txt',request_key=None,expected=200):
    item=item or next(i['key'] for i in r['sop']['items'] if i['evidence_required'])
    params={'filename':filename,'item_key':item,'expected_revision':r['revision'],'request_key':request_key or key()}
    response=c.post(f"/api/sop-reports/{r['id']}/attachments",params=params,content=body,headers={**h,'Content-Type':'application/octet-stream'})
    assert response.status_code==expected,response.text
    if expected==200:r['revision']=response.json()['revision']
    return response,params


def complete(c,h,code='IT-01',order=None):
    r,_=create(c,h,code,order);r,_=save(c,h,r)
    for item in r['sop']['items']:
        if item['evidence_required']:upload(c,h,r,item['key'])
    data={'expected_revision':r['revision'],'request_key':key()}
    return post(c,f"/api/sop-reports/{r['id']}/submit",h,data)


@pytest.mark.parametrize('username',['resepsionis','dokter','lab','teknisi','qc','fat','direktur','it','perawat','cadcam','cs','gudang','purchasing','hr','marketing'])
def test_staff_catalog_and_position_are_scoped(client,username):
    login(client,username)
    data=client.get('/api/sops').json()
    assert len(data['items'])==len(CATALOG)
    assert any(s['can_start'] for s in data['items'])
    org=client.get('/api/organization').json()
    assert len(org['positions'])==31 and org['draft']
    assert not any('password' in json.dumps(p) for p in org['positions'])
    assert client.get('/api/sops/manual').status_code==200


@pytest.mark.parametrize('username',['pasien','mitra'])
def test_portal_users_cannot_read_staff_sops_structure_or_reports(client,username):
    h=login(client,username)
    for path in ('/api/sops','/api/sops/manual','/api/organization','/api/sop-reports'):
        assert client.get(path).status_code==403
    post(client,'/api/sop-reports',h,{'sop_code':'INC-01','report_day':str(date.today()),'request_key':key()},403)


def test_all_chart_roles_have_sop_but_vacancies_do_not_create_logins(client):
    assert all(any(role in s['roles'] for s in CATALOG) for role in ADDITIONAL_ROLES)
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User))==19
        assert db.scalar(select(func.count()).select_from(UserPosition))==17
    login(client,'direktur')
    positions=client.get('/api/organization').json()['positions']
    assert not next(p for p in positions if p['code']=='commissioner')['accounts']
    assert next(p for p in positions if p['code']=='reception')['accounts'][0]['name']=='Resepsionis Demo'


def test_position_change_is_compatible_scoped_versioned_idempotent_audited(client):
    h=login(client,'hr');data=client.get('/api/organization').json()
    account=next(u for u in data['staff'] if u['id']==12)
    position=next(p for p in data['positions'] if p['code']=='lab_head')
    payload={'user_id':12,'position_id':position['id'],'expected_revision':account['revision'],'reason':'Rotasi akun latihan sesuai fungsi','request_key':key()}
    first=post(client,'/api/organization/assignments',h,payload)
    assert post(client,'/api/organization/assignments',h,payload)==first
    post(client,'/api/organization/assignments',h,{**payload,'request_key':key()},409)
    post(client,'/api/organization/assignments',h,{**payload,'user_id':1,'request_key':key()},409)
    post(client,'/api/organization/assignments',h,{**payload,'user_id':8,'request_key':key()},404)
    with database.SessionLocal() as db:
        assert db.get(User,12).role=='lab_supervisor'
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='organization.position_assigned'))==1
    h=login(client,'resepsionis')
    post(client,'/api/organization/assignments',h,payload,403)


def test_wrong_tenant_staff_cannot_access_any_new_module(client):
    h=login(client,'it')
    with database.SessionLocal() as db:
        db.get(User,10).org_id=2;db.commit()
    for path in ('/api/organization','/api/sops','/api/sop-reports','/api/sops/manual'):
        assert client.get(path).status_code==403
    post(client,'/api/sop-reports',h,{'sop_code':'IT-01','report_day':str(date.today()),'request_key':key()},403)


def test_template_role_input_and_order_workflow_cannot_be_bypassed(client):
    h=login(client,'resepsionis')
    base={'sop_code':'QC-01','report_day':str(date.today()),'order_id':1,'request_key':key()}
    post(client,'/api/sop-reports',h,base,403)
    h=login(client,'lab')
    post(client,'/api/sop-reports',h,{**base,'sop_code':'LAB-01','request_key':key()},404)
    h=assign_and_accept(client)
    r,_=create(client,h,'LAB-01',1)
    assert r['order_state_at_creation']=='accepted'
    h2=login(client,'lab2')
    assert client.get('/api/sop-orders?sop_code=LAB-01').json()==[]
    assert client.get(f"/api/sop-reports/{r['id']}").status_code==404
    post(client,'/api/sop-reports',h2,{**base,'sop_code':'LAB-01','request_key':key()},404)
    h=login(client,'qc')
    post(client,'/api/sop-reports',h,base,409)
    with database.SessionLocal() as db:
        db.get(LabOrder,1).status='qc_pending';db.get(LabOrder,1).technician_id=5;db.commit()
    post(client,'/api/sop-reports',h,{**base,'request_key':key()},404)


def test_draft_is_private_and_director_gets_only_clinical_status(client):
    h=login(client,'dokter')
    r,_=create(client,h,'CLI-01',1)
    login(client,'direktur')
    assert client.get('/api/sop-reports').json()==[]
    assert client.get(f"/api/sop-reports/{r['id']}").status_code==404
    h=login(client,'dokter');r=complete(client,h,'CLI-01',1)
    login(client,'direktur')
    row=next(x for x in client.get('/api/sop-reports').json() if x['id']==r['id'])
    assert row['can_read'] is False
    assert not set(row)&{'summary','order_id','author','results','attachments','review_note'}
    for suffix in ('','/export','/attachments/1'):
        assert client.get(f"/api/sop-reports/{r['id']}"+suffix).status_code==404


def test_create_save_upload_submit_are_idempotent_and_no_business_state_changes(client):
    h=login(client,'it');r,data=create(client,h)
    assert post(client,'/api/sop-reports',h,data)['id']==r['id']
    post(client,'/api/sop-reports',h,{**data,'report_day':str(date.today()-timedelta(days=1))},409)
    r,data=save(client,h,r)
    assert post(client,f"/api/sop-reports/{r['id']}/save",h,data)['revision']==r['revision']
    response,params=upload(client,h,r)
    again=client.post(f"/api/sop-reports/{r['id']}/attachments",params=params,content=b'Bukti sintetis untuk pengujian.',headers=h)
    assert again.status_code==200 and again.json()==response.json()
    submit={'expected_revision':r['revision'],'request_key':key()}
    r=post(client,f"/api/sop-reports/{r['id']}/submit",h,submit)
    assert post(client,f"/api/sop-reports/{r['id']}/submit",h,submit)==r
    assert r['status']=='submitted' and len(r['history'])==1
    with database.SessionLocal() as db:
        for event in ('created','saved','evidence_added','submitted'):
            assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event=='sop_report.'+event))==1
        assert db.get(LabOrder,1).status=='submitted'
    post(client,f"/api/sop-reports/{r['id']}/save",h,{**data,'expected_revision':r['revision'],'request_key':key()},409)
    assert client.post(f"/api/sop-reports/{r['id']}/submit",json={'expected_revision':r['revision'],'request_key':key()}).status_code==403


def test_incomplete_checklist_findings_na_and_evidence_block_submission(client):
    h=login(client,'it');r,_=create(client,h)
    submit=lambda r:post(client,f"/api/sop-reports/{r['id']}/submit",h,{'expected_revision':r['revision'],'request_key':key()},422)
    submit(r)
    r,_=save(client,h,r,answers(r,result='issue',note='Ada gangguan layanan'))
    submit(r)
    r,_=save(client,h,r,answers(r,result='na',note='Tidak relevan pada shift ini'))
    submit(r)
    r,_=save(client,h,r,answers(r))
    assert 'lampiran' in submit(r)['detail'].lower()
    upload(client,h,r)
    rows=answers(r);rows[0].update(result='issue',note='Simulasi layanan terganggu',action='Periksa dan pulihkan layanan',owner='Petugas Demo',due=str(date.today()+timedelta(days=1)))
    r,_=save(client,h,r,rows)
    result=post(client,f"/api/sop-reports/{r['id']}/submit",h,{'expected_revision':r['revision'],'request_key':key()})
    assert result['results'][0]['result']=='issue' and result['status']=='submitted'


@pytest.mark.parametrize('filename,body',[('../bukti.txt',b'bukti'),('bukti.exe',b'MZexe'),('bukti.png',b'not an image'),('bukti.pdf',b'%PDF-1.7 /JavaScript test %%EOF'),('bukti.txt',b'abc\x00def'),('CON.txt',b'bukti')])
def test_unsafe_evidence_is_rejected(client,filename,body):
    h=login(client,'it');r,_=create(client,h)
    upload(client,h,r,filename=filename,body=body,expected=422)
    with database.SessionLocal() as db:assert db.scalar(select(func.count()).select_from(ReportAttachment))==0


def test_evidence_limits_context_and_private_download(client):
    h=login(client,'it');r,_=create(client,h)
    upload(client,h,r,body=b'x'*(MAX_FILE+1),expected=413)
    upload(client,h,r,item='not-an-item',expected=422)
    response,_=upload(client,h,r)
    ident=response.json()['attachment']['id'];path=f"/api/sop-reports/{r['id']}/attachments/{ident}"
    download=client.get(path)
    assert download.content==b'Bukti sintetis untuk pengujian.'
    assert download.headers['content-disposition'].startswith('attachment')
    assert 'sandbox' in download.headers['content-security-policy']
    for _ in range(7):upload(client,h,r)
    upload(client,h,r,expected=413)
    login(client,'hr');assert client.get(path).status_code==404
    login(client,'mitra');assert client.get(path).status_code==403


def test_review_return_resubmit_keeps_old_versions_and_evidence(client):
    h=login(client,'it');r=complete(client,h);path=f"/api/sop-reports/{r['id']}"
    old_id=r['attachments'][0]['id']
    post(client,path+'/review',h,{'expected_revision':r['revision'],'decision':'reviewed','note':'Tidak boleh memeriksa sendiri','request_key':key()},403)
    director=login(client,'direktur')
    data={'expected_revision':r['revision'],'decision':'returned','note':'Lengkapi bukti pemeriksaan ulang','request_key':key()}
    r=post(client,path+'/review',director,data)
    assert post(client,path+'/review',director,data)==r
    h=login(client,'it')
    r=client.get(path).json()
    remove={'expected_revision':r['revision'],'request_key':key()}
    removed=post(client,path+f'/attachments/{old_id}/remove',h,remove)
    assert post(client,path+f'/attachments/{old_id}/remove',h,remove)==removed
    r['revision']=removed['revision'];upload(client,h,r,filename='pemeriksaan-ulang.txt')
    r,_=save(client,h,r,summary='Pemeriksaan ulang fiktif selesai, bukti diganti')
    r=post(client,path+'/submit',h,{'expected_revision':r['revision'],'request_key':key()})
    assert len(r['history'])==3 and r['history'][0]['snapshot']['attachments'][0]['id']==old_id
    assert client.get(path+f'/attachments/{old_id}').status_code==200
    director=login(client,'direktur')
    data={'expected_revision':r['revision'],'decision':'reviewed','note':'Bukti pemeriksaan ulang sudah ditelaah','request_key':key()}
    r=post(client,path+'/review',director,data)
    assert r['status']=='reviewed' and len(r['history'])==4
    package=client.get(path+'/export')
    assert package.status_code==200
    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
        assert 'laporan.html' in archive.namelist() and 'riwayat.json' in archive.namelist()
        assert len([n for n in archive.namelist() if n.startswith('lampiran/')])==2
        assert len(json.loads(archive.read('riwayat.json')))==4
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(SopReportVersion))==4
        assert db.get(ReportAttachment,old_id).removed


def test_linked_order_assignment_and_state_rechecked_on_read_submit_export(client):
    h=assign_and_accept(client);r=complete(client,h,'LAB-01',1)
    path=f"/api/sop-reports/{r['id']}"
    with database.SessionLocal() as db:db.get(LabOrder,1).lead_id=12;db.commit()
    assert client.get(path).status_code==404
    assert client.get(path+'/export').status_code==404
    assert client.get(path+'/attachments/'+str(r['attachments'][0]['id'])).status_code==404
    with database.SessionLocal() as db:db.get(LabOrder,1).lead_id=3;db.get(LabOrder,1).status='production';db.commit()
    create_data={'sop_code':'LAB-01','report_day':str(date.today()),'order_id':1,'request_key':key()}
    post(client,'/api/sop-reports',h,create_data,409)


def test_stale_and_concurrent_edits_do_not_overwrite(client):
    h=login(client,'it');r,_=create(client,h)
    second=TestClient(appmod.app);second.cookies.update(client.cookies)
    data={'expected_revision':r['revision'],'summary':'Pemeriksaan fiktif versi pertama','results':answers(r),'request_key':key()}
    other={**data,'summary':'Pemeriksaan fiktif versi kedua','request_key':key()}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(client.post,f"/api/sop-reports/{r['id']}/save",json=data,headers=h),pool.submit(second.post,f"/api/sop-reports/{r['id']}/save",json=other,headers=h)]
        responses=[f.result() for f in futures]
    assert sorted(x.status_code for x in responses)==[200,409]
    with database.SessionLocal() as db:assert db.get(SopReport,r['id']).revision==2
    second.close()


def test_report_export_escapes_html_and_rejects_forged_shape(client):
    h=login(client,'it');r,_=create(client,h)
    r,_=save(client,h,r,summary='<script>alert(1)</script> Simulasi')
    html=client.get(f"/api/sop-reports/{r['id']}/export?format=html").text
    assert '<script>' not in html and '&lt;script&gt;' in html
    invalid={'expected_revision':r['revision'],'summary':'Simulasi','results':answers(r)[:-1],'request_key':key()}
    post(client,f"/api/sop-reports/{r['id']}/save",h,invalid,422)
    post(client,'/api/sop-reports',h,{'sop_code':'IT-01','report_day':str(date.today()+timedelta(days=1)),'request_key':key()},422)
    post(client,'/api/sop-reports',h,{'sop_code':'IT-01','report_day':str(date.today()),'org_id':2,'request_key':key()},422)
