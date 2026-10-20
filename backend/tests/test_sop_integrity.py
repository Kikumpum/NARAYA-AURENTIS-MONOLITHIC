from datetime import date
from sqlalchemy import func, select
from test_api import client, login, post, assign_and_accept
from test_sop_reports import create, save, upload, key
from backend import database
from backend.models import LabOrder, ReportAttachment, SopReport, SopReportVersion
from backend.modules.sop_reports import MAX_RETAINED


def test_submit_rechecks_order_state_and_create_retry_rechecks_assignment(client):
    h=assign_and_accept(client)
    r,original=create(client,h,'LAB-01',1);r,_=save(client,h,r);upload(client,h,r)
    with database.SessionLocal() as db:db.get(LabOrder,1).status='production';db.commit()
    post(client,f"/api/sop-reports/{r['id']}/submit",h,{'expected_revision':r['revision'],'request_key':key()},409)
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(SopReportVersion))==0
        assert db.get(SopReport,r['id']).status=='draft'
        db.get(LabOrder,1).lead_id=12;db.commit()
    post(client,'/api/sop-reports',h,original,404)


def test_upload_replay_rejects_changed_body_and_retained_quota(client):
    h=login(client,'it');r,_=create(client,h)
    response,params=upload(client,h,r)
    changed=client.post(f"/api/sop-reports/{r['id']}/attachments",params=params,content=b'Isi berbeda',headers=h)
    assert changed.status_code==409
    with database.SessionLocal() as db:
        a=db.get(ReportAttachment,response.json()['attachment']['id'])
        a.size=MAX_RETAINED;a.removed=True;db.commit()
    upload(client,h,r,expected=413)


def test_report_moved_to_other_tenant_is_unavailable_even_to_author(client):
    h=login(client,'it');r,_=create(client,h);path=f"/api/sop-reports/{r['id']}"
    with database.SessionLocal() as db:db.get(SopReport,r['id']).org_id=2;db.commit()
    assert client.get(path).status_code==404
    assert client.get(path+'/export').status_code==404
    assert client.get('/api/sop-reports').json()==[]
