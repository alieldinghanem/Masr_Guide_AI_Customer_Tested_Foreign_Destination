import hashlib
from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import accounts, account_recovery, provider_status, security
from app.main import app
from app.schemas import ConsultRequest, TripState, TravelerProfile
from app.travel_agent import consult_travel
from app.traveler_profile import update_profile


@pytest.fixture
def platform(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'accounts.sqlite3')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'catalog.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    monkeypatch.setenv('RATING_RATE_PER_MINUTE', '100')
    monkeypatch.setenv('AUTH_EMAIL_RATE_PER_MINUTE', '100')
    monkeypatch.setenv('ADMIN_API_TOKEN', 'private-test-staff-token-2026')
    monkeypatch.delenv('NEON_DATABASE_URL', raising=False)
    security._guard_hits.clear()
    with TestClient(app) as client:
        yield client


def register(client, email='traveler@example.org'):
    reply = client.post('/api/auth/register', json={'email': email, 'password': 'Original-password-2026!'})
    assert reply.status_code == 201, reply.text
    return {'Authorization': 'Bearer ' + reply.json()['token']}


@pytest.fixture
def mail(monkeypatch):
    sent = []
    monkeypatch.setattr(account_recovery, 'mail_ready', lambda: True)
    monkeypatch.setattr(account_recovery, '_send_link', lambda address, purpose, token: sent.append((address, purpose, token)))
    return sent


def test_email_disabled_is_honest_and_existing_login_survives(platform, monkeypatch):
    monkeypatch.setattr(account_recovery, 'mail_ready', lambda: False)
    register(platform)
    assert platform.get('/api/auth/email-capabilities').json()['password_recovery'] is False
    assert platform.post('/api/auth/password-reset/request', json={'email': 'traveler@example.org'}).status_code == 503
    assert platform.post('/api/auth/login', json={'email': 'traveler@example.org', 'password': 'Original-password-2026!'}).status_code == 200


def test_reset_is_single_use_hashed_and_revokes_old_sessions(platform, mail):
    headers = register(platform)
    requested = platform.post('/api/auth/password-reset/request', json={'email': 'traveler@example.org'})
    unknown = platform.post('/api/auth/password-reset/request', json={'email': 'unknown@example.org'})
    assert requested.status_code == unknown.status_code == 202
    assert requested.json() == unknown.json()
    token = mail[0][2]
    assert token not in requested.text
    with accounts._open() as db:
        row = db.execute('SELECT token_hash FROM account_actions').fetchone()
        assert row['token_hash'] == hashlib.sha256(token.encode()).hexdigest()
    payload = {'token': token, 'password': 'Replacement-password-2026!'}
    assert platform.post('/api/auth/password-reset/confirm', json=payload).status_code == 200
    assert platform.get('/api/auth/me', headers=headers).status_code == 401
    assert platform.post('/api/auth/password-reset/confirm', json=payload).status_code == 400
    assert platform.post('/api/auth/login', json={'email': 'traveler@example.org', 'password': payload['password']}).status_code == 200
    assert platform.post('/api/auth/login', json={'email': 'traveler@example.org', 'password': 'Original-password-2026!'}).status_code == 401


def test_expired_wrong_purpose_and_short_password_do_not_consume_link(platform, mail):
    headers = register(platform)
    assert platform.post('/api/auth/email-verification/request', headers=headers).status_code == 202
    token = mail[0][2]
    assert platform.post('/api/auth/password-reset/confirm', json={'token': token, 'password': 'Long-enough-password'}).status_code == 400
    assert platform.post('/api/auth/email-verification/confirm', json={'token': token}).json() == {'verified': True}
    assert platform.get('/api/auth/email-status', headers=headers).json() == {'verified': True}
    assert platform.post('/api/auth/email-verification/confirm', json={'token': token}).status_code == 400
    with accounts._open() as db:
        db.execute('DELETE FROM account_mail_requests')
    platform.post('/api/auth/password-reset/request', json={'email': 'traveler@example.org'})
    token = mail[-1][2]
    assert platform.post('/api/auth/password-reset/confirm', json={'token': token, 'password': 'short'}).status_code == 422
    with accounts._open() as db:
        db.execute('UPDATE account_actions SET expires_at=?', ((accounts._now() - timedelta(seconds=1)).isoformat(),))
    assert platform.post('/api/auth/password-reset/confirm', json={'token': token, 'password': 'Another-long-password'}).status_code == 400


