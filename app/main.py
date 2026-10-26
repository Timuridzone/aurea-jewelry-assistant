import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from .db import database, Customer, Conversation, Message, Product, Ticket, Employee, Note, Activity, Reminder, Setting
from .seed import seed
from .catalog import product_dict
from .assistant import answer
from .tickets import TRANSITIONS, transition, ensure_ticket, event
from .reminders import process_reminders


class NewConversation(BaseModel):
    name: str = Field(default='Visitante', min_length=1, max_length=80)
    language: Literal['es', 'en'] = 'es'


class TextInput(BaseModel):
    body: str = Field(min_length=1, max_length=3000)
    @model_validator(mode='after')
    def clean(self):
        self.body = self.body.strip()
        if not self.body:
            raise ValueError('Write a message first')
        return self


class TicketUpdate(BaseModel):
    status: str | None = None
    employee_id: int | None = None
    priority: Literal['standard', 'high'] | None = None
    human_takeover: bool | None = None


class StaffText(TextInput):
    employee_id: int


class Rules(BaseModel):
    high_minutes: int = Field(ge=1, le=1440)
    standard_minutes: int = Field(ge=1, le=1440)
    owner_minutes: int = Field(ge=1, le=2880)
    open_hour: int = Field(ge=0, le=23)
    close_hour: int = Field(ge=1, le=24)
    weekdays: list[int] = Field(min_length=1, max_length=7)
    @model_validator(mode='after')
    def valid(self):
        if self.close_hour <= self.open_hour or any(d not in range(7) for d in self.weekdays) or len(set(self.weekdays)) != len(self.weekdays):
            raise ValueError('Invalid business hours')
        if self.owner_minutes < max(self.high_minutes, self.standard_minutes):
            raise ValueError('Owner threshold must be at least the staff threshold')
        return self


def record(obj):
    return {c.name: (getattr(obj, c.name).isoformat() + 'Z' if c.type.python_type.__name__ == 'datetime' else getattr(obj, c.name)) for c in obj.__table__.columns}


