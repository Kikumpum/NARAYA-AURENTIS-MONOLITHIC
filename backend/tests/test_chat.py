"""AI-first support privacy, workflow, duplicate requests and audit evidence."""
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select

from backend import database
from backend.models import Audit, Base, ChatConversation, ChatMessage, Org, User
from backend.tests.test_api import appmod, client, login, post
from backend.utils import pwd_hash


def start(client,headers,order=None,key='start-demo-0001'):
    return post(client,'/api/chat/conversations',headers,{'request_id':key,'order_id':order})


def send(client,headers,ident,body='Bagaimana status order?',key='message-demo-0001',expected=200):
    return post(client,f'/api/chat/conversations/{ident}/messages',headers,{'request_id':key,'body':body},expected=expected)


def test_assistant_first_idempotency_and_content_safety(client):
    headers=login(client,'pasien')
    chat=start(client,headers,1)
    assert chat['status']=='assistant' and chat['assistant_mode']=='mock'
    assert start(client,headers,1)['id']==chat['id']
    path=f"/api/chat/conversations/{chat['id']}"
    assert len(client.get(path).json()['messages'])==1
    send(client,headers,chat['id'])
    assert send(client,headers,chat['id'])['duplicate'] is True
    transcript=client.get(path).json()['messages']
    assert [message['sender'] for message in transcript]==['assistant','user','assistant']
    assert 'LAB-DEMO-001' in transcript[-1]['body']
    assert 'menunggu penugasan' in transcript[-1]['body']
    send(client,headers,chat['id'],'Bagaimana dosis obat?','medical-demo-001')
    assert 'dokter gigi' in client.get(path).json()['messages'][-1]['body']
    send(client,headers,chat['id'],'Screenshot QRIS sudah berhasil?','payment-demo-001')
    assert 'belum menyatakan pembayaran berhasil' in client.get(path).json()['messages'][-1]['body']
    send(client,headers,chat['id'],'Isi berbeda dengan kunci yang sama',expected=409)
    with database.SessionLocal() as db:
        events=db.scalars(select(Audit).where(Audit.event.like('chat.%'))).all()
        assert sum(row.event=='chat.started' for row in events)==1
        assert sum(row.event=='chat.message_recorded' for row in events)==3
        assert all('dosis' not in row.detail for row in events)


def test_order_context_and_conversation_tenant_scope(client):
    patient=login(client,'pasien')
    chat=start(client,patient,1)
    post(client,'/api/chat/conversations',patient,{'request_id':'forbidden-order-01','order_id':2},expected=404)
    partner=login(client,'mitra')
    assert client.get('/api/chat/conversations').status_code==403
    path=f"/api/chat/conversations/{chat['id']}"
    assert client.get(path).status_code==404
    send(client,partner,chat['id'],expected=404)
    post(client,path+'/handoff',partner,expected=404)
    post(client,path+'/close',partner,expected=404)
    for username in ('it','resepsionis','direktur','dokter'):
        login(client,username)
        assert client.get(path).status_code==404
        assert client.get('/api/chat/queue').status_code==403


def test_handoff_claim_reply_close_and_no_ai_after_handoff(client):
    patient=login(client,'pasien')
    chat=start(client,patient,1)
    ident=chat['id']; path=f'/api/chat/conversations/{ident}'
    post(client,path+'/handoff',patient)
    post(client,path+'/handoff',patient)
    send(client,patient,ident,'Mohon bantuan petugas')
    messages=client.get(path).json()['messages']
    assert messages[-1]['sender']=='user'
    assert sum(message['sender']=='assistant' for message in messages)==1
    cs=login(client,'cs')
    queue=client.get('/api/chat/queue').json()
    assert queue[0]['id']==ident and 'messages' not in queue[0]
    assert not any(key in queue[0] for key in ('owner_id','name','phone','body'))
    assert client.get(path).status_code==404
    send(client,cs,ident,expected=404)
    post(client,path+'/claim',cs)
    post(client,path+'/claim',cs)
    send(client,cs,ident,'Selamat siang, saya petugas CS. Apa yang perlu dibantu?','cs-message-demo-01')
    patient=login(client,'pasien')
    messages=client.get(path).json()['messages']
    assert messages[-1]['sender']=='agent'
    assert messages[-1]['body'].startswith('Selamat siang')
    send(client,patient,ident,'Terima kasih, bantuan sudah cukup.','patient-message-02')
    post(client,path+'/close',patient)
    post(client,path+'/close',patient)
    send(client,patient,ident,'Pesan setelah tutup','closed-message-01',409)
    assert client.get(path).json()['status']=='closed'
    with database.SessionLocal() as db:
        for event in ('chat.handoff_requested','chat.claimed','chat.closed'):
            assert db.scalar(select(func.count()).select_from(Audit).where(Audit.event==event))==1


