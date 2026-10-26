from datetime import timedelta
from sqlalchemy import select
from .db import Product, Employee, Customer, Conversation, Message, Ticket, Activity, Note, Setting, now

PRODUCTS = [
('Anillo Alba', 'anillo', 8900, 'plata', 'minimalista', 'Plata 925 pulida, perfil fino y cómodo para cada día.', True),
('Solitario Aurora', 'anillo', 69000, 'oro', 'clasico', 'Oro amarillo de 18 quilates con circonita central.', True),
('Alianza Horizonte', 'anillo', 42000, 'oro', 'minimalista', 'Banda de oro de 18 quilates, acabado satinado.', True),
('Anillo Bruma', 'anillo', 12500, 'plata', 'vintage', 'Plata 925 con relieve floral y acabado envejecido.', True),
('Anillo Latido', 'anillo', 19500, 'oro', 'romantico', 'Oro de 9 quilates con un pequeño corazón calado.', True),
('Anillo Órbita', 'anillo', 13500, 'titanio', 'moderno', 'Titanio ligero con una línea central cepillada.', True),
('Pendientes Rocío', 'pendientes', 6500, 'plata', 'minimalista', 'Pequeñas gotas de plata 925 con cierre de presión.', True),
('Aros Luz', 'pendientes', 18500, 'oro', 'minimalista', 'Aros de oro de 9 quilates de 12 mm.', True),
('Pendientes Nácar', 'pendientes', 11900, 'plata', 'clasico', 'Perlas cultivadas de agua dulce sobre plata 925.', True),
('Pendientes Celeste', 'pendientes', 24500, 'oro', 'romantico', 'Oro de 9 quilates con circonitas en forma de estrella.', True),
('Pendientes Art Déco', 'pendientes', 14500, 'plata', 'vintage', 'Diseño geométrico en plata con ónix sintético.', False),
('Collar Marea', 'collar', 9900, 'plata', 'minimalista', 'Cadena de plata 925 de 42 cm con pequeño disco.', True),
('Colgante Sol', 'collar', 27500, 'oro', 'moderno', 'Medallón solar de oro de 9 quilates con cadena de 45 cm.', True),
('Collar Lazo', 'collar', 15900, 'plata', 'romantico', 'Lazo de plata pulida con cadena ajustable.', True),
('Collar Herencia', 'collar', 56000, 'oro', 'vintage', 'Camafeo sintético en marco de oro de 18 quilates.', True),
('Collar Línea', 'collar', 5900, 'acero', 'moderno', 'Cadena de acero inoxidable con barra horizontal.', True),
('Pulsera Arena', 'pulsera', 7900, 'plata', 'minimalista', 'Cadena de eslabones finos en plata 925, 18 cm.', True),
('Pulsera Eslabón', 'pulsera', 35000, 'oro', 'clasico', 'Eslabones de oro de 9 quilates con cierre de mosquetón.', True),
('Pulsera Norte', 'pulsera', 4900, 'acero', 'moderno', 'Acero cepillado con cierre plegable, 20 cm.', True),
('Pulsera Jardín', 'pulsera', 12900, 'plata', 'romantico', 'Motivos florales de plata 925 con circonitas.', False),
('Reloj Tiempo', 'reloj', 18900, 'acero', 'clasico', 'Reloj de cuarzo ficticio de 38 mm, esfera marfil.', True),
('Reloj Eclipse', 'reloj', 29500, 'titanio', 'moderno', 'Reloj de cuarzo ficticio de 40 mm, esfera gris.', True),
('Reloj Memoria', 'reloj', 22900, 'acero', 'vintage', 'Reloj ficticio de 36 mm con correa de piel marrón.', True),
('Solitario Estrella', 'anillo', 125000, 'oro', 'romantico', 'Oro de 18 quilates con diamante de laboratorio de 0,30 ct.', True),
]


def seed(session):
    if session.get(Setting, 1):
        return
    session.add(Setting(id=1))
    for name, category, price, material, style, description, available in PRODUCTS:
        session.add(Product(name=name, category=category, price_cents=price, material=material, style=style, description=description, available=available))
    session.add_all([Employee(name='Lucía Martín', role='sales'), Employee(name='Diego Ruiz', role='workshop'), Employee(name='Elena Vega', role='owner')])
    session.flush()
    demos = [
        ('Clara Molina', 'Un anillo para un gran sí', 'Busco un anillo de compromiso en oro. Mi presupuesto es de 900 €.', 'high', 'Waiting for Staff', 1, 80, {'category':'anillo','material':'oro','budget':900}, [2,3]),
        ('Javier Soto', 'Seguimiento de reparación', '¿Podéis confirmar cómo va la reparación DEMO-1042?', 'standard', 'In Progress', 2, 42, {}, []),
        ('María Costa', 'Un regalo por menos de 150 €', 'Quiero un collar de plata minimalista, hasta 150 €.', 'standard', 'New', None, 18, {'category':'collar','material':'plata','budget':150,'style':'minimalista'}, [12]),
        ('Pablo Alonso', 'Alianzas para nuestra boda', 'Queremos ver alianzas de oro. Tenemos 1.200 € de presupuesto.', 'high', 'Waiting for Customer', 1, 120, {'category':'anillo','material':'oro','budget':1200}, [3]),
        ('Ana Beltrán', 'Consulta de garantía', '¿Qué garantía tiene mi reloj? Me gustaría hablar con una persona.', 'standard', 'Resolved', 2, 180, {}, []),
        ('Sofía Vidal', 'Pendientes para una celebración', 'Busco pendientes de oro, sencillos, hasta 250 €.', 'standard', 'Reopened', 1, 35, {'category':'pendientes','material':'oro','budget':250}, [8]),
    ]
    for name, subject, body, priority, status, employee, age, prefs, ids in demos:
        stamp = now() - timedelta(minutes=age)
        customer = Customer(name=name)
        session.add(customer); session.flush()
        conv = Conversation(customer_id=customer.id, preferences=prefs, human_takeover=status != 'New', created_at=stamp)
        session.add(conv); session.flush()
        session.add(Message(conversation_id=conv.id, role='customer', body=body, created_at=stamp))
        session.add(Message(conversation_id=conv.id, role='assistant', body='He compartido tu consulta con el equipo de la demo. Los datos y productos de este entorno son ficticios.', product_ids=ids, created_at=stamp + timedelta(seconds=1)))
        ticket = Ticket(conversation_id=conv.id, subject=subject, summary=body, priority=priority, status=status, employee_id=employee, created_at=stamp, updated_at=stamp, reminder_since=stamp)
        session.add(ticket); session.flush()
        session.add(Activity(ticket_id=ticket.id, body='Consulta de ejemplo creada', created_at=stamp))
        if status == 'Waiting for Customer':
            session.add(Message(conversation_id=conv.id, role='staff', body='En esta simulación podemos ayudarte a comparar estilos. ¿Preferís acabado pulido o satinado?', created_at=stamp + timedelta(minutes=5)))
        if status == 'In Progress':
            session.add(Note(ticket_id=ticket.id, employee_id=2, body='Ejemplo: consultar al taller. No hay conexión con reparaciones reales.'))
    session.commit()
