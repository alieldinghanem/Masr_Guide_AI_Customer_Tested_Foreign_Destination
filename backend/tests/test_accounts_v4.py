import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from app.main import app
import app.accounts as ac


def test_account_isolation_and_trip_crud(tmp_path, monkeypatch):
    monkeypatch.setattr(ac, '_DB', tmp_path / 'test_users.sqlite3')
    with TestClient(app) as client:
        first = client.post('/api/auth/register', json={'email':'testone@example.com','password':'longpassword1234'})
        assert first.status_code == 201, first.text
        a = {'Authorization': 'Bearer ' + first.json()['token']}
        second = client.post('/api/auth/register', json={'email':'testtwo@example.com','password':'longpassword5678'})
        assert second.status_code == 201
        b = {'Authorization': 'Bearer ' + second.json()['token']}
        assert client.post('/api/auth/register', json={'email':'testone@example.com','password':'longpassword1234'}).status_code == 409
        assert client.post('/api/auth/login', json={'email':'testone@example.com','password':'incorrect12345'}).status_code == 401
        assert client.get('/api/my/trips').status_code == 401
        saved = client.post('/api/my/trips', json={'title':'My Egyptian tour','itinerary':{'days':[{'day':1,'city':'Cairo','stops':[]}] }}, headers=a)
        assert saved.status_code == 201, saved.text
        trip_id = saved.json()['id']
        assert len(client.get('/api/my/trips', headers=a).json()['trips']) == 1
        assert client.get('/api/my/trips', headers=b).json()['trips'] == []
        assert client.get('/api/my/trips/'+trip_id, headers=b).status_code == 404
        assert client.put('/api/my/trips/'+trip_id, headers=b, json={'title':'bad','itinerary':{'days':[]}}).status_code == 404
        assert client.delete('/api/my/trips/'+trip_id, headers=b).status_code == 404
        assert client.put('/api/my/trips/'+trip_id, headers=a, json={'title':'Updated title','itinerary':{'days':[]}}).status_code == 200
        assert client.get('/api/my/trips/'+trip_id, headers=a).json()['title'] == 'Updated title'
        assert client.post('/api/auth/logout', headers=a).status_code == 200
        assert client.get('/api/my/trips', headers=a).status_code == 401
        assert client.post('/api/auth/login', json={'email':'testone@example.com','password':'longpassword1234'}).status_code == 200


def test_partner_intake_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(ac, '_DB', tmp_path / 'users.sqlite3')
    monkeypatch.delenv('PARTNER_INQUIRIES_ENABLED', raising=False)
    with TestClient(app) as client:
        result = client.post('/api/partners/apply', json={'company':'A partner','email':'partner@example.com'})
        assert result.status_code == 503
