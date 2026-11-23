import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from google.auth import crypt, jwt
from google.auth.exceptions import TransportError

from app import accounts, account_recovery, google_auth, security
from app.main import app

CLIENT = 'unit-client.apps.googleusercontent.com'
PASSWORD = 'Existing-account-password-2026!'


@pytest.fixture(scope='module')
def signing_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Isolated test signing key')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=1)).sign(key, hashes.SHA256()))
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    return crypt.RSASigner.from_string(private, key_id='unit-key'), cert.public_bytes(serialization.Encoding.PEM).decode()


@pytest.fixture
def google(tmp_path, monkeypatch, signing_key):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'accounts.sqlite3')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'catalog.sqlite3'))
    monkeypatch.setenv('APP_ENV', 'local')
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    monkeypatch.setenv('GOOGLE_CLIENT_ID', CLIENT)
    monkeypatch.setenv('AUTH_GOOGLE_RATE_PER_MINUTE', '1000')
    monkeypatch.delenv('NEON_DATABASE_URL', raising=False)
    monkeypatch.delenv('RENDER', raising=False)
    security._guard_hits.clear()
    signer, cert = signing_key

    def request(url, method='GET', timeout=None, **_kwargs):
        assert url == 'https://www.googleapis.com/oauth2/v1/certs'
        assert timeout == 8
        return type('Certificates', (), {'status': 200, 'data': json.dumps({'unit-key': cert}).encode()})()

    monkeypatch.setattr(google_auth, 'GoogleRequest', lambda: request)

    def token(challenge_nonce, **changes):
        now = int(time.time())
        claims = {'iss': 'https://accounts.google.com', 'aud': CLIENT, 'sub': 'google-unit-subject',
                  'email': 'traveler@gmail.com', 'email_verified': True, 'nonce': challenge_nonce,
                  'iat': now - 1, 'exp': now + 300, **changes}
        return jwt.encode(signer, claims).decode()

    with TestClient(app, base_url='https://travel.example.org') as client:
        yield client, token


def credentials(client, token, purpose='login', headers=None, **changes):
    result = client.post('/api/auth/google/challenge', json={'purpose': purpose}, headers=headers)
    assert result.status_code == 200, result.text
    nonce = result.json()['nonce']
    return {'credential': token(nonce, **changes), 'nonce': nonce}


def test_registration_confirms_password_without_breaking_legacy_clients(google):
    client, _ = google
    body = {'email': 'legacy@example.org', 'password': PASSWORD}
    assert client.post('/api/auth/register', json={**body, 'password_confirmation': PASSWORD + 'different'}).status_code == 422
    assert client.post('/api/auth/register', json=body).status_code == 201
    assert client.post('/api/auth/register', json={**body, 'email': 'confirmed@example.org', 'password_confirmation': PASSWORD}).status_code == 201


