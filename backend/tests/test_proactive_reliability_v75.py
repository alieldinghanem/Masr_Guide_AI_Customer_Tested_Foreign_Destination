"""Forward-looking adversarial regression checks, not a live-model benchmark."""
import concurrent.futures
import json
import threading

import pytest
from fastapi.testclient import TestClient
from app import accounts, main, security
from app.commerce import OfferIn
from app.schemas import TripState


@pytest.fixture(autouse=True)
def guard_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, "_DB", tmp_path / "isolated_users.sqlite3")
    security._guard_hits.clear()
    main._chat_calls.clear()
    yield
    security._guard_hits.clear()
    main._chat_calls.clear()


def _auth(client, email='reliable@example.com'):
    r = client.post('/api/auth/register', json={'email': email, 'password': 'a-real-password-longer-than-12'})
    assert r.status_code == 201, r.text
    return {'Authorization': 'Bearer ' + r.json()['token']}


def test_bruteforce_login_limited_and_headers_not_trusted(client, monkeypatch):
    monkeypatch.setenv('AUTH_LOGIN_RATE_PER_MINUTE', '2')
    payload = {'email': 'missing@example.com', 'password': 'a-real-password-longer-than-12'}
    first = client.post('/api/auth/login', json=payload, headers={'X-Real-IP': '1.1.1.1'})
    second = client.post('/api/auth/login', json=payload, headers={'X-Real-IP': '2.2.2.2'})
    last = client.post('/api/auth/login', json=payload, headers={'X-Real-IP': '3.3.3.3'})
    assert [first.status_code, second.status_code, last.status_code] == [401, 401, 429]
    assert int(last.headers['Retry-After']) >= 1
    assert last.headers['Cache-Control'] == 'no-store'
    assert not security.sensitive_requests(type('R', (), {'url': type('U', (), {'path':'/api/health'})(), 'method':'GET'})())


def test_register_and_partner_rate_limits(client, monkeypatch):
    monkeypatch.setenv('AUTH_REGISTER_RATE_PER_MINUTE', '2')
    data = {'email': 'person@example.com', 'password': 'a-real-password-longer-than-12'}
    assert client.post('/api/auth/register', json=data).status_code == 201
    assert client.post('/api/auth/register', json=data).status_code == 409
    assert client.post('/api/auth/register', json=data).status_code == 429
    security._guard_hits.clear()
    monkeypatch.setenv('PARTNER_RATE_PER_MINUTE', '1')
    assert client.post('/api/partners/apply', json={'company':'Partner Egypt', 'email':'partner@example.com'}).status_code == 503
    assert client.post('/api/partners/apply', json={'company':'Partner Egypt', 'email':'partner@example.com'}).status_code == 429


def test_staff_bruteforce_throttled_without_valid_token(client, monkeypatch):
    monkeypatch.setenv('ADMIN_RATE_PER_MINUTE', '2')
    monkeypatch.setenv('ADMIN_API_TOKEN', 'x'*40)
    assert client.get('/api/admin/overview', headers={'X-Admin-Key': 'wrong'}).status_code == 403
    assert client.get('/api/admin/overview', headers={'X-Admin-Key': 'wrong'}).status_code == 403
    assert client.get('/api/admin/overview', headers={'X-Admin-Key': 'wrong'}).status_code == 429


def test_counters_fail_closed_if_new_peers_exceed_capacity(monkeypatch):
    monkeypatch.setattr(security, '_MAX_KEYS', 2)
    class Req:
        url = type('U', (), {'path': '/api/auth/login'})()
        method = 'POST'
        def __init__(self, peer): self.client = type('C', (), {'host': peer})()
    assert security.sensitive_requests(Req('A')) == 0
    assert security.sensitive_requests(Req('B')) == 0
    assert security.sensitive_requests(Req('C')) > 0
    assert len(security._guard_hits) == 2


def test_proxy_header_not_trusted_in_production_without_allowlist(monkeypatch):
    from starlette.requests import Request
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('TRUST_PROXY_HEADERS', '1')
    monkeypatch.delenv('TRUSTED_PROXY_IPS', raising=False)
    scope = {'type': 'http', 'method':'GET', 'path':'/api/chat', 'headers':[(b'x-real-ip', b'192.0.2.99')], 'client': ('127.0.0.1', 1234), 'scheme':'http', 'server':('testserver',80), 'query_string':b''}
    req = Request(scope)
    assert main.client_key(req) == '127.0.0.1'
    monkeypatch.setenv('TRUSTED_PROXY_IPS', '127.0.0.1')
    assert main.client_key(req) == '192.0.2.99'