def test_email_cooldown_and_delivery_failure_do_not_leak_tokens(platform, mail, monkeypatch):
    register(platform)
    for _ in range(2):
        assert platform.post('/api/auth/password-reset/request', json={'email': 'traveler@example.org'}).status_code == 202
    assert len(mail) == 1
    with accounts._open() as db:
        db.execute('DELETE FROM account_mail_requests')
    def fail(*args):
        raise OSError('mail transport unavailable')
    monkeypatch.setattr(account_recovery, '_send_link', fail)
    assert platform.post('/api/auth/password-reset/request', json={'email': 'traveler@example.org'}).status_code == 202
    with accounts._open() as db:
        assert db.execute('SELECT COUNT(*) FROM account_actions').fetchone()[0] == 0


@pytest.mark.parametrize('ages', [[True], [-1], [18], ['4']])
def test_profile_rejects_invalid_ages(ages):
    with pytest.raises(ValidationError):
        TravelerProfile(children_ages=ages)


def test_profile_uses_age_labels_not_duration_or_budget():
    assert update_profile({}, 'Plan 14 days, budget 4000 USD')['children_ages'] == []
    profile = update_profile({}, '2 adults, children aged 4 and 7, budget 4000 USD, halal food')
    assert profile == {'adults': 2, 'children_ages': [4, 7], 'food_preferences': ['halal']}
    assert update_profile(profile, '٣ بالغين والأطفال أعمارهم ٥ و٩')['children_ages'] == [5, 9]


def test_family_memory_survives_day_edit_extension_and_saved_conversation(platform):
    headers = register(platform)
    first = consult_travel(ConsultRequest(message='Plan 5 days in Cairo and Alexandria. 2 adults, children aged 4 and 7, halal food', language='English'))
    profile = first['trip_state']['traveler_profile']
    assert first['trip_state']['family'] is True
    second = consult_travel(ConsultRequest(message='Make Day 3 one activity for children', language='English', trip_state=TripState.model_validate(first['trip_state'])))
    assert second['trip_state']['traveler_profile'] == profile
    assert [d for d in first['itinerary']['days'] if d['day'] != 3] == [d for d in second['itinerary']['days'] if d['day'] != 3]
    third = consult_travel(ConsultRequest(message='زود إجمالي مدة الرحلة يوم للإسكندرية من غير ما تقلل أيام القاهرة', language='Arabic', trip_state=TripState.model_validate(second['trip_state'])))
    assert third['trip_state']['traveler_profile'] == profile
    assert third['trip_state']['days'] == 6
    saved = platform.post('/api/my/conversations', headers=headers, json={'title': 'Family trip', 'messages': [{'role': 'user', 'text': 'My family trip'}], 'trip_state': third['trip_state'], 'itinerary': third['itinerary']})
    assert saved.status_code == 201, saved.text
    restored = platform.get('/api/my/conversations/' + saved.json()['id'], headers=headers).json()
    assert restored['trip_state']['traveler_profile'] == profile


def test_reports_require_accounts_and_staff_and_hide_every_public_view(platform):
    headers = register(platform)
    posted = platform.post('/api/ratings/giza-pyramids/comments', headers=headers, json={'comment': 'An interesting visit.'}).json()
    item = posted['comments'][0]
    report = {'target_id': 'giza-pyramids', 'comment_id': item['comment_id'], 'reason': 'misinformation'}
    assert 'voter_hash' not in item
    assert platform.post('/api/community/reports', json=report).status_code == 401
    assert platform.post('/api/community/reports', json=report, headers=headers).status_code == 202
    assert platform.get('/api/admin/community/reports').status_code == 403
    staff = {'X-Admin-Key': 'private-test-staff-token-2026'}
    assert len(platform.get('/api/admin/community/reports', headers=staff).json()['reports']) == 1
    review_url = '/api/admin/community/reports/' + item['comment_id']
    assert platform.post(review_url, headers=staff, json={'action': 'hide'}).status_code == 200
    assert platform.get('/api/ratings/giza-pyramids/comments').json()['count'] == 0
    assert platform.get('/api/ratings/recent-comments').json()['comments'] == []
    assert platform.post('/api/ratings/giza-pyramids/comments', headers=headers, json={'comment': 'Bypass the decision.'}).status_code == 403
    assert platform.post(review_url, headers=staff, json={'action': 'restore'}).status_code == 200
    assert platform.get('/api/ratings/giza-pyramids/comments').json()['count'] == 1


