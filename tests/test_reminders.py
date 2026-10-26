from datetime import datetime
from sqlalchemy import select
from app.db import Setting, Ticket, Reminder, Customer, Conversation
from app.reminders import business_minutes, process_reminders
from app.tickets import transition

def dt(text): return datetime.fromisoformat(text)

def isolated(session, priority='high', start='2026-10-19T08:00:00'):
    for t in session.scalars(select(Ticket)): t.status='Resolved'
    c=Customer(name='Reminder Test');session.add(c);session.flush()
    conv=Conversation(customer_id=c.id);session.add(conv);session.flush()
    t=Ticket(conversation_id=conv.id,subject='Test',summary='Test',priority=priority,reminder_since=dt(start))
    session.add(t);session.commit()
    return t

def test_business_minutes_weekend_and_closing(session):
    s=session.get(Setting,1)
    assert business_minutes(dt('2026-10-19T07:00:00'),dt('2026-10-19T08:15:00'),s)==15
    assert business_minutes(dt('2026-10-24T16:50:00'),dt('2026-10-26T09:10:00'),s)==20
    assert business_minutes(dt('2026-10-19T18:00:00'),dt('2026-10-20T07:00:00'),s)==0
    assert business_minutes(dt('2026-10-20T08:00:00'),dt('2026-10-19T08:00:00'),s)==0

def test_high_threshold_dedup_owner_and_restart(session):
    t=isolated(session)
    assert process_reminders(session,dt('2026-10-19T08:14:00'))==0
    assert process_reminders(session,dt('2026-10-19T08:15:00'))==1
    assert process_reminders(session,dt('2026-10-19T08:30:00'))==0
    assert process_reminders(session,dt('2026-10-19T09:00:00'))==1
    session.expire_all()
    assert process_reminders(session,dt('2026-10-19T10:00:00'))==0
    rows=list(session.scalars(select(Reminder).where(Reminder.ticket_id==t.id)))
    assert {r.kind for r in rows}=={'staff','owner'}
    assert next(r for r in rows if r.kind=='owner').recipient=='Elena Vega'

def test_standard_threshold_and_pause(session):
    t=isolated(session,'standard')
    assert process_reminders(session,dt('2026-10-19T08:15:00'))==0
    assert process_reminders(session,dt('2026-10-19T08:30:00'))==1
    transition(session,t,'Waiting for Customer');session.commit()
    assert process_reminders(session,dt('2026-10-19T10:00:00'))==0
    assert all(r.acknowledged for r in session.scalars(select(Reminder).where(Reminder.ticket_id==t.id)))
    transition(session,t,'In Progress');t.reminder_since=dt('2026-10-19T10:00:00');session.commit()
    assert t.reminder_cycle==2
    assert process_reminders(session,dt('2026-10-19T10:30:00'))==1
    transition(session,t,'Resolved');session.commit()
    assert process_reminders(session,dt('2026-10-19T12:00:00'))==0

def test_closed_hours_defer_delivery(session):
    isolated(session,start='2026-10-24T16:40:00')
    assert process_reminders(session,dt('2026-10-24T18:00:00'))==0
    assert process_reminders(session,dt('2026-10-25T12:00:00'))==0
    assert process_reminders(session,dt('2026-10-26T09:00:00'))==1

def test_config_validation_persistence(client):
    rules={'high_minutes':10,'standard_minutes':20,'owner_minutes':45,'open_hour':9,'close_hour':18,'weekdays':[0,1,2,3,4]}
    assert client.put('/api/settings',json=rules).status_code==200
    assert client.get('/api/settings').json()['high_minutes']==10
    assert client.put('/api/settings',json={**rules,'close_hour':8}).status_code==422
    assert client.put('/api/settings',json={**rules,'weekdays':[]}).status_code==422
    assert client.put('/api/settings',json={**rules,'owner_minutes':1}).status_code==422

def test_reminder_dedup_survives_new_app_instance(tmp_path):
    from app.main import create_app
    url=f'sqlite:///{tmp_path}/restart.db'
    first=create_app(url,reminders_enabled=False)
    with first.state.session_factory() as s:
        t=isolated(s)
        assert process_reminders(s,dt('2026-10-19T08:15:00'))==1
        setting=s.get(Setting,1);setting.owner_minutes=90;s.commit()
    second=create_app(url,reminders_enabled=False)
    with second.state.session_factory() as s:
        assert s.get(Setting,1).owner_minutes==90
        assert process_reminders(s,dt('2026-10-19T08:30:00'))==0
        assert process_reminders(s,dt('2026-10-19T09:30:00'))==1