def create_app(url=None, reminders_enabled=True):
    engine, factory = database(url)
    with factory() as s:
        seed(s)

    @asynccontextmanager
    async def lifespan(app):
        async def loop():
            while True:
                def tick():
                    with factory() as s:
                        process_reminders(s)
                try:
                    await asyncio.to_thread(tick)
                except Exception:
                    import logging
                    logging.exception('Reminder sweep failed; retrying next minute')
                await asyncio.sleep(60)
        task = asyncio.create_task(loop()) if reminders_enabled else None
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        engine.dispose()

    app = FastAPI(title='Áurea · Jewelry assistant demo', lifespan=lifespan)
    app.state.session_factory = factory

    def get(s, cls, id):
        obj = s.get(cls, id)
        if not obj:
            raise HTTPException(404, 'Record not found')
        return obj

    def conversation_data(s, c):
        data = record(c)
        data['customer'] = record(s.get(Customer, c.customer_id))
        data['messages'] = []
        for m in s.scalars(select(Message).where(Message.conversation_id == c.id).order_by(Message.id)):
            row = record(m)
            row['products'] = [product_dict(p) for id in m.product_ids if (p := s.get(Product, id))]
            data['messages'].append(row)
        ticket = s.scalar(select(Ticket).where(Ticket.conversation_id == c.id))
        data['ticket_id'] = ticket.id if ticket else None
        return data

    def ticket_data(s, t):
        d = record(t)
        c = s.get(Conversation, t.conversation_id)
        d['customer_name'] = s.get(Customer, c.customer_id).name
        e = s.get(Employee, t.employee_id) if t.employee_id else None
        d['employee_name'] = e.name if e else None
        d['human_takeover'] = c.human_takeover
        return d

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'demo': True}

    @app.get('/api/products')
    def products():
        with factory() as s:
            return [product_dict(p) for p in s.scalars(select(Product))]

    @app.post('/api/conversations', status_code=201)
    def create_conversation(body: NewConversation):
        with factory() as s:
            customer = Customer(name=body.name.strip() or 'Visitante'); s.add(customer); s.flush()
            c = Conversation(customer_id=customer.id, language=body.language); s.add(c); s.flush()
            greeting = '¡Hola! Soy el asistente de Áurea. ¿Buscas una joya especial? Cuéntame para quién es y tu presupuesto. Este es un entorno ficticio de demostración.' if body.language == 'es' else 'Hello! I am the Áurea assistant. What piece are you looking for, and what is your budget? This is a fictional demo environment.'
            s.add(Message(conversation_id=c.id, role='assistant', body=greeting)); s.commit()
            return conversation_data(s, c)

    @app.get('/api/conversations/{id}')
    def read_conversation(id: int):
        with factory() as s:
            return conversation_data(s, get(s, Conversation, id))

    @app.post('/api/conversations/{id}/messages')
    def message(id: int, body: TextInput):
        with factory() as s:
            c = get(s, Conversation, id)
            s.add(Message(conversation_id=id, role='customer', body=body.body))
            response, ids = answer(s, c, body.body)
            if response:
                s.add(Message(conversation_id=id, role='assistant', body=response, product_ids=ids))
            s.commit()
            return conversation_data(s, c)

    @app.post('/api/conversations/{id}/ticket')
    def create_ticket(id: int):
        with factory() as s:
            c = get(s, Conversation, id)
            messages = list(s.scalars(select(Message).where(Message.conversation_id == id, Message.role == 'customer').order_by(Message.id.desc()).limit(3)))
            t = ensure_ticket(s, c, 'Solicitud de atención personal', '\n'.join(m.body for m in reversed(messages)) or 'El cliente solicita atención personal.')
            if t.status in {'New', 'Reopened'}:
                transition(s, t, 'Waiting for Staff')
            c.human_takeover = True
            s.add(Message(conversation_id=id, role='assistant', body=f'Ticket #{t.id} sent to the team. The assistant is paused.' if c.language == 'en' else f'Consulta #{t.id} enviada al equipo. El asistente queda en pausa.'))
            s.commit()
            return conversation_data(s, c)

    @app.get('/api/dashboard')
    def dashboard(q: str = '', status: str = '', priority: str = '', employee_id: str = ''):
        with factory() as s:
            rows = [ticket_data(s, t) for t in s.scalars(select(Ticket).order_by(Ticket.updated_at.desc(), Ticket.id.desc()))]
            counts = {'open': sum(t['status'] != 'Resolved' for t in rows), 'high': sum(t['priority'] == 'high' and t['status'] != 'Resolved' for t in rows), 'waiting': sum(t['status'] == 'Waiting for Staff' for t in rows), 'resolved': sum(t['status'] == 'Resolved' for t in rows)}
            filtered = [t for t in rows if (not q or q.lower() in (t['customer_name'] + t['subject'] + t['summary'] + str(t['id'])).lower()) and (not status or t['status'] == status) and (not priority or t['priority'] == priority) and (not employee_id or str(t['employee_id'] or 'unassigned') == employee_id)]
            return {'tickets': filtered, 'counts': counts, 'employees': [record(e) for e in s.scalars(select(Employee))], 'reminders': [record(r) for r in s.scalars(select(Reminder).where(Reminder.acknowledged.is_(False)).order_by(Reminder.created_at.desc()))], 'transitions': TRANSITIONS}

    @app.get('/api/tickets/{id}')
    def read_ticket(id: int):
        with factory() as s:
            t = get(s, Ticket, id)
            return {**ticket_data(s, t), 'conversation': conversation_data(s, s.get(Conversation, t.conversation_id)), 'notes': [record(n) for n in s.scalars(select(Note).where(Note.ticket_id == id).order_by(Note.id))], 'activity': [record(a) for a in s.scalars(select(Activity).where(Activity.ticket_id == id).order_by(Activity.id.desc()))], 'allowed_statuses': TRANSITIONS[t.status]}

    @app.patch('/api/tickets/{id}')
    def update_ticket(id: int, body: TicketUpdate):
        with factory() as s:
            t = get(s, Ticket, id)
            if body.status:
                try:
                    transition(s, t, body.status)
                except ValueError as exc:
                    raise HTTPException(409, str(exc))
            if 'employee_id' in body.model_fields_set:
                e = get(s, Employee, body.employee_id) if body.employee_id else None
                t.employee_id = e.id if e else None
                event(s, t, 'Asignación: ' + (e.name if e else 'Sin asignar'))
            if body.priority and body.priority != t.priority:
                t.priority = body.priority; event(s, t, 'Prioridad: ' + body.priority)
            if body.human_takeover is not None:
                c = s.get(Conversation, t.conversation_id)
                c.human_takeover = body.human_takeover
                event(s, t, 'Atención humana activada' if body.human_takeover else 'Asistente reactivado')
            s.commit()
            return ticket_data(s, t)

    @app.post('/api/tickets/{id}/notes', status_code=201)
    def note(id: int, body: StaffText):
        with factory() as s:
            t = get(s, Ticket, id); e = get(s, Employee, body.employee_id)
            s.add(Note(ticket_id=id, employee_id=e.id, body=body.body))
            event(s, t, f'{e.name} añadió una nota interna'); s.commit()
            return {'ok': True}

    @app.post('/api/tickets/{id}/reply', status_code=201)
    def reply(id: int, body: StaffText):
        with factory() as s:
            t = get(s, Ticket, id); e = get(s, Employee, body.employee_id)
            if t.status == 'Resolved':
                raise HTTPException(409, 'Reopen this ticket before replying')
            c = s.get(Conversation, t.conversation_id); c.human_takeover = True
            s.add(Message(conversation_id=c.id, role='staff', body=body.body))
            transition(s, t, 'Waiting for Customer')
            event(s, t, f'{e.name} respondió al cliente'); s.commit()
            return {'ok': True}

    @app.get('/api/settings')
    def settings():
        with factory() as s:
            return record(s.get(Setting, 1))

    @app.put('/api/settings')
    def save_settings(body: Rules):
        with factory() as s:
            setting = s.get(Setting, 1)
            for key, value in body.model_dump().items():
                setattr(setting, key, value)
            s.commit()
            return record(setting)

    @app.post('/api/reminders/run')
    def run_reminders():
        with factory() as s:
            return {'created': process_reminders(s)}

    @app.post('/api/reminders/{id}/acknowledge')
    def acknowledge(id: int):
        with factory() as s:
            r = get(s, Reminder, id)
            if not r.acknowledged:
                r.acknowledged = True
                event(s, s.get(Ticket, r.ticket_id), 'Recordatorio marcado como visto')
            s.commit()
            return {'ok': True}

    static = Path(__file__).parent / 'static'
    app.mount('/static', StaticFiles(directory=static), name='static')
    @app.get('/')
    def index():
        return FileResponse(static / 'index.html')
    return app