def test_real_signature_creates_google_account_and_rejects_nonce_replay(google):
    client, token = google
    body = credentials(client, token)
    response = client.post('/api/auth/google', json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['auth_methods'] == {'password': False, 'google': True}
    headers = {'Authorization': 'Bearer ' + data['token']}
    assert client.get('/api/auth/me', headers=headers).json()['user']['id'] == data['user']['id']
    assert client.get('/api/auth/email-status', headers=headers).json()['verified']
    assert client.post('/api/auth/google', json=body).status_code == 400
    assert client.get('/api/auth/google/config').headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('changes', [
    {'aud': 'attacker.apps.googleusercontent.com'}, {'iss': 'https://attacker.example'},
    {'exp': 1}, {'iat': 9999999999}, {'sub': ''}, {'nonce': 'wrong-nonce'},
    {'email_verified': False}, {'email_verified': 'true'}, {'email': ''},
])
def test_rejects_wrong_claims_even_with_a_valid_test_signature(google, changes):
    client, token = google
    body = credentials(client, token, **changes)
    assert client.post('/api/auth/google', json=body).status_code in (401, 422)
    with accounts._open() as db:
        assert db.execute('SELECT COUNT(*) FROM account_users').fetchone()[0] == 0


def test_signature_tampering_cannot_create_a_session(google):
    client, token = google
    body = credentials(client, token)
    parts = body['credential'].split('.')
    parts[2] = ('A' if parts[2][0] != 'A' else 'B') + parts[2][1:]
    body['credential'] = '.'.join(parts)
    assert client.post('/api/auth/google', json=body).status_code == 401


def test_challenge_is_bound_to_browser_and_expires(google):
    client, token = google
    body = credentials(client, token)
    with TestClient(app, base_url='https://travel.example.org') as other:
        credentials(other, token)
        assert other.post('/api/auth/google', json=body).status_code == 400
    with accounts._open() as db:
        db.execute('UPDATE account_google_challenges SET expires_at=?', ((accounts._now() - timedelta(seconds=1)).isoformat(),))
    assert client.post('/api/auth/google', json=body).status_code == 400


def test_public_challenge_cookie_is_secure_http_only_and_same_site(google):
    with TestClient(app, base_url='https://travel.example.org') as public:
        response = public.post('/api/auth/google/challenge', json={})
        cookie = response.headers['set-cookie']
        assert cookie.startswith('__Host-masr-google-browser=')
        assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Path=/' in cookie
        assert 'Domain=' not in cookie


def test_existing_email_is_never_auto_linked_and_saved_trips_survive(google):
    client, token = google
    original = client.post('/api/auth/register', json={'email': 'traveler@gmail.com', 'password': PASSWORD}).json()
    headers = {'Authorization': 'Bearer ' + original['token']}
    trip = client.post('/api/my/trips', headers=headers, json={'title': 'Existing trip', 'itinerary': {'days': []}}).json()
    body = credentials(client, token)
    assert client.post('/api/auth/google', json=body).status_code == 428
    assert client.post('/api/auth/google', json={**body, 'existing_password': 'Wrong-password-2026!'}).status_code == 403
    linked = client.post('/api/auth/google', json={**body, 'existing_password': PASSWORD})
    assert linked.status_code == 200
    assert linked.json()['user']['id'] == original['user']['id']
    assert linked.json()['auth_methods'] == {'password': True, 'google': True}
    google_headers = {'Authorization': 'Bearer ' + linked.json()['token']}
    assert client.get('/api/my/trips/' + trip['id'], headers=google_headers).status_code == 200
    assert client.post('/api/auth/login', json={'email': 'traveler@gmail.com', 'password': PASSWORD}).status_code == 200


def test_bound_subject_is_stable_when_email_changes_and_other_subject_cannot_claim_it(google):
    client, token = google
    first = client.post('/api/auth/google', json=credentials(client, token)).json()
    again = client.post('/api/auth/google', json=credentials(client, token, email='new-email@gmail.com')).json()
    assert again['user']['id'] == first['user']['id']
    assert again['user']['email'] == first['user']['email']  # no automatic email migration
    other = credentials(client, token, sub='another-google-subject')
    assert client.post('/api/auth/google', json=other).status_code == 409


def test_non_authoritative_external_email_requires_local_account_proof(google):
    client, token = google
    body = credentials(client, token, email='traveler@example.org')
    assert client.post('/api/auth/google', json=body).status_code == 422
    client.post('/api/auth/register', json={'email': 'traveler@example.org', 'password': PASSWORD})
    linked = client.post('/api/auth/google', json={**body, 'existing_password': PASSWORD})
    assert linked.status_code == 200
    assert not client.get('/api/auth/email-status', headers={'Authorization': 'Bearer ' + linked.json()['token']}).json()['verified']


def test_verified_workspace_can_register_and_existing_google_login_survives_registration_pause(google, monkeypatch):
    client, token = google
    body = credentials(client, token, email='traveler@company.example', hd='company.example')
    assert client.post('/api/auth/google', json=body).status_code == 200
    monkeypatch.setenv('APP_ENV', 'portfolio'); monkeypatch.delenv('MASR_DURABLE_STORAGE_CONFIRMED', raising=False)
    assert client.post('/api/auth/google', json=credentials(client, token, email='traveler@company.example')).status_code == 200
    assert client.post('/api/auth/google', json=credentials(client, token, sub='new-user-subject', email='new-user@gmail.com')).status_code == 503


def test_google_only_accounts_do_not_gain_password_login_or_email_reset(google, monkeypatch):
    client, token = google
    created = client.post('/api/auth/google', json=credentials(client, token)).json()
    with accounts._open() as db:
        salt = 'a' * 32
        db.execute('UPDATE account_users SET password_hash=?,salt=? WHERE id=?', (accounts._hash_password(PASSWORD, salt), salt, created['user']['id']))
    assert client.post('/api/auth/login', json={'email': 'traveler@gmail.com', 'password': PASSWORD}).status_code == 401
    sent = []
    monkeypatch.setattr(account_recovery, 'mail_ready', lambda: True)
    monkeypatch.setattr(account_recovery, '_send_link', lambda *args: sent.append(args))
    assert client.post('/api/auth/password-reset/request', json={'email': 'traveler@gmail.com'}).status_code == 202
    assert sent == []


def test_google_deletion_requires_fresh_bound_identity_and_explicit_confirmation(google):
    client, token = google
    created = client.post('/api/auth/google', json=credentials(client, token)).json()
    headers = {'Authorization': 'Bearer ' + created['token']}
    login_challenge = credentials(client, token)
    assert client.post('/api/auth/google/reauth-delete', headers=headers, json=login_challenge).status_code == 400
    delete_challenge = credentials(client, token, purpose='delete', headers=headers)
    proof = client.post('/api/auth/google/reauth-delete', headers=headers, json=delete_challenge)
    assert proof.status_code == 200
    body = {'google_proof': proof.json()['google_proof'], 'confirmation': 'DELETE MY ACCOUNT'}
    assert client.request('DELETE', '/api/my/account', headers=headers, json={**body, 'confirmation': 'no'}).status_code == 422
    assert client.request('DELETE', '/api/my/account', headers=headers, json=body).status_code == 200
    assert client.get('/api/auth/me', headers=headers).status_code == 401
    with accounts._open() as db:
        assert db.execute('SELECT COUNT(*) FROM account_google_identities').fetchone()[0] == 0


def test_wrong_google_identity_cannot_approve_deletion(google):
    client, token = google
    created = client.post('/api/auth/google', json=credentials(client, token)).json()
    headers = {'Authorization': 'Bearer ' + created['token']}
    body = credentials(client, token, purpose='delete', headers=headers, sub='different-subject')
    assert client.post('/api/auth/google/reauth-delete', headers=headers, json=body).status_code == 403


def test_config_disabled_provider_failure_and_rate_limits_are_honest(google, monkeypatch):
    client, token = google
    body = credentials(client, token)
    def unavailable(*_args, **_kwargs):
        raise TransportError('private transport details')
    monkeypatch.setattr(google_auth.id_token, 'verify_oauth2_token', unavailable)
    result = client.post('/api/auth/google', json=body)
    assert result.status_code == 503 and 'private transport' not in result.text
    monkeypatch.delenv('GOOGLE_CLIENT_ID')
    assert client.get('/api/auth/google/config').json() == {'enabled': False, 'client_id': None}
    assert client.post('/api/auth/google/challenge', json={}).status_code == 503
    security._guard_hits.clear(); monkeypatch.setenv('AUTH_GOOGLE_RATE_PER_MINUTE', '1')
    client.post('/api/auth/google/challenge', json={})
    assert client.post('/api/auth/google/challenge', json={}).status_code == 429
