"""Exercise the real PostgreSQL path on CI's temporary database."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import accounts, security
from app.main import app


@pytest.mark.skipif(not os.getenv('MASR_TEST_POSTGRES_URL'), reason='PostgreSQL service not configured')
def test_traveler_account_and_reviews_survive_catalog_rebuild_and_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', None)
    monkeypatch.setenv('NEON_DATABASE_URL', os.environ['MASR_TEST_POSTGRES_URL'])
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'derived_catalog.sqlite3'))
    monkeypatch.setenv('APP_ENV', 'portfolio')
    monkeypatch.setenv('MASR_DURABLE_STORAGE_CONFIRMED', 'true')
    security._guard_hits.clear()
    email = f'postgres-qa-{uuid4().hex}@example.org'
    password = 'Postgres-Test-Password-2026!'
    with TestClient(app) as first:
        assert first.get('/api/ready').status_code == 200
        assert first.get('/api/health').json()['registration_enabled'] is True
        created = first.post('/api/auth/register', json={'email': email, 'password': password})
        assert created.status_code == 201, created.text
        headers = {'Authorization': f"Bearer {created.json()['token']}"}
        assert first.post('/api/my/favorites/karnak', headers=headers).status_code == 200
        assert first.post('/api/ratings/giza-pyramids', json={'rating': 5}, headers=headers).status_code == 200
        assert first.post('/api/ratings/giza-pyramids/comments',
                          json={'comment': 'A memorable visit.'}, headers=headers).status_code == 200

    with TestClient(app) as restarted:
        login = restarted.post('/api/auth/login', json={'email': email, 'password': password})
        assert login.status_code == 200, login.text
        headers = {'Authorization': f"Bearer {login.json()['token']}"}
        assert restarted.get('/api/my/favorites', headers=headers).json() == {'place_ids': ['karnak']}
        assert restarted.get('/api/ratings').json() == {
            'ratings': {'giza-pyramids': {'average': 5.0, 'count': 1}},
            'temporary_storage': False,
        }
        comments = restarted.get('/api/ratings/giza-pyramids/comments').json()
        assert comments['comments'][0]['comment'] == 'A memorable visit.'
        deleted = restarted.request('DELETE', '/api/my/account', headers=headers, json={
            'password': password, 'confirmation': 'DELETE MY ACCOUNT'})
        assert deleted.status_code == 200, deleted.text
        assert restarted.get('/api/ratings').json()['ratings'] == {}
