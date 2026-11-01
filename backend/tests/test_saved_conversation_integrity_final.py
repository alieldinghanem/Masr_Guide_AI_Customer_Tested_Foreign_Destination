"""Regression tests: saved chat content must never crash travel UI on restoration."""
import pytest
from app import accounts, security


@pytest.fixture(autouse=True)
def isolated_account_db(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'isolated-saved-chat.sqlite3')
    security._guard_hits.clear()
    accounts.setup()
    yield
    security._guard_hits.clear()


def auth(client):
    r = client.post('/api/auth/register', json={
        'email': 'chat-integrity@example.org', 'password': 'very-long-safe-test-password-2026'})
    assert r.status_code == 201, r.text
    return {'Authorization': 'Bearer ' + r.json()['token']}


def test_chat_saves_normal_curated_itinerary(client):
    headers = auth(client)
    plan = client.post('/api/plan', json={'cities':['Cairo'], 'days': 2}).json()
    body = {'title':'Curated Cairo trip', 'messages':[{'role':'user','text':'Plan Cairo'}],
            'itinerary': plan}
    response = client.post('/api/my/conversations', json=body, headers=headers)
    assert response.status_code == 201, response.text
    loaded = client.get('/api/my/conversations/'+response.json()['id'], headers=headers)
    assert loaded.json()['itinerary']['days'][0]['city'] == 'Cairo'


@pytest.mark.parametrize('value', [
    {}, {'days':'malformed'}, {'days':[None]},
    {'days':[{'day':1,'city':'Cairo','stops':[{}]}]},
    {'days':[{'day':1,'city':'Cairo','stops':[{'place': {'name':'Missing ID'}}]}]},
    {'days':[{'day':1,'city':'Cairo','stops':[], 'travel':'bad'}]},
    {'days':[{'day':1,'city':'Cairo','stops':[], 'activity_ideas':'not a list'}]},
])
def test_cannot_persist_malformed_chat_itinerary(client, value):
    headers = auth(client)
    response = client.post('/api/my/conversations', json={
        'title':'Imported session', 'messages':[{'role':'user','text':'Hello'}], 'itinerary': value
    }, headers=headers)
    assert response.status_code == 422, response.text
    assert client.get('/api/my/conversations', headers=headers).json()['conversations'] == []


def test_rejects_invalid_chat_update_without_overwriting_existing_content(client):
    headers = auth(client)
    initial = {'title':'Safe chat','messages':[{'role':'user','text':'Welcome'}]}
    created = client.post('/api/my/conversations', json=initial, headers=headers)
    assert created.status_code == 201
    uri = '/api/my/conversations/'+created.json()['id']
    updated = client.put(uri, json={**initial, 'itinerary':{'days':[{'day':1, 'city':'Luxor',
        'stops':[{'place': {'name':'No ID'}}]}]}}, headers=headers)
    assert updated.status_code == 422
    saved = client.get(uri, headers=headers).json()
    assert saved['itinerary'] is None
    assert saved['messages'][0]['text'] == 'Welcome'

@pytest.mark.parametrize('message,coast', [
    ('رحلة 20 يوم، 13 يوم في القاهرة و7 أيام للغردقة', 'Hurghada'),
    ('رحلة ٢٠ يوم، ١٣ يوم في القاهرة و٧ أيام لشرم الشيخ', 'Sharm El Sheikh'),
    ('Plan 20 days: 13 days in Cairo and 7 days in Hurghada', 'Hurghada'),
])
def test_explicit_coastal_city_without_word_beach_preserves_allocation(client, message, coast):
    response = client.post('/api/consult',json={'message':message})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get('itinerary') is not None, payload['answer']
    state = payload['trip_state']
    assert state['days'] == 20
    assert [p['days'] for p in state['phases']] == [13,7]
    assert state['phases'][0]['cities'] == ['Cairo']
    assert state['phases'][1]['cities'] == [coast]
    assert len(payload['itinerary']['days']) == 20
    assert payload['itinerary']['days'][-1]['city'] == coast


def test_high_cardinality_rate_limiter_fails_closed_instead_of_growing_unbounded(monkeypatch):
    from collections import deque
    from time import monotonic
    from app import main
    from fastapi import HTTPException
    now = monotonic()
    main._chat_calls.clear()
    for n in range(4096):
        main._chat_calls[f'peer-{n}'] = deque([now])
    with pytest.raises(HTTPException) as exc:
        main.check_chat_limit('new-peer')
    assert exc.value.status_code == 429
    assert len(main._chat_calls) == 4096
    main._chat_calls.clear()


