"""Customer-derived regressions: colloquial allocation, card safety, French duration."""
import pytest


@pytest.fixture
def existing_trip(client):
    body = {'message': 'خططلي رحلة 12 يوم 4 أيام القاهرة و4 أيام الأقصر و4 أيام الغردقة',
            'language': 'Arabic'}
    result = client.post('/api/consult', json=body)
    assert result.status_code == 200
    state = result.json()['trip_state']
    assert state and state['days'] == 12
    return state


def allocations(state):
    return {p['cities'][0]: p['days'] for p in state['phases'] if len(p['cities']) == 1}


def test_colloquial_transfer_mutates_only_target_cities(client, existing_trip):
    response = client.post('/api/consult', json={
        'message': 'شيل يومين من الأقصر وحطهم في الغردقة',
        'language': 'Arabic', 'trip_state': existing_trip})
    assert response.status_code == 200
    body = response.json()
    assert body['mode'] == 'local-planner'
    assert body['trip_state']['days'] == 12
    assert allocations(body['trip_state']) == {'Cairo': 4, 'Luxor': 2, 'Hurghada': 6}


@pytest.mark.parametrize('message', ['شيل 9 أيام من الأقصر وحطهم في الغردقة',
                                      'شيل 4 أيام من الأقصر وحطهم في الغردقة'])
def test_invalid_transfer_preserves_trip(client, existing_trip, message):
    body = client.post('/api/consult', json={'message': message,
                     'language': 'Arabic', 'trip_state': existing_trip}).json()
    assert body['trip_state'] == existing_trip
    assert body['mode'] == 'needs-clarification'


@pytest.mark.parametrize('path', ['/api/chat', '/api/consult'])
def test_visa_payment_question_explains_no_checkout(client, path):
    body = client.post(path, json={'message': 'هل أقدر أدفع بالفيزا هنا؟',
                                  'language': 'Arabic'}).json()
    assert body['mode'] == 'local-assistant'
    assert 'لا يمكنني' in body['answer']
    assert 'بطاق' in body['answer']


@pytest.mark.parametrize('path', ['/api/chat', '/api/consult'])
def test_numeric_card_disclosure_not_echoed(client, path):
    number = '4111 1111 1111 1111'  # public, non-secret test-card pattern
    body = client.post(path, json={'message': 'ده رقم بطاقتي ' + number,
                                  'language': 'Arabic'}).json()
    assert body['mode'] == 'local-assistant'
    assert number not in body['answer']
    assert 'CVV' in body['answer']


def test_french_spelled_day_duration_works(client):
    response = client.post('/api/consult', json={
        'message': 'Je veux visiter l’Egypte pendant dix jours, Le Caire et Louxor',
        'language': 'French'})
    assert response.status_code == 200
    body = response.json()
    assert body['trip_state'] and body['trip_state']['days'] == 10
    assert {'Cairo', 'Luxor'}.issubset(
        {city for p in body['trip_state']['phases'] for city in p['cities']})


def test_entry_visa_not_treated_as_payment(client):
    body = client.post('/api/chat', json={'message': 'هل أحتاج فيزا دخول مصر؟',
                                          'language': 'Arabic'}).json()
    assert 'بطاقتك البنكية' not in body['answer']


def test_payment_history_redaction_helper():
    from app.conversation_router import redact_payment_data
    raw = 'Earlier card 4111 1111 1111 1111 and CVV: 123'
    clean = redact_payment_data(raw)
    assert '4111' not in clean and '123' not in clean
    assert 'redacted' in clean
    assert redact_payment_data('Visa entry requirements for Egypt') == 'Visa entry requirements for Egypt'


def test_gemini_provider_never_forwards_prior_card_number(monkeypatch):
    import json
    from types import SimpleNamespace
    from app import gemini_client
    monkeypatch.setenv('GEMINI_API_KEY', 'mock-only')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-2.5-flash')
    seen = []
    def fake_open(req, timeout):
        seen.append(json.loads(req.data.decode()))
        text = json.dumps({'candidates': [{'content': {'parts': [{'text': 'Safe advice'}]}}]})
        return type('Context', (), {
            '__enter__': lambda self: self, '__exit__': lambda *args: False,
            'read': lambda self, *args: text.encode()})()
    monkeypatch.setattr(gemini_client, 'urlopen', fake_open)
    history = [SimpleNamespace(role='user', content='My card number was 4111 1111 1111 1111'),
               SimpleNamespace(role='assistant', content='Do not share card data.')]
    assert gemini_client.generate('Where is Luxor?', 'Safe answers only', history=history) == 'Safe advice'
    assert '4111' not in json.dumps(seen)
    assert 'redacted' in json.dumps(seen)


def test_openai_provider_never_forwards_prior_card_number(monkeypatch):
    import sys
    import types
    from app import openai_client
    seen = []
    class FakeClient:
        def __init__(self, **kwargs): self.responses = self
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def create(self, **kwargs):
            seen.append(kwargs)
            return types.SimpleNamespace(status='completed', incomplete_details=None, output_text='No stored card data')
    monkeypatch.setenv('OPENAI_API_KEY', 'mock-only')
    monkeypatch.setitem(sys.modules, 'openai', types.SimpleNamespace(OpenAI=FakeClient))
    history = [types.SimpleNamespace(role='user', content='Card: 4111 1111 1111 1111')]
    assert openai_client.generate('Where is Luxor?', 'Use safe sources', history=history) == 'No stored card data'
    assert '4111' not in str(seen)
    assert seen[-1]['store'] is False


def test_account_persistence_rejects_unredacted_card_numbers():
    from fastapi import HTTPException
    from app.accounts import ConversationSave, _conversation_payload
    message = ConversationSave(title='Egypt travel chat', messages=[
        {'role': 'user', 'text': 'My card is 4111 1111 1111 1111'}])
    with pytest.raises(HTTPException) as exc:
        _conversation_payload(message)
    assert exc.value.status_code == 422
    assert '4111' not in str(exc.value.detail)


def test_account_persistence_allows_regular_travel_questions():
    from app.accounts import ConversationSave, _conversation_payload
    message = ConversationSave(title='Egypt travel chat', messages=[
        {'role': 'user', 'text': 'Is a visa required for Egypt in 2026?'}])
    raw, _, _ = _conversation_payload(message)
    assert 'visa required' in raw
