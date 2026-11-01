"""Adversarial API boundary, concurrent save, privacy and deployment regressions."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app import accounts, main, security
from app.schemas import TripState


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'users.sqlite3')
    accounts.setup()
    security._guard_hits.clear()
    main._chat_calls.clear()
    yield
    security._guard_hits.clear()
    main._chat_calls.clear()


def _register(client, email='secure@example.com'):
    res = client.post('/api/auth/register', json={'email': email, 'password':'SecureTravelerPassword!234'})
    assert res.status_code == 201, res.text
    return {'Authorization': 'Bearer ' + res.json()['token']}


def _trip():
    return {'days':[{'day':1, 'city':'Cairo', 'stops':[]}]}


@pytest.mark.parametrize('declared', [None, b'5', b'garbage'])
def test_streaming_body_limit_ignores_spoofed_or_missing_content_length(declared):
    """Raw ASGI data arrives in chunks; a fake short header must not bypass 413."""
    async def request():
        scope = {'type':'http', 'method':'POST','path':'/api/chat', 'raw_path':b'/api/chat',
                 'query_string':b'', 'root_path':'', 'scheme':'http', 'server':('testserver',80),
                 'client':('127.0.0.1',5656), 'headers':[(b'content-type',b'application/json')] +
                 ([(b'content-length', declared)] if declared is not None else [])}
        items = [
            {'type':'http.request','body':b'x'*270000, 'more_body': True},
            {'type':'http.request','body':b'y'*270000, 'more_body': False},
        ]
        sent=[]
        async def receive(): return items.pop(0)
        async def send(item): sent.append(item)
        await main.app(scope,receive,send)
        return sent
    events=asyncio.run(request())
    starts=[e for e in events if e['type']=='http.response.start']
    assert starts[0]['status']==413
    assert b'512 KB' in b''.join(e.get('body',b'') for e in events)


def test_oversized_declared_content_length_does_not_need_to_read_request():
    async def request():
        scope={'type':'http','method':'POST','path':'/api/plan', 'raw_path':b'/api/plan',
               'query_string':b'', 'root_path':'', 'scheme':'http', 'server':('testserver',80),
               'client':('127.0.0.1',9000), 'headers':[(b'content-length', b'999999999')]}
        sent=[]
        async def receive(): raise AssertionError('Oversized declared body should not be read')
        async def send(message): sent.append(message)
        await main.app(scope,receive,send)
        return sent
    assert asyncio.run(request())[0]['status']==413


def test_production_trip_writes_require_if_match(client, monkeypatch):
    auth=_register(client)
    trip = client.post('/api/my/trips',json={'title':'First trip','itinerary':_trip()}, headers=auth).json()
    uri='/api/my/trips/'+trip['id']
    version=client.get(uri, headers=auth).json()['updated_at']
    monkeypatch.setenv('APP_ENV','production')
    assert client.put(uri,json={'title':'Changed','itinerary':_trip()},headers=auth).status_code==428
    assert client.put(uri,json={'title':'Changed','itinerary':_trip()},headers={**auth, 'If-Match':version}).status_code==200
    assert client.put(uri,json={'title':'Stale','itinerary':_trip()},headers={**auth, 'If-Match':version}).status_code==409
    assert client.get(uri,headers=auth).json()['title']=='Changed'


def test_production_conversation_writes_require_if_match(client, monkeypatch):
    auth=_register(client)
    payload={'title':'Cairo conversation','messages':[{'role':'user','text':'Tell me about Cairo'}]}
    created=client.post('/api/my/conversations',json=payload,headers=auth).json()
    uri='/api/my/conversations/'+created['id']
    monkeypatch.setenv('REQUIRE_CONDITIONAL_WRITES','true')
    assert client.put(uri,json=payload,headers=auth).status_code==428
    assert client.put(uri,json=payload,headers={**auth, 'If-Match':created['updated_at']}).status_code==200


def test_account_deletion_requires_password_and_confirmation_revokes_all_sessions(client):
    a=_register(client)
    login=client.post('/api/auth/login',json={'email':'secure@example.com','password':'SecureTravelerPassword!234'}).json()
    b={'Authorization':'Bearer '+login['token']}
    client.post('/api/my/trips',json={'title':'Private vacation','itinerary':_trip()},headers=a)
    client.post('/api/my/conversations',json={'title':'Private conversation', 'messages':[{'role':'user','text':'Hello'}]}, headers=a)
    uri='/api/my/account'
    assert client.request('DELETE', uri,json={'password':'wrong-but-long-enough','confirmation':'DELETE MY ACCOUNT'},headers=a).status_code==403
    assert client.request('DELETE', uri,json={'password':'SecureTravelerPassword!234','confirmation':'not confirmed'},headers=a).status_code==422
    assert client.get('/api/my/trips',headers=b).json()['trips']
    result=client.request('DELETE', uri,json={'password':'SecureTravelerPassword!234','confirmation':'DELETE MY ACCOUNT'},headers=a)
    assert result.status_code==200 and result.json()['deleted'] is True
    assert client.get('/api/my/trips',headers=a).status_code==401
    assert client.get('/api/my/conversations',headers=b).status_code==401
    assert client.post('/api/auth/login',json={'email':'secure@example.com','password':'SecureTravelerPassword!234'}).status_code==401
    with accounts._open() as c:
        assert c.execute('SELECT COUNT(*) FROM account_users').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM account_tokens').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM account_trips').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM account_conversations').fetchone()[0]==0


def test_nonfinite_nested_conversation_payload_does_not_raise_server_error(client):
    auth=_register(client)
    payload={'title':'Bad conversation','messages':[{'role':'user','text':'Hi!'}],
             'itinerary':{'days':[{'day':1,'city':'Cairo','cost': float('inf')}]}}
    r=client.post('/api/my/conversations',content=json.dumps(payload), headers={**auth,'Content-Type':'application/json'})
    assert r.status_code==422, r.text

@pytest.mark.parametrize('stop', [None, '', 12, [], {}, {'place':None},
                                  {'place':{}}, {'place':{'id':'x'}},
                                  {'place':{'id':42, 'name':'Karnak'}}])
def test_trip_rejects_malformed_stop_entries_that_would_crash_react(client, stop):
    auth=_register(client)
    payload={'title':'Imported trip','itinerary':{'days':[{'day':1,'city':'Luxor','stops':[stop]}]}}
    r=client.post('/api/my/trips',json=payload,headers=auth)
    assert r.status_code==422, r.text
    assert client.get('/api/my/trips',headers=auth).json()['trips']==[]


def test_saved_itinerary_accepts_full_curated_stop_from_planner(client):
    auth=_register(client)
    plan=client.post('/api/plan',json={'cities':['Cairo'],'days':1}).json()
    result=client.post('/api/my/trips',json={'title':'Verified visit','itinerary':plan},headers=auth)
    assert result.status_code==201, result.text
    loaded=client.get('/api/my/trips/'+result.json()['id'],headers=auth).json()['itinerary']
    assert loaded['days'][0]['stops']


def test_account_deletion_cannot_remove_other_user(client):
    a=_register(client, 'first@example.com')
    b=_register(client, 'second@example.com')
    client.request('DELETE','/api/my/account',json={
        'password':'SecureTravelerPassword!234','confirmation':'DELETE MY ACCOUNT'},headers=a)
    assert client.get('/api/auth/me',headers=a).status_code==401
    assert client.get('/api/auth/me',headers=b).status_code==200

@pytest.mark.parametrize('bad_email', [
    'a@example.com\r\nBcc:someone@example.com', 'two@@example.com',
    'abc @example.com', 'abc@example.com/', 'abc@example..com',
    'abc@example-.com', '.abc@example.com', 'foo@localhost',
])
def test_account_registration_rejects_ambiguous_emails(client, bad_email):
    res=client.post('/api/auth/register', json={'email':bad_email,'password':'SecureTravelerPassword!234'})
    assert res.status_code==422, res.text


def test_readiness_requires_real_database_tables(client, monkeypatch, tmp_path):
    assert client.get('/api/ready').status_code==200
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'empty.sqlite3')
    assert client.get('/api/ready').status_code==503


def test_production_storage_requires_explicit_operator_confirmation(monkeypatch):
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.delenv('MASR_DURABLE_STORAGE_CONFIRMED', raising=False)
    with pytest.raises(RuntimeError, match='persistent'):
        main.validate_deployment_settings()
    monkeypatch.setenv('MASR_DURABLE_STORAGE_CONFIRMED','yes')
    monkeypatch.setenv('BACKUP_RECOVERY_VERIFIED','yes')
    monkeypatch.setenv('MASR_USER_DB','/data/travelers.sqlite3')
    monkeypatch.setenv('DATABASE_PATH','/data/tourism.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY','test-nonlive-placeholder')
    monkeypatch.delenv('TRUST_PROXY_HEADERS', raising=False)
    main.validate_deployment_settings()


def test_account_storage_path_resolves_environment_after_import(monkeypatch, tmp_path):
    from app import accounts
    target = tmp_path / 'configured_from_env.sqlite3'
    monkeypatch.setattr(accounts, '_DB', None)
    monkeypatch.setenv('MASR_USER_DB', str(target))
    assert accounts._db_path() == target
    accounts.setup()
    assert target.is_file()
