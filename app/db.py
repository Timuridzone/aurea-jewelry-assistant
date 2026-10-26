import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, event, ForeignKey, String, Text, Integer, Boolean, JSON, DateTime, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str]
    price_cents: Mapped[int]
    material: Mapped[str]
    style: Mapped[str]
    description: Mapped[str] = mapped_column(Text)
    available: Mapped[bool] = mapped_column(default=True)


class Customer(Base):
    __tablename__ = 'customers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class Employee(Base):
    __tablename__ = 'employees'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    role: Mapped[str]


class Conversation(Base):
    __tablename__ = 'conversations'
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'))
    language: Mapped[str] = mapped_column(default='es')
    channel: Mapped[str] = mapped_column(default='simulator')
    human_takeover: Mapped[bool] = mapped_column(default=False)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('conversations.id'), index=True)
    role: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    product_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Ticket(Base):
    __tablename__ = 'tickets'
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('conversations.id'), unique=True)
    subject: Mapped[str]
    summary: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(default='standard')
    status: Mapped[str] = mapped_column(default='New')
    employee_id: Mapped[int | None] = mapped_column(ForeignKey('employees.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    reminder_since: Mapped[datetime] = mapped_column(DateTime, default=now)
    reminder_cycle: Mapped[int] = mapped_column(default=1)


class Note(Base):
    __tablename__ = 'notes'
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey('tickets.id'))
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Activity(Base):
    __tablename__ = 'activity_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey('tickets.id'), index=True)
    body: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Reminder(Base):
    __tablename__ = 'reminders'
    __table_args__ = (UniqueConstraint('ticket_id', 'cycle', 'kind'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey('tickets.id'))
    cycle: Mapped[int]
    kind: Mapped[str]
    recipient: Mapped[str]
    acknowledged: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Setting(Base):
    __tablename__ = 'settings'
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    high_minutes: Mapped[int] = mapped_column(default=15)
    standard_minutes: Mapped[int] = mapped_column(default=30)
    owner_minutes: Mapped[int] = mapped_column(default=60)
    open_hour: Mapped[int] = mapped_column(default=10)
    close_hour: Mapped[int] = mapped_column(default=19)
    weekdays: Mapped[list] = mapped_column(JSON, default=lambda: [0, 1, 2, 3, 4, 5])
    timezone: Mapped[str] = mapped_column(default='Europe/Madrid')


def database(url=None):
    default = Path(__file__).resolve().parent.parent / 'data' / 'aurea.db'
    default.parent.mkdir(exist_ok=True)
    engine = create_engine(url or os.getenv('DATABASE_URL', f'sqlite:///{default}'), connect_args={'check_same_thread': False, 'timeout': 20})
    @event.listens_for(engine, 'connect')
    def setup(conn, record):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA journal_mode=WAL')
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