def test_stale_report_cannot_moderate_new_comment(platform):
    headers = register(platform)
    url = '/api/ratings/giza-pyramids/comments'
    item = platform.post(url, headers=headers, json={'comment': 'Original version.'}).json()['comments'][0]
    platform.post('/api/community/reports', headers=headers, json={'target_id': 'giza-pyramids', 'comment_id': item['comment_id'], 'reason': 'spam'})
    platform.post(url, headers=headers, json={'comment': 'Corrected version.'})
    response = platform.post('/api/admin/community/reports/' + item['comment_id'], headers={'X-Admin-Key': 'private-test-staff-token-2026'}, json={'action': 'hide'})
    assert response.status_code == 409
    assert platform.get(url).json()['comments'][0]['comment'] == 'Corrected version.'


def test_coastal_favorites_are_owned_and_validated(platform):
    headers = register(platform)
    assert platform.post('/api/my/favorites/coast:dahab', headers=headers).status_code == 200
    assert platform.post('/api/my/favorites/coast:invented', headers=headers).status_code == 404
    assert platform.get('/api/my/favorites', headers=headers).json()['place_ids'] == ['coast:dahab']


def test_provider_verification_is_fresh_config_scoped_and_never_local(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-provider-key')
    provider_status._observations.clear()
    assert provider_status.snapshot()['state'] == 'unverified'
    provider_status.observe('gemini-3.5-flash-lite', True)
    assert provider_status.snapshot()['state'] == 'verified'
    monkeypatch.setenv('GEMINI_API_KEY', 'different-test-key')
    assert provider_status.snapshot()['state'] == 'unverified'
    provider_status.observe('gemini-3.5-flash-lite', False)
    assert provider_status.snapshot()['state'] == 'unavailable'
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    assert provider_status.snapshot()['state'] == 'disabled'


def test_staff_probe_requires_real_expected_response(platform, monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-provider-key')
    assert platform.post('/api/admin/ai-check').status_code == 403
    monkeypatch.setattr('app.gemini_client.generate', lambda *a, **k: 'MASR_OK')
    headers = {'X-Admin-Key': 'private-test-staff-token-2026'}
    result = platform.post('/api/admin/ai-check', headers=headers).json()
    assert result['result'] == 'success' and result['connection']['state'] == 'verified'
    def fail(*args, **kwargs):
        raise HTTPException(502, 'test failure')
    monkeypatch.setattr('app.gemini_client.generate', fail)
    result = platform.post('/api/admin/ai-check', headers=headers).json()
    assert result['result'] == 'failed' and result['connection']['state'] == 'unavailable'


def test_aggregate_metrics_are_opt_in_and_never_store_conversation_data(platform, monkeypatch):
    from app.metrics import record
    staff = {'X-Admin-Key': 'private-test-staff-token-2026'}
    monkeypatch.delenv('MASR_AGGREGATE_METRICS_ENABLED', raising=False)
    record('plan_created')
    assert platform.get('/api/admin/metrics', headers=staff).json()['counts'] == []
    monkeypatch.setenv('MASR_AGGREGATE_METRICS_ENABLED', 'true')
    record('plan_created'); record('plan_created'); record('private visitor text must be ignored')
    assert platform.get('/api/admin/metrics').status_code == 403
    rows = platform.get('/api/admin/metrics', headers=staff).json()['counts']
    assert len(rows) == 1 and rows[0]['event'] == 'plan_created' and rows[0]['count'] == 2
    assert set(rows[0]) == {'day', 'event', 'count'}
