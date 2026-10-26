from fastapi.testclient import TestClient
from app.main import create_app

def create(client):
    c = client.post('/api/conversations',json={'name':'Test customer'}).json()
    c = client.post(f"/api/conversations/{c['id']}/messages",json={'body':'Quiero un anillo de oro hasta 900 €'}).json()
    return c['id'], c['ticket_id']

def test_full_lifecycle_and_human_takeover(client):
    cid, tid = create(client)
    ticket = client.get(f'/api/tickets/{tid}').json()
    assert ticket['priority'] == 'high' and ticket['status'] == 'New'
    assert client.patch(f'/api/tickets/{tid}',json={'status':'In Progress','employee_id':2,'human_takeover':True}).status_code == 200
    assert client.post(f'/api/tickets/{tid}/notes',json={'body':'Only staff can see this','employee_id':2}).status_code == 201
    messages = client.get(f'/api/conversations/{cid}').json()['messages']
    c = client.post(f'/api/conversations/{cid}/messages',json={'body':'¿Me ayudas?'}).json()
    assert len(c['messages']) == len(messages)+1 and c['messages'][-1]['role']=='customer'
    assert 'notes' not in c
    assert client.post(f'/api/tickets/{tid}/reply',json={'body':'¿Qué talla necesitas?','employee_id':2}).status_code == 201
    assert client.get(f'/api/tickets/{tid}').json()['status']=='Waiting for Customer'
    client.post(f'/api/conversations/{cid}/messages',json={'body':'Talla 14'})
    assert client.get(f'/api/tickets/{tid}').json()['status']=='In Progress'
    assert client.patch(f'/api/tickets/{tid}',json={'status':'Resolved'}).status_code == 200
    assert client.post(f'/api/tickets/{tid}/reply',json={'body':'invalid','employee_id':2}).status_code==409
    client.post(f'/api/conversations/{cid}/messages',json={'body':'Otra consulta'})
    ticket=client.get(f'/api/tickets/{tid}').json()
    assert ticket['status']=='Reopened' and ticket['notes'][0]['body']=='Only staff can see this'
    assert len(ticket['activity'])>=6
    assert len([t for t in client.get('/api/dashboard').json()['tickets'] if t['conversation_id']==cid])==1

def test_transition_and_validation(client):
    _, tid = create(client)
    assert client.patch(f'/api/tickets/{tid}',json={'status':'Reopened'}).status_code==409
    assert client.patch(f'/api/tickets/{tid}',json={'employee_id':999}).status_code==404
    assert client.post(f'/api/tickets/{tid}/notes',json={'body':'  ','employee_id':1}).status_code==422
    assert client.get('/api/tickets/999').status_code==404
    client.patch(f'/api/tickets/{tid}',json={'employee_id':1})
    assert client.get('/api/dashboard',params={'q':'Test customer','priority':'high','employee_id':'1'}).json()['tickets'][0]['id']==tid

def test_restart_persistence(tmp_path):
    url=f'sqlite:///{tmp_path}/persist.db'
    with TestClient(create_app(url,reminders_enabled=False)) as c:
        cid,tid=create(c)
        c.patch(f'/api/tickets/{tid}',json={'employee_id':3,'status':'In Progress','human_takeover':True})
        c.post(f'/api/tickets/{tid}/notes',json={'body':'Persist this note','employee_id':3})
        count=len(c.get('/api/dashboard').json()['tickets'])
    with TestClient(create_app(url,reminders_enabled=False)) as c:
        t=c.get(f'/api/tickets/{tid}').json()
        assert t['employee_id']==3 and t['status']=='In Progress' and t['human_takeover']
        assert t['notes'][0]['body']=='Persist this note'
        assert len(c.get('/api/dashboard').json()['tickets'])==count
        assert len(c.get('/api/products').json())==24

def test_english_and_manual_ticket(client):
    c=client.post('/api/conversations',json={'language':'en'}).json()
    assert 'Hello' in c['messages'][0]['body']
    c=client.post(f"/api/conversations/{c['id']}/ticket").json()
    assert c['human_takeover'] and c['ticket_id'] and 'team' in c['messages'][-1]['body']