@pytest.mark.parametrize('bad', [
    {'days':'nope'},
    {'days': 'string'},
    {'days': [{'day':1,'city':'Cairo'}, {'day':1,'city':'Luxor'}]},
    {'days': [{'day':2,'city':'Cairo'}]},
    {'days': [{'day':1,'city': None}]},
    {'days': [{'day':1,'city': 'Cairo', 'stops':'bad'}]},
    {'days': [{'day':1,'city': 'Cairo', 'stops':[{}] * 26}]},
    {'days': [{'day':1,'city':'Cairo'}] * 31},
])
def test_refuse_corrupt_itineraries_before_persistence(client, tmp_path, monkeypatch, bad):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'itineraries.sqlite3')
    auth = _auth(client, 't'+str(abs(hash(json.dumps(bad, sort_keys=True))))+'@example.com')
    r = client.post('/api/my/trips', json={'title':'Untrusted uploaded plan', 'itinerary':bad}, headers=auth)
    assert r.status_code == 422, (bad, r.text)
    assert client.get('/api/my/trips', headers=auth).json()['trips'] == []


def test_optimistic_concurrency_rejects_stale_trip_update(client, tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'concurrency.sqlite3')
    auth = _auth(client)
    plan={'days':[{'day':1,'city':'Cairo', 'stops':[]}]}
    saved = client.post('/api/my/trips', json={'title':'Version 1', 'itinerary':plan}, headers=auth).json()
    trip_id = saved['id']
    old_version = client.get('/api/my/trips/'+trip_id, headers=auth).json()['updated_at']
    assert client.put('/api/my/trips/'+trip_id, headers={**auth, 'If-Match':old_version}, json={'title':'Version 2', 'itinerary':plan}).status_code == 200
    stale = client.put('/api/my/trips/'+trip_id, headers={**auth, 'If-Match':old_version}, json={'title':'Old version overwrite', 'itinerary':plan})
    assert stale.status_code == 409
    assert client.get('/api/my/trips/'+trip_id, headers=auth).json()['title'] == 'Version 2'


def test_optimistic_concurrency_rejects_stale_conversation_update(client, tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'conversations.sqlite3')
    auth=_auth(client)
    body={'title':'Hello traveler', 'messages':[{'role':'user', 'text':'Visit Egypt'}]}
    cid=client.post('/api/my/conversations', json=body, headers=auth).json()['id']
    old=client.get('/api/my/conversations/'+cid, headers=auth).json()['updated_at']
    assert client.put('/api/my/conversations/'+cid, headers={**auth, 'If-Match':old}, json={**body, 'title':'Updated'}).status_code==200
    assert client.put('/api/my/conversations/'+cid, headers={**auth, 'If-Match':old}, json={**body, 'title':'Stale'}).status_code==409
    assert client.get('/api/my/conversations/'+cid, headers=auth).json()['title']=='Updated'


@pytest.mark.parametrize('bad_url', [
    'https://localhost/booking', 'https://127.0.0.1/offers', 'https://10.0.0.1/',
    'https://[::1]/', 'https://partner.internal/booking', 'https://no-hostname',
    'https://admin:secret@example.com/booking', 'http://example.com/booking',
])
def test_partner_redirects_require_public_hostnames(bad_url):
    data={'title': 'Example boat experience', 'city':'Hurghada', 'description':'Locally operated sample experience', 'partner':'Local Operator', 'target_url':bad_url}
    with pytest.raises(ValueError):
        OfferIn(**data)


def test_public_partner_url_can_still_be_used():
    data={'title': 'Example boat experience', 'city':'Hurghada', 'description':'Locally operated sample experience', 'partner':'Local Operator', 'target_url':'https://www.example.com/book'}
    assert OfferIn(**data).target_url == 'https://www.example.com/book'


def test_header_hardening_applied_without_breaking_api(client):
    res=client.get('/api/cities')
    assert res.status_code == 200
    assert res.headers['X-Content-Type-Options']=='nosniff'
    assert res.headers['X-Frame-Options']=='DENY'
    assert client.get('/api/auth/me').headers['Cache-Control']=='no-store'


def test_large_content_length_rejected_before_parsing(client):
    # Distinct from Pydantic limits: reject oversized uploads at HTTP boundary.
    response = client.post('/api/chat', content=b'{}', headers={'Content-Length': str(600000)})
    assert response.status_code == 413
    assert '512 KB' in response.json()['detail']


def test_nonfinite_numbers_cannot_be_saved_as_trips(client):
    auth = _auth(client, 'nonfinite@example.com')
    result = client.post('/api/my/trips', content=json.dumps({'title':'Impossible amount', 'itinerary':{'days':[{'day':1, 'city':'Cairo', 'cost': float('nan') }]}}), headers={**auth, 'Content-Type': 'application/json'})
    assert result.status_code == 422
