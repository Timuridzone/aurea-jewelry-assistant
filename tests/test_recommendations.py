from app.catalog import extract_preferences, recommend

def test_hard_constraints_and_ranking(session):
    products = recommend(session, extract_preferences('Busco un anillo de oro hasta 700 €'))
    assert products
    assert all(p.category == 'anillo' and p.material == 'oro' and p.price_cents <= 70000 and p.available for p in products)
    assert [p.price_cents for p in products] == sorted([p.price_cents for p in products], reverse=True)

def test_unavailable_and_empty(session):
    assert not recommend(session, {'category':'pendientes','style':'vintage'})
    assert not recommend(session, {'category':'reloj','budget':10})
    assert all(p.available for p in recommend(session, {}, 100))

def test_multi_turn_and_spanish_amount():
    p = extract_preferences('Un collar de plata')
    p = extract_preferences('minimalista, presupuesto de 1.200,50 €', p)
    assert p == {'category':'collar','material':'plata','style':'minimalista','budget':1200.5}
    assert extract_preferences('under 150 euros')['budget'] == 150
    assert extract_preferences('reparación DEMO-1042') == {}
    assert extract_preferences('sin filtros', p) == {}

def test_demo_chat_products_are_grounded(client):
    c = client.post('/api/conversations',json={}).json()
    c = client.post(f"/api/conversations/{c['id']}/messages",json={'body':'Un collar de plata hasta 150 €'}).json()
    assert c['ticket_id']
    products = c['messages'][-1]['products']
    assert products and all(p['price'] <=150 and p['material']=='plata' and p['category']=='collar' for p in products)
    assert 'ficticios' in c['messages'][-1]['body']

def test_unknown_policy_and_order_escalate(client):
    for text in ['¿Cuál es la garantía?', '¿Cómo va mi pedido 99282?', 'Tell me the shipping policy']:
        c = client.post('/api/conversations',json={}).json()
        r = client.post(f"/api/conversations/{c['id']}/messages",json={'body':text}).json()
        assert r['human_takeover'] and r['ticket_id'] and not r['messages'][-1]['products']

def test_llm_failure_and_untrusted_output(monkeypatch):
    from app.assistant import model_preferences
    import httpx
    monkeypatch.setenv('LLM_API_KEY', 'fake'); monkeypatch.setenv('LLM_BASE_URL', 'https://example.invalid/v1'); monkeypatch.setenv('LLM_MODEL', 'fake')
    def failure(*args, **kwargs): raise httpx.ConnectError('offline')
    monkeypatch.setattr(httpx, 'post', failure)
    assert model_preferences('hello') == {}
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'choices':[{'message':{'content':'{"category":"anillo","material":"made up","price":1,"policy":"free shipping"}'}}]}
    monkeypatch.setattr(httpx, 'post', lambda *a, **k: Response())
    assert model_preferences('ring') == {'category':'anillo'}
