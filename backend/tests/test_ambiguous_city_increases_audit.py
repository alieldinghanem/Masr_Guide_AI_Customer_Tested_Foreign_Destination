"""Regression for ambiguous city/day additions discovered in Oct 31 2026 user QA."""
from fastapi.testclient import TestClient
from app.main import app


def _ask(client, message, state=None):
    req = {'message': message}
    if state is not None:
        req['trip_state'] = state
    resp = client.post('/api/consult', json=req)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_arabic_ambiguous_increase_preserves_allocation():
    with TestClient(app, client=('192.0.2.73', 63000)) as client:
        prior = _ask(client, 'Plan 15 days: 10 days in Cairo and 5 days in Sharm El Sheikh')
        original = prior['trip_state']
        assert [p['days'] for p in original['phases']] == [10, 5]
        response = _ask(client, 'خلينا نزود 3 أيام في القاهرة', original)
        assert response['mode'] == 'needs-clarification'
        assert response['trip_state'] == original
        assert response['itinerary'] is None
        assert 'لم أغيّر' in response['answer']


def test_english_ambiguous_increase_preserves_allocation():
    with TestClient(app, client=('192.0.2.73', 63000)) as client:
        prior = _ask(client, 'Plan 15 days: 10 days in Cairo and 5 days in Sharm El Sheikh')
        original = prior['trip_state']
        response = _ask(client, 'Add 3 days in Cairo', original)
        assert response['mode'] == 'needs-clarification'
        assert response['trip_state'] == original
        assert response['itinerary'] is None
        assert 'unchanged' in response['answer']


def test_explicit_city_transfer_still_works():
    with TestClient(app, client=('192.0.2.73', 63000)) as client:
        prior = _ask(client, 'Plan 15 days: 10 days in Cairo and 5 days in Sharm El Sheikh')
        original = prior['trip_state']
        response = _ask(client, 'Move 3 days from Cairo to Sharm El Sheikh', original)
        assert [p['days'] for p in response['trip_state']['phases']] == [7, 8]
        assert len(response['itinerary']['days']) == 15


def test_arabic_without_preposition_still_safe():
    with TestClient(app, client=('192.0.2.73', 63000)) as client:
        prior = _ask(client, 'Plan 15 days: 10 days in Cairo and 5 days in Sharm El Sheikh')
        original = prior['trip_state']
        response = _ask(client, 'زود 3 أيام القاهرة', original)
        assert response['mode'] == 'needs-clarification'
        assert response['trip_state'] == original
        assert response['itinerary'] is None


def test_english_increase_city_by_amount_safe():
    with TestClient(app, client=('192.0.2.73', 63000)) as client:
        prior = _ask(client, 'Plan 15 days: 10 days in Cairo and 5 days in Sharm El Sheikh')
        original = prior['trip_state']
        response = _ask(client, 'Increase Cairo by 3 days', original)
        assert response['mode'] == 'needs-clarification'
        assert response['trip_state'] == original
        assert response['itinerary'] is None


def test_arabic_explicit_transfer_still_works():
    with TestClient(app, client=('192.0.2.73', 63000)) as client:
        prior = _ask(client, 'Plan 15 days: 10 days in Cairo and 5 days in Sharm El Sheikh')
        original = prior['trip_state']
        response = _ask(client, 'انقل ٣ أيام من القاهرة لشرم الشيخ', original)
        assert [p['days'] for p in response['trip_state']['phases']] == [7, 8]
        assert len(response['itinerary']['days']) == 15
