-- Generated from app/db.py. Schema is initialized automatically on startup.
PRAGMA foreign_keys=ON;

CREATE TABLE customers (
	id INTEGER NOT NULL,
	name VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE employees (
	id INTEGER NOT NULL,
	name VARCHAR NOT NULL,
	role VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE products (
	id INTEGER NOT NULL,
	name VARCHAR(120) NOT NULL,
	category VARCHAR NOT NULL,
	price_cents INTEGER NOT NULL,
	material VARCHAR NOT NULL,
	style VARCHAR NOT NULL,
	description TEXT NOT NULL,
	available BOOLEAN NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE settings (
	id INTEGER NOT NULL,
	high_minutes INTEGER NOT NULL,
	standard_minutes INTEGER NOT NULL,
	owner_minutes INTEGER NOT NULL,
	open_hour INTEGER NOT NULL,
	close_hour INTEGER NOT NULL,
	weekdays JSON NOT NULL,
	timezone VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE conversations (
	id INTEGER NOT NULL,
	customer_id INTEGER NOT NULL,
	language VARCHAR NOT NULL,
	channel VARCHAR NOT NULL,
	human_takeover BOOLEAN NOT NULL,
	preferences JSON NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(customer_id) REFERENCES customers (id)
)

;

CREATE TABLE messages (
	id INTEGER NOT NULL,
	conversation_id INTEGER NOT NULL,
	role VARCHAR NOT NULL,
	body TEXT NOT NULL,
	product_ids JSON NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(conversation_id) REFERENCES conversations (id)
)

;
CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);

CREATE TABLE tickets (
	id INTEGER NOT NULL,
	conversation_id INTEGER NOT NULL,
	subject VARCHAR NOT NULL,
	summary TEXT NOT NULL,
	priority VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	employee_id INTEGER,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	reminder_since DATETIME NOT NULL,
	reminder_cycle INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (conversation_id),
	FOREIGN KEY(conversation_id) REFERENCES conversations (id),
	FOREIGN KEY(employee_id) REFERENCES employees (id)
)

;

CREATE TABLE activity_events (
	id INTEGER NOT NULL,
	ticket_id INTEGER NOT NULL,
	body VARCHAR NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(ticket_id) REFERENCES tickets (id)
)

;
CREATE INDEX ix_activity_events_ticket_id ON activity_events (ticket_id);

CREATE TABLE notes (
	id INTEGER NOT NULL,
	ticket_id INTEGER NOT NULL,
	employee_id INTEGER NOT NULL,
	body TEXT NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(ticket_id) REFERENCES tickets (id),
	FOREIGN KEY(employee_id) REFERENCES employees (id)
)

;

CREATE TABLE reminders (
	id INTEGER NOT NULL,
	ticket_id INTEGER NOT NULL,
	cycle INTEGER NOT NULL,
	kind VARCHAR NOT NULL,
	recipient VARCHAR NOT NULL,
	acknowledged BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (ticket_id, cycle, kind),
	FOREIGN KEY(ticket_id) REFERENCES tickets (id)
)

;
