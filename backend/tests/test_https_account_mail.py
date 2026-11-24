import hashlib
import http.client
import json
import ssl
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import account_recovery, accounts
from app.main import app


@pytest.fixture
def configured(monkeypatch):
    for name in ('SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_PORT', 'MAIL_PROVIDER',
                 'RESEND_API_KEY', 'BREVO_API_KEY', 'MAIL_FROM', 'PUBLIC_SITE_URL', 'RENDER', 'MAIL_ALLOW_RENDER_SMTP'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('PUBLIC_SITE_URL', 'https://travel.example.org')
    monkeypatch.setenv('MAIL_FROM', 'Masr Guide AI <accounts@travel.example.org>')
    monkeypatch.setenv('MAIL_PROVIDER', 'resend')
    monkeypatch.setenv('RESEND_API_KEY', 'unit-test-only-placeholder')
    return monkeypatch


def transport(monkeypatch, status=200, body=b'{"id":"accepted-test-id"}', error=None):
    calls = []

    class Connection:
        def __init__(self, host, timeout, context):
            calls.append({'host': host, 'timeout': timeout, 'context': context})

        def request(self, *args, **kwargs):
            calls[0]['request'] = (args, kwargs)
            if error:
                raise error

        def getresponse(self):
            return type('Response', (), {'status': status, 'read': lambda self, limit: body[:limit]})()

        def close(self):
            calls[0]['closed'] = True

    monkeypatch.setattr(account_recovery.http.client, 'HTTPSConnection', Connection)
    return calls


def test_https_mail_is_available_on_render_without_smtp(configured):
    configured.setenv('RENDER', 'true')
    assert account_recovery.mail_ready()
    configured.delenv('RESEND_API_KEY')
    assert not account_recovery.mail_ready()


@pytest.mark.parametrize('name,value', [
    ('MAIL_PROVIDER', 'unknown'), ('PUBLIC_SITE_URL', 'http://travel.example.org'),
    ('PUBLIC_SITE_URL', 'https://user:password@travel.example.org'),
    ('PUBLIC_SITE_URL', 'https://['), ('PUBLIC_SITE_URL', 'https://travel.example.org/other'),
    ('MAIL_FROM', 'onboarding@resend.dev'), ('MAIL_FROM', 'not-an-address'),
    ('MAIL_FROM', 'accounts@example.org\r\nBcc: attacker@example.org')
])
def test_incomplete_unsafe_or_test_sender_config_stays_disabled(configured, name, value):
    configured.setenv(name, value)
    assert not account_recovery.mail_ready()


def test_fixed_https_transport_preserves_single_use_link_and_closes(configured):
    calls = transport(configured)
    account_recovery._send_link('recipient@example.org', 'reset', 'test-token')
    call = calls[0]
    assert call['host'] == 'api.resend.com'
    assert call['timeout'] == 10
    assert call['context'].check_hostname and call['context'].verify_mode == ssl.CERT_REQUIRED
    args, kwargs = call['request']
    assert args[:2] == ('POST', '/emails')
    payload = json.loads(args[2])
    assert payload['to'] == ['recipient@example.org']
    assert payload['from'] == 'Masr Guide AI <accounts@travel.example.org>'
    assert payload['subject'].endswith('Reset your password')
    assert 'https://travel.example.org/#/account?action=reset&token=test-token' in payload['text']
    assert kwargs['headers']['Authorization'] == 'Bearer unit-test-only-placeholder'
    assert call['closed']


def test_brevo_https_supports_verified_free_email_sender(configured):
    configured.setenv('MAIL_PROVIDER', 'brevo')
    configured.setenv('MAIL_FROM', 'Masr Guide AI <owner@gmail.com>')
    configured.setenv('BREVO_API_KEY', 'unit-test-brevo-placeholder')
    configured.setenv('RENDER', 'true')
    assert account_recovery.mail_ready()
    calls = transport(configured, 201, b'{"messageId":"accepted-test-message"}')
    account_recovery._send_link('recipient@example.org', 'verify', 'test-token')
    assert calls[0]['host'] == 'api.brevo.com'
    args, kwargs = calls[0]['request']
    assert args[:2] == ('POST', '/v3/smtp/email')
    payload = json.loads(args[2])
    assert payload['sender'] == {'name': 'Masr Guide AI', 'email': 'owner@gmail.com'}
    assert payload['to'] == [{'email': 'recipient@example.org'}]
    assert 'action=verify&token=test-token' in payload['textContent']
    assert kwargs['headers']['api-key'] == 'unit-test-brevo-placeholder'
    assert 'Authorization' not in kwargs['headers']
    assert calls[0]['closed']
    configured.delenv('BREVO_API_KEY')
    assert not account_recovery.mail_ready()


def test_brevo_rejects_receipt_from_other_provider(configured):
    configured.setenv('MAIL_PROVIDER', 'brevo')
    configured.setenv('BREVO_API_KEY', 'unit-test-brevo-placeholder')
    calls = transport(configured)
    with pytest.raises(ValueError):
        account_recovery._send_link('recipient@example.org', 'verify', 'test-token')
    assert calls[0]['closed']


@pytest.mark.parametrize('status,body', [
    (302, b'{"id":"redirect"}'), (403, b'{"message":"private error"}'),
    (429, b'{}'), (200, b'not-json'), (200, b'{}'), (200, b'{"id":null}'),
    (200, b'[]'), (200, b'x' * 8193)
])
def test_failed_or_unconfirmed_send_is_not_success(configured, status, body):
    calls = transport(configured, status, body)
    with pytest.raises(ValueError):
        account_recovery._send_link('recipient@example.org', 'verify', 'test-token')
    assert calls[0]['closed']


def test_failed_https_delivery_invalidates_only_its_action_token(configured, tmp_path):
    configured.setattr(accounts, '_DB', tmp_path / 'accounts.sqlite3')
    configured.delenv('NEON_DATABASE_URL', raising=False)
    configured.setenv('DATABASE_PATH', str(tmp_path / 'catalog.sqlite3'))
    configured.setenv('AI_PROVIDER', 'offline')
    calls = transport(configured, error=http.client.RemoteDisconnected('private provider detail'))
    with TestClient(app) as client:
        user = client.post('/api/auth/register', json={'email': 'recipient@example.org', 'password': 'unit-test-password-2026'}).json()['user']
        digest = hashlib.sha256(b'test-token').hexdigest()
        with accounts._open() as db:
            db.execute('INSERT INTO account_actions VALUES (?,?,?,?)',
                       (digest, user['id'], 'reset', (accounts._now() + timedelta(minutes=30)).isoformat()))
            db.execute('INSERT INTO account_actions VALUES (?,?,?,?)',
                       ('other-test-digest', user['id'], 'verify', (accounts._now() + timedelta(minutes=30)).isoformat()))
        account_recovery._deliver('recipient@example.org', 'reset', 'test-token')
        with accounts._open() as db:
            assert db.execute('SELECT 1 FROM account_actions WHERE token_hash=?', (digest,)).fetchone() is None
            assert db.execute('SELECT 1 FROM account_users WHERE id=?', (user['id'],)).fetchone()
            assert db.execute('SELECT 1 FROM account_actions WHERE token_hash=?', ('other-test-digest',)).fetchone()
    assert calls[0]['closed']


def test_existing_secure_smtp_transport_remains_available(configured):
    configured.setenv('MAIL_PROVIDER', 'smtp')
    for name in ('SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD'):
        configured.setenv(name, 'unit-test-placeholder')
    assert account_recovery.mail_ready()
    configured.setenv('RENDER', 'true')
    assert not account_recovery.mail_ready()
    configured.setenv('MAIL_ALLOW_RENDER_SMTP', 'true')
    assert account_recovery.mail_ready()
