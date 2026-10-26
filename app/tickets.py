from sqlalchemy import select
from .db import Ticket, Activity, Reminder, now

TRANSITIONS = {
    'New': ['Waiting for Staff', 'In Progress', 'Waiting for Customer', 'Resolved'],
    'Waiting for Staff': ['In Progress', 'Waiting for Customer', 'Resolved'],
    'In Progress': ['Waiting for Staff', 'Waiting for Customer', 'Resolved'],
    'Waiting for Customer': ['In Progress', 'Waiting for Staff', 'Resolved'],
    'Resolved': ['Reopened'],
    'Reopened': ['Waiting for Staff', 'In Progress', 'Waiting for Customer', 'Resolved'],
}


def event(session, ticket, body):
    session.add(Activity(ticket_id=ticket.id, body=body))
    ticket.updated_at = now()


def clear_reminders(session, ticket):
    for r in session.scalars(select(Reminder).where(Reminder.ticket_id == ticket.id, Reminder.acknowledged.is_(False))):
        r.acknowledged = True


def transition(session, ticket, status):
    if status == ticket.status:
        return
    if status not in TRANSITIONS[ticket.status]:
        raise ValueError(f'Invalid transition: {ticket.status} → {status}')
    old = ticket.status
    if status in {'Waiting for Customer', 'Resolved'}:
        clear_reminders(session, ticket)
    if old in {'Waiting for Customer', 'Resolved'}:
        ticket.reminder_cycle += 1
        ticket.reminder_since = now()
    ticket.status = status
    event(session, ticket, f'Estado: {old} → {status}')


def ensure_ticket(session, conversation, subject, summary, priority='standard'):
    ticket = session.scalar(select(Ticket).where(Ticket.conversation_id == conversation.id))
    if not ticket:
        ticket = Ticket(conversation_id=conversation.id, subject=subject, summary=summary, priority=priority)
        session.add(ticket)
        session.flush()
        event(session, ticket, 'Consulta creada desde el simulador')
    else:
        if ticket.status == 'Resolved':
            transition(session, ticket, 'Reopened')
        elif ticket.status == 'Waiting for Customer':
            transition(session, ticket, 'In Progress')
        ticket.summary = summary
        if priority == 'high' and ticket.priority != 'high':
            ticket.priority = 'high'
            event(session, ticket, 'Prioridad elevada: oportunidad de venta')
    return ticket