def test_rejects_itinerary_that_silently_changes_explicit_destination_allocation(client):
    """A correctly shaped 20-day document is still invalid when 13/7 becomes 14/6."""
    headers = auth(client)
    reply = client.post('/api/consult', json={
        'message': 'Plan 20 days: 13 days in Cairo and 7 days in Hurghada'
    })
    assert reply.status_code == 200, reply.text
    state, plan = reply.json()['trip_state'], reply.json()['itinerary']
    assert [p['days'] for p in state['phases']] == [13, 7]
    assert plan['days'][13]['city'] == 'Hurghada'
    plan['days'][13]['city'] = 'Cairo'  # schema remains valid, allocation is now wrong
    result = client.post('/api/my/conversations', headers=headers, json={
        'title': 'Misallocated journey', 'messages': [{'role': 'user', 'text': 'Plan my trip'}],
        'trip_state': state, 'itinerary': plan,
    })
    assert result.status_code == 422, result.text
    assert client.get('/api/my/conversations', headers=headers).json()['conversations'] == []


def test_rejects_saved_conversation_with_malformed_trip_state(client):
    headers = auth(client)
    result = client.post('/api/my/conversations', headers=headers, json={
        'title': 'Broken trip state', 'messages': [{'role': 'user', 'text': 'Plan my trip'}],
        'trip_state': {'days': 20, 'phases': [{'days': 19, 'cities': ['Cairo'], 'kind': 'history'}]},
    })
    assert result.status_code == 422, result.text


def test_rejects_malformed_travel_fields_in_saved_plan(client):
    headers = auth(client)
    result = client.post('/api/my/conversations', headers=headers, json={
        'title': 'Broken transfer', 'messages': [{'role': 'user', 'text': 'Plan my trip'}],
        'itinerary': {'days': [{'day': 1, 'city': 'Cairo', 'stops': [],
                                'travel': {'minutes': 'one hour', 'from_city': 'Giza'}}]},
    })
    assert result.status_code == 422, result.text


def test_real_stateful_replacement_persists_without_changing_day_allocation(client, monkeypatch):
    """HTTP integration: initial plan -> authorized edit -> cloud save -> reload."""
    headers = auth(client)
    original = client.post('/api/consult', json={
        'message': 'Plan 20 days: 13 days in Cairo and 7 days in Hurghada',
    })
    assert original.status_code == 200, original.text
    before = original.json()
    assert [p['days'] for p in before['trip_state']['phases']] == [13, 7]
    created = client.post('/api/my/conversations', headers=headers, json={
        'title': 'My Egypt journey', 'messages': [{'role': 'user', 'text': 'Plan twenty days'}],
        'trip_state': before['trip_state'], 'itinerary': before['itinerary'],
    })
    assert created.status_code == 201, created.text
    uri = '/api/my/conversations/' + created.json()['id']
    previous = client.get(uri, headers=headers).json()
    assert previous['itinerary']['days'][13]['city'] == 'Hurghada'

    edited = client.post('/api/consult', json={
        'message': 'Replace Hurghada with Sharm El Sheikh',
        'trip_state': before['trip_state'],
    })
    assert edited.status_code == 200, edited.text
    after = edited.json()
    assert after['trip_state']['days'] == 20
    assert [p['days'] for p in after['trip_state']['phases']] == [13, 7]
    assert [day['city'] for day in after['itinerary']['days']] == ['Cairo'] * 13 + ['Sharm El Sheikh'] * 7

    body = {'title': 'Updated journey',
            'messages': [{'role': 'user', 'text': 'Replace Hurghada with Sharm El Sheikh'}],
            'trip_state': after['trip_state'], 'itinerary': after['itinerary']}
    saved = client.put(uri, headers={**headers, 'If-Match': previous['updated_at']}, json=body)
    assert saved.status_code == 200, saved.text
    restored = client.get(uri, headers=headers).json()
    assert restored['itinerary']['days'][13]['city'] == 'Sharm El Sheikh'
    assert restored['trip_state']['phases'][1]['cities'] == ['Sharm El Sheikh']
    assert restored['itinerary']['days'][0]['city'] == 'Cairo'
    stale = client.put(uri, headers={**headers, 'If-Match': previous['updated_at']}, json=body)
    assert stale.status_code == 409, stale.text
