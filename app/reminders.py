from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import Ticket, Setting, Reminder, Employee, Activity, now

ACTIVE = {'New', 'Waiting for Staff', 'In Progress', 'Reopened'}


def business_minutes(start, end, setting):
    zone = ZoneInfo(setting.timezone)
    start = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
    end = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
    if end <= start:
        return 0
    day, last = start.astimezone(zone).date(), end.astimezone(zone).date()
    seconds = 0
    while day <= last:
        if day.weekday() in setting.weekdays:
            opening = datetime(day.year, day.month, day.day, setting.open_hour, tzinfo=zone).astimezone(timezone.utc)
            closing = (datetime(day.year, day.month, day.day, tzinfo=zone) + timedelta(hours=setting.close_hour)).astimezone(timezone.utc)
            seconds += max(0, (min(end, closing) - max(start, opening)).total_seconds())
        day += timedelta(days=1)
    return seconds / 60


def process_reminders(session, at=None):
    at = at or now()
    setting = session.get(Setting, 1)
    local = at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(setting.timezone))
    if local.weekday() not in setting.weekdays or not setting.open_hour <= local.hour < setting.close_hour:
        return 0
    count = 0
    for ticket in session.scalars(select(Ticket).where(Ticket.status.in_(ACTIVE))):
        minutes = business_minutes(ticket.reminder_since, at, setting)
        employee = session.get(Employee, ticket.employee_id) if ticket.employee_id else None
        owner = session.scalar(select(Employee).where(Employee.role == 'owner'))
        thresholds = [('staff', setting.high_minutes if ticket.priority == 'high' else setting.standard_minutes, employee.name if employee else 'Equipo'), ('owner', setting.owner_minutes, owner.name if owner else 'Responsable')]
        for kind, threshold, recipient in thresholds:
            if minutes < threshold:
                continue
            exists = session.scalar(select(Reminder.id).where(Reminder.ticket_id == ticket.id, Reminder.cycle == ticket.reminder_cycle, Reminder.kind == kind))
            if exists:
                continue
            try:
                with session.begin_nested():
                    session.add(Reminder(ticket_id=ticket.id, cycle=ticket.reminder_cycle, kind=kind, recipient=recipient, created_at=at))
                    session.flush()
                    session.add(Activity(ticket_id=ticket.id, body=f'Recordatorio {kind} → {recipient}', created_at=at))
                count += 1
            except IntegrityError:
                pass  # Unique key also protects overlapping workers.
    session.commit()
    return count
