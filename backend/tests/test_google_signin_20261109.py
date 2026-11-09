"""Google Identity Services regression tests, no live Google credentials used."""
from fastapi.testclient import TestClient

from app.main import app
from app import accounts as ac


def test_google_signin_creates_session_and_reuses_google_subject(tmp_path, monkeypatch):
    monkeypatch.setattr(ac, '_DB', tmp_path / 'users.sqlite3')
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'example-client.apps.googleusercontent.com')
    monkeypatch.setattr(ac, '_verify_google_credential', lambda value: ('hello@gmail.com', 'google-sub-123'))
    with TestClient(app) as client:
        config = client.get('/api/auth/google/config')
        assert config.status_code == 200
        assert config.json()['client_id'] == 'example-client.apps.googleusercontent.com'
        created = client.post('/api/auth/google', json={'credential': 'x' * 100})
        assert created.status_code == 200, created.text
        token = created.json()['token']
        assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + token}).json()['user']['google_linked']
        assert created.json()['user']['email'] == 'hello@gmail.com'
        again = client.post('/api/auth/google', json={'credential': 'x' * 100})
        assert again.status_code == 200
        assert again.json()['user']['id'] == created.json()['user']['id']
        assert client.post('/api/auth/logout', headers={'Authorization': 'Bearer ' + token}).status_code == 200


def test_existing_password_account_must_explicitly_link_google(tmp_path, monkeypatch):
    monkeypatch.setattr(ac, '_DB', tmp_path / 'users.sqlite3')
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setattr(ac, '_verify_google_credential', lambda value: ('existing@gmail.com', 'google-sub-2'))
    with TestClient(app) as client:
        created = client.post('/api/auth/register', json={
            'email': 'existing@gmail.com', 'password': 'a-strong-password-123'})
        assert created.status_code == 201
        session = created.json()['token']
        # Verified Google email alone never silently claims a password account.
        rejected = client.post('/api/auth/google', json={'credential': 'x' * 100})
        assert rejected.status_code == 409
        auth = {'Authorization': 'Bearer ' + session}
        linked = client.post('/api/auth/google/link', json={'credential': 'x' * 100}, headers=auth)
        assert linked.status_code == 200, linked.text
        same = client.post('/api/auth/google', json={'credential': 'x' * 100})
        assert same.status_code == 200
        assert same.json()['user']['id'] == created.json()['user']['id']
        assert client.get('/api/auth/me', headers=auth).json()['user']['google_linked'] is True


def test_google_linking_rejects_wrong_email_and_unauthenticated_user(tmp_path, monkeypatch):
    monkeypatch.setattr(ac, '_DB', tmp_path / 'users.sqlite3')
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setattr(ac, '_verify_google_credential', lambda value: ('other@gmail.com', 'google-sub-3'))
    with TestClient(app) as client:
        account = client.post('/api/auth/register', json={
            'email': 'correct@gmail.com', 'password': 'a-strong-password-123'})
        assert account.status_code == 201
        assert client.post('/api/auth/google/link', json={'credential': 'x' * 100}).status_code == 401
        auth = {'Authorization': 'Bearer ' + account.json()['token']}
        assert client.post('/api/auth/google/link', json={'credential': 'x' * 100}, headers=auth).status_code == 409


def test_google_only_account_deletion_requires_linked_google_credential(tmp_path, monkeypatch):
    monkeypatch.setattr(ac, '_DB', tmp_path / 'users.sqlite3')
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setattr(ac, '_verify_google_credential', lambda value: ('new@gmail.com', 'google-sub-4'))
    with TestClient(app) as client:
        account = client.post('/api/auth/google', json={'credential': 'x' * 100})
        assert account.status_code == 200
        auth = {'Authorization': 'Bearer ' + account.json()['token']}
        request = {'confirmation': 'DELETE MY ACCOUNT'}
        assert client.request('DELETE', '/api/my/account', headers=auth, json=request).status_code == 403
        deleted = client.request('DELETE', '/api/my/account', headers=auth,
                                 json={**request, 'google_credential': 'x' * 100})
        assert deleted.status_code == 200, deleted.text
        assert client.get('/api/auth/me', headers=auth).status_code == 401


def test_new_google_signup_disabled_on_temporary_portfolio_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(ac, '_DB', tmp_path / 'users.sqlite3')
    monkeypatch.setenv('APP_ENV', 'portfolio')
    monkeypatch.delenv('MASR_DURABLE_STORAGE_CONFIRMED', raising=False)
    monkeypatch.setattr(ac, '_verify_google_credential', lambda value: ('new@gmail.com', 'google-sub-5'))
    with TestClient(app) as client:
        response = client.post('/api/auth/google', json={'credential': 'x' * 100})
        assert response.status_code == 503
        assert 'durable' in response.json()['detail'].lower()


def test_google_signin_is_unavailable_without_oauth_client_id(tmp_path, monkeypatch):
    monkeypatch.setattr(ac, '_DB', tmp_path / 'users.sqlite3')
    monkeypatch.delenv('GOOGLE_CLIENT_ID', raising=False)
    with TestClient(app) as client:
        response = client.post('/api/auth/google', json={'credential': 'x' * 100})
        assert response.status_code == 503