def test_claim_rejects_wrong_workflow_and_role(client):
    patient=login(client,'pasien')
    ident=start(client,patient)['id']; path=f'/api/chat/conversations/{ident}'
    post(client,path+'/claim',patient,expected=403)
    cs=login(client,'cs')
    post(client,path+'/claim',cs,expected=409)
    assert client.get(path).status_code==404


def add_agent(username,org=1):
    with database.SessionLocal() as db:
        db.add(User(username=username,display_name='Petugas simulasi',role='customer_service',
                    org_id=org,password_hash=pwd_hash('DemoNAM2026!'),active=True))
        db.commit()


def test_only_one_agent_can_claim_and_other_agent_cannot_read(client):
    patient=login(client,'pasien'); ident=start(client,patient)['id']
    post(client,f'/api/chat/conversations/{ident}/handoff',patient)
    add_agent('cs2')
    agent1=TestClient(appmod.app); agent2=TestClient(appmod.app)
    first=login(agent1,'cs'); second=login(agent2,'cs2')
    path=f'/api/chat/conversations/{ident}'
    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts=[pool.submit(agent1.post,path+'/claim',headers=first),pool.submit(agent2.post,path+'/claim',headers=second)]
        responses=[future.result() for future in attempts]
    assert sorted(response.status_code for response in responses)==[200,409]
    winner,loser=(agent1,agent2) if responses[0].status_code==200 else (agent2,agent1)
    assert winner.get(path).status_code==200
    assert loser.get(path).status_code==404
    assert loser.get('/api/chat/queue').json()==[]
    with database.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.request_key=='claimed'))==1
    agent1.close(); agent2.close()


def test_patient_handoff_has_explicit_service_routing(client):
    patient=login(client,'pasien'); ident=start(client,patient,1)['id']
    post(client,f'/api/chat/conversations/{ident}/handoff',patient)
    add_agent('cs-mitra',2)
    bad=login(client,'cs-mitra')
    assert client.get('/api/chat/queue').status_code==403
    post(client,f'/api/chat/conversations/{ident}/claim',bad,expected=403)
    good=login(client,'cs')
    post(client,f'/api/chat/conversations/{ident}/claim',good)
    assert client.get(f'/api/chat/conversations/{ident}').status_code==200
    # Support transcript authorization does not grant clinical order authorization.
    assert client.get('/api/orders/2').status_code==404


def test_csrf_and_empty_message_validation(client):
    headers=login(client,'pasien'); ident=start(client,headers)['id']
    path=f'/api/chat/conversations/{ident}'
    assert client.post(path+'/handoff').status_code==403
    assert client.post(path+'/messages',json={'body':'Tidak sah','request_id':'missing-csrf-0001'}).status_code==403
    send(client,headers,ident,'  ','blank-message-01',422)
    send(client,headers,ident,'x'*2001,'long-message-01',422)
    post(client,path+'/close',headers)
    post(client,path+'/handoff',headers,expected=409)


def test_migration_adopts_existing_demo_and_preserves_data(tmp_path,monkeypatch):
    engine=create_engine(f'sqlite:///{tmp_path}/legacy.db')
    legacy=[table for table in Base.metadata.sorted_tables if not table.name.startswith(('chat_','patient_','visit_','whatsapp_'))]
    Base.metadata.create_all(engine,tables=legacy)
    with engine.begin() as connection:
        connection.execute(Org.__table__.insert(),{'id':1,'name':'Data demo tersimpan','kind':'internal'})
    monkeypatch.setattr(database,'engine',engine)
    database.upgrade_schema(); database.upgrade_schema()
    with engine.connect() as connection:
        assert connection.scalar(select(Org.name).where(Org.id==1))=='Data demo tersimpan'
        assert connection.scalar(select(func.count()).select_from(ChatConversation))==0
    engine.dispose()
