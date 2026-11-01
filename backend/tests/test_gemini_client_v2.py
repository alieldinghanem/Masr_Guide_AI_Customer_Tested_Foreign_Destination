import json
from unittest.mock import patch
from app.gemini_client import generate


class FakeReply:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


def test_gemini_rest_contract_without_real_key(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'mock-key-do-not-publish')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-2.5-flash')
    calls = []
    def fake_open(req, timeout):
        assert req.full_url.endswith('models/gemini-2.5-flash:generateContent')
        assert req.headers['X-goog-api-key'] == 'mock-key-do-not-publish'
        body = json.loads(req.data)
        assert body['contents'][0]['parts'][0]['text'] == 'trip question'
        assert body['generationConfig']['responseMimeType'] == 'application/json'
        calls.append(body)
        resp = FakeReply()
        resp.read = lambda *args: b''
        # json.load normally wants a file-like object
        return type('Ctx', (), {'__enter__': lambda self: self,
                                '__exit__':lambda *args: False,
                                'read': lambda *args: json.dumps({'candidates':[{'content':{'parts':[{'text':'{"action":"plan"}'}]}}]}).encode()})()
    with patch('app.gemini_client.urlopen', fake_open):
        text = generate('trip question', 'instructions', json_mode=True)
    assert json.loads(text)['action'] == 'plan'
    assert len(calls) == 1


def test_fastapi_serves_no_build_demo(client):
    page = client.get('/demo')
    assert page.status_code == 200
    assert '<title>Masr Guide AI' in page.text
    assert '/api/consult' in page.text
    assert '<script>' in page.text


def test_gemini_multiturn_roles_not_flattened_in_a_single_user_prompt(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setenv('GEMINI_API_KEY', 'mock-not-a-secret')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-2.5-flash')
    captured = []
    def fake_open(req, timeout):
        captured.append(json.loads(req.data))
        payload = json.dumps({'candidates':[{'content':{'parts':[{'text':'Answer'}]}}]}).encode()
        return type('Ctx', (), {'__enter__': lambda self: self,
                                '__exit__': lambda *args: False,
                                'read': lambda *args: payload})()
    turns = [SimpleNamespace(role='user', content='I am visiting Cairo'),
             SimpleNamespace(role='assistant', content='What interests you?'),
             SimpleNamespace(role='user', content='Museums')]
    with patch('app.gemini_client.urlopen', fake_open):
        result = generate('Use reference [1]. Which museum?', 'Stay grounded', history=turns)
    assert result == 'Answer'
    data = captured[0]
    assert [x['role'] for x in data['contents']] == ['user', 'model', 'user']
    assert data['contents'][-1]['parts'][0]['text'].endswith('Which museum?')
    assert 'Stay grounded' in data['system_instruction']['parts'][0]['text']


def test_gemini_ignores_orphaned_assistant_greeting(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setenv('GEMINI_API_KEY', 'mock-not-real')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-2.5-flash')
    requests = []
    def fake_open(req, timeout):
        requests.append(json.loads(req.data))
        payload = json.dumps({'candidates':[{'content':{'parts':[{'text':'ok'}]}}]}).encode()
        return type('Ctx', (), {'__enter__': lambda self: self,
                                '__exit__': lambda *args: False,
                                'read': lambda *args: payload})()
    history = [SimpleNamespace(role='assistant', content='Welcome!')]
    with patch('app.gemini_client.urlopen', fake_open):
        assert generate('Tell me about Cairo', 'Be helpful', history=history) == 'ok'
    assert requests[0]['contents'] == [{'role':'user','parts':[{'text':'Tell me about Cairo'}]}]


def test_grounded_chat_passes_role_history_to_gemini(monkeypatch, client):
    from app import guide
    from app.main import _chat_calls
    _chat_calls.clear()
    monkeypatch.setattr(guide, 'gemini_key', lambda: 'test-not-real')
    seen = []
    def pretend_gemini(prompt, instructions, **kwargs):
        seen.append(kwargs)
        return 'Based on reference [1], consider the Egyptian Museum.'
    monkeypatch.setattr(guide, 'generate', pretend_gemini)
    response = client.post('/api/chat', json={
        'language':'English', 'message':'What should I see in Cairo?',
        'history':[{'role':'user', 'content':'I enjoy history'},
                   {'role':'assistant', 'content':'Which city?'},
                   {'role':'user','content':'Cairo'}]})
    assert response.status_code == 200
    assert response.json()['mode'] == 'gemini-rag'
    assert len(seen) == 1
    assert len(seen[0]['history']) == 3
