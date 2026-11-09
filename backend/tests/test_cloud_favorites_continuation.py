"""Continuation regression: cloud favorites are account-scoped and resilient."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import accounts, security


@pytest.fixture(autouse=True)
def isolated_rate_counters():
    # Avoid making unrelated auth tests fail through shared in-memory test peer quotas.
    security._guard_hits.clear()
    yield
    security._guard_hits.clear()


def test_favorite_auth_isolation_idempotence_and_erasure(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'favorites.sqlite3')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'catalog.sqlite3'))
    with TestClient(app) as client:
        register = lambda email: client.post('/api/auth/register', json={
            'email': email, 'password': 'Correct-Password-2026!'
        })
        one, two = register('fav-first@example.org'), register('fav-second@example.org')
        assert one.status_code == two.status_code == 201
        a = {'Authorization': 'Bearer ' + one.json()['token']}
        b = {'Authorization': 'Bearer ' + two.json()['token']}
        assert client.get('/api/my/favorites').status_code == 401
        assert client.post('/api/my/favorites/karnak').status_code == 401
        assert client.delete('/api/my/favorites/karnak').status_code == 401
        assert client.get('/api/my/favorites', headers=a).json() == {'place_ids': []}
        assert client.post('/api/my/favorites/karnak', headers=a).status_code == 200
        assert client.post('/api/my/favorites/karnak', headers=a).status_code == 200
        assert client.get('/api/my/favorites', headers=a).json() == {'place_ids': ['karnak']}
        assert client.get('/api/my/favorites', headers=b).json() == {'place_ids': []}
        assert client.post('/api/my/favorites/not-in-catalog', headers=a).status_code == 404
        assert client.post('/api/my/favorites/not!valid', headers=a).status_code == 422
        assert client.get('/api/my/favorites', headers=a).json() == {'place_ids': ['karnak']}
        assert client.delete('/api/my/favorites/karnak', headers=b).status_code == 200
        assert client.get('/api/my/favorites', headers=a).json() == {'place_ids': ['karnak']}
        assert client.delete('/api/my/favorites/karnak', headers=a).status_code == 200
        assert client.delete('/api/my/favorites/karnak', headers=a).status_code == 200
        assert client.get('/api/my/favorites', headers=a).json() == {'place_ids': []}
        assert client.post('/api/my/favorites/karnak', headers=a).status_code == 200
        deleted = client.request('DELETE', '/api/my/account', headers=a, json={
            'password': 'Correct-Password-2026!', 'confirmation': 'DELETE MY ACCOUNT'
        })
        assert deleted.status_code == 200, deleted.text
        assert client.get('/api/my/favorites', headers=a).status_code == 401
        assert client.get('/api/my/favorites', headers=b).json() == {'place_ids': []}
        with accounts._open() as conn:
            assert conn.execute('SELECT COUNT(*) FROM account_favorites').fetchone()[0] == 0


def test_favorites_limit_is_enforced_before_write(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'favorites2.sqlite3')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'catalog2.sqlite3'))
    with TestClient(app) as client:
        r = client.post('/api/auth/register', json={
            'email': 'fav-limit@example.org', 'password': 'Correct-Password-2026!'
        })
        assert r.status_code == 201
        token = {'Authorization': 'Bearer ' + r.json()['token']}
        uid = r.json()['user']['id']
        with accounts._open() as conn:
            conn.executemany('INSERT INTO account_favorites VALUES (?,?,?)', [
                (uid, f'seed-{i}', accounts._now().isoformat()) for i in range(500)
            ])
        assert client.post('/api/my/favorites/karnak', headers=token).status_code == 422
        assert len(client.get('/api/my/favorites', headers=token).json()['place_ids']) == 500
        assert client.delete('/api/my/favorites/seed-0', headers=token).status_code == 200
        assert client.post('/api/my/favorites/karnak', headers=token).status_code == 200
        assert len(client.get('/api/my/favorites', headers=token).json()['place_ids']) == 500


def test_private_data_export_excludes_tokens_and_other_accounts(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'account-export.sqlite3')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'tourism-export.sqlite3'))
    with TestClient(app) as client:
        first = client.post('/api/auth/register', json={
            'email': 'private-export@example.org', 'password': 'Correct-Password-2026!'
        }).json()
        second = client.post('/api/auth/register', json={
            'email': 'other-export@example.org', 'password': 'Correct-Password-2026!'
        }).json()
        a = {'Authorization': 'Bearer ' + first['token']}
        b = {'Authorization': 'Bearer ' + second['token']}
        assert client.post('/api/my/favorites/karnak', headers=a).status_code == 200
        assert client.post('/api/my/trips', headers=a,
                           json={'title': 'My sample', 'itinerary': {'days': [
                               {'day': 1, 'city': 'Luxor', 'stops': []}]}}).status_code == 201
        assert client.get('/api/my/export').status_code == 401
        result = client.get('/api/my/export', headers=a)
        assert result.status_code == 200
        assert result.headers['cache-control'] == 'no-store'
        content = result.json()
        assert content['profile']['email'] == 'private-export@example.org'
        assert len(content['trips']) == 1
        assert [f['place_id'] for f in content['favorites']] == ['karnak']
        assert content['conversations'] == []
        body = result.text
        assert first['token'] not in body
        assert second['token'] not in body
        assert 'password_hash' not in body
        assert 'salt' not in body
        assert 'other-export@example.org' not in body
        second_export = client.get('/api/my/export', headers=b).json()
        assert second_export['trips'] == [] and second_export['favorites'] == []


def test_public_portfolio_preview_disables_ephemeral_registration(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'preview-accounts.sqlite3')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'preview-places.sqlite3'))
    monkeypatch.setenv('APP_ENV', 'portfolio')
    monkeypatch.delenv('MASR_DURABLE_STORAGE_CONFIRMED', raising=False)
    with TestClient(app) as client:
        assert client.get('/api/health').json()['registration_enabled'] is False
        result = client.post('/api/auth/register', json={
            'email': 'new-preview@example.org', 'password': 'Correct-Password-2026!'
        })
        assert result.status_code == 503
        with accounts._open() as db:
            assert db.execute('SELECT COUNT(*) FROM account_users').fetchone()[0] == 0
    monkeypatch.setenv('MASR_DURABLE_STORAGE_CONFIRMED', 'true')
    with TestClient(app) as client:
        assert client.get('/api/health').json()['registration_enabled'] is True
        assert client.post('/api/auth/register', json={
            'email': 'new-preview@example.org', 'password': 'Correct-Password-2026!'
        }).status_code == 201


def test_render_disables_registration_without_confirmed_durable_storage(monkeypatch):
    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.setenv('RENDER', 'true')
    monkeypatch.delenv('MASR_DURABLE_STORAGE_CONFIRMED', raising=False)
    assert accounts.registration_enabled() is False
    monkeypatch.setenv('MASR_DURABLE_STORAGE_CONFIRMED', 'true')
    assert accounts.registration_enabled() is True
