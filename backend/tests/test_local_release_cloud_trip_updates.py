"""Traveler acceptance: revise one cloud trip, not silently create a duplicate.

All provider calls are disabled; this exercises the deterministic AI/planner route,
HTTP authorization, persistence and optimistic concurrency together.
"""

from fastapi.testclient import TestClient
from app import accounts, security
from app.main import app, _chat_calls


def test_multi_city_revision_updates_the_selected_persisted_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'travelers.sqlite3')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'places.sqlite3'))
    monkeypatch.setenv('GEMINI_API_KEY', '')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setenv('CHAT_RATE_LIMIT_PER_MINUTE', '999')
    security._guard_hits.clear()
    _chat_calls.clear()
    with TestClient(app) as client:
        a = client.post('/api/auth/register', json={
            'email': 'release-owner@example.org', 'password': 'Change-Me-Release-2026!'
        })
        b = client.post('/api/auth/register', json={
            'email': 'release-other@example.org', 'password': 'Change-Me-Release-2026!'
        })
        assert a.status_code == b.status_code == 201
        own = {'Authorization': 'Bearer ' + a.json()['token']}
        other = {'Authorization': 'Bearer ' + b.json()['token']}
        original = client.post('/api/consult', json={
            'message': 'Plan 20 days in Egypt, 13 days Cairo and 7 days Hurghada'
        })
        assert original.status_code == 200, original.text
        first = original.json()
        assert len(first['itinerary']['days']) == 20
        assert [day['city'] for day in first['itinerary']['days']] == ['Cairo'] * 13 + ['Hurghada'] * 7
        saved = client.post('/api/my/trips', headers=own, json={
            'title': 'Our 20-day Egypt trip', 'itinerary': first['itinerary']
        })
        assert saved.status_code == 201, saved.text
        uid = saved.json()['id']
        version = client.get(f'/api/my/trips/{uid}', headers=own).json()['updated_at']
        second = client.post('/api/consult', json={
            'message': 'Replace Hurghada with Sharm El Sheikh',
            'trip_state': first['trip_state'],
        })
        assert second.status_code == 200, second.text
        revised = second.json()['itinerary']
        assert [day['city'] for day in revised['days']] == ['Cairo'] * 13 + ['Sharm El Sheikh'] * 7
        assert client.put(f'/api/my/trips/{uid}', headers={**own, 'If-Match': version}, json={
            'title': 'Our 20-day Egypt trip', 'itinerary': revised
        }).status_code == 200
        result = client.get(f'/api/my/trips/{uid}', headers=own)
        assert result.status_code == 200
        assert [day['city'] for day in result.json()['itinerary']['days']] == ['Cairo'] * 13 + ['Sharm El Sheikh'] * 7
        assert len(client.get('/api/my/trips', headers=own).json()['trips']) == 1
        assert client.get('/api/my/trips', headers=other).json()['trips'] == []
        assert client.get(f'/api/my/trips/{uid}', headers=other).status_code == 404
        assert client.put(f'/api/my/trips/{uid}', headers={**own, 'If-Match': version}, json={
            'title': 'Stale edit', 'itinerary': first['itinerary']
        }).status_code == 409
        assert 'Sharm El Sheikh' in str(client.get(f'/api/my/trips/{uid}', headers=own).json()['itinerary'])
    security._guard_hits.clear()
    _chat_calls.clear()
