"""No network: contract tests for the new explicit OpenAI routing."""
import json
import sys
import types
import pytest
from fastapi import HTTPException
from app import guide, hotel_companion, travel_agent
from app.main import _chat_calls
from app.openai_client import generate
from app.schemas import ChatTurn


class FakeResponse:
    output_text = 'A grounded answer about Karnak. [1]'


class FakeOpenAI:
    calls = []
    def __init__(self, **kwargs):
        assert kwargs['api_key'] == 'mock-openai-key'
        self.responses = self
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse()


def test_openai_responses_sends_real_roles_and_no_storage(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'mock-openai-key')
    monkeypatch.setenv('OPENAI_MODEL', 'gpt-4o-mini')
    monkeypatch.setitem(sys.modules, 'openai', types.SimpleNamespace(OpenAI=FakeOpenAI))
    FakeOpenAI.calls.clear()
    history = [ChatTurn(role='user', content='Hi'), ChatTurn(role='assistant', content='Welcome')]
    answer = generate('What to see in Cairo?', 'Tourism instructions', history=history, json_mode=True)
    assert '[1]' in answer
    request = FakeOpenAI.calls[-1]
    assert request['model'] == 'gpt-4o-mini'
    assert request['store'] is False
    assert request['text']['format']['type'] == 'json_object'
    assert [msg['role'] for msg in request['input']] == ['user', 'assistant', 'user']
    assert 'Cairo' in request['input'][-1]['content']
    assert request['instructions'] == 'Tourism instructions'


def test_openai_fails_without_leaking_key(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'mock-openai-key')
    class Broken(FakeOpenAI):
        def create(self, **kwargs):
            raise RuntimeError('mock-openai-key: sensitive provider diagnostic')
    monkeypatch.setitem(sys.modules, 'openai', types.SimpleNamespace(OpenAI=Broken))
    with pytest.raises(HTTPException) as error:
        generate('test', 'instructions')
    assert error.value.status_code == 502
    assert 'mock-openai-key' not in str(error.value.detail)


def test_explicit_openai_overrides_gemini_for_guide(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'openai')
    monkeypatch.setenv('OPENAI_API_KEY', 'mock-openai-key')
    monkeypatch.setenv('GEMINI_API_KEY', 'gemini-should-not-be-used')
    monkeypatch.setattr(guide, 'generate', lambda *_a, **_kw: pytest.fail('Gemini was called'))
    calls = []
    def fake(prompt, instructions, **kwargs):
        calls.append((prompt, instructions, kwargs))
        return 'معبد الكرنك في الأقصر [1]'
    monkeypatch.setattr(guide, 'generate_openai', fake)
    assert client.get('/api/health').json()['guide_mode'] == 'openai-configured'
    result = client.post('/api/chat', json={
        'message': 'احكي لي عن معبد الكرنك', 'language': 'Arabic',
        'history': [{'role': 'user', 'content': 'أنا مهتم بالتاريخ'}],
    })
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['mode'] == 'openai-rag'
    assert data['sources']
    assert len(calls) == 1
    assert calls[0][2]['history'][0].role == 'user'


def test_explicit_openai_planner_still_validates_days(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'openai')
    monkeypatch.setenv('OPENAI_API_KEY', 'mock-openai-key')
    monkeypatch.setenv('GEMINI_API_KEY', 'gemini-should-not-be-used')
    called = []
    def fake(prompt, instructions, **kwargs):
        called.append(kwargs)
        return json.dumps({'action': 'plan', 'days': 99, 'history': True,
                           'beach': False, 'city_preferences': ['Cairo', 'Luxor'],
                           'replace_from': '', 'replace_to': '', 'extra_day_city': ''})
    monkeypatch.setattr(travel_agent, 'generate_openai', fake)
    result = client.post('/api/consult', json={
        'message': 'خطط لي 6 أيام: 4 أيام القاهرة ويومين الأقصر', 'language': 'Arabic'
    })
    assert result.status_code == 200, result.text
    trip = result.json()['trip_state']
    assert trip['days'] == 6
    assert [p['days'] for p in trip['phases']] == [6] or sum(p['days'] for p in trip['phases']) == 6
    assert result.json()['mode'] == 'openai-intent+local-planner'
    assert called[0]['json_mode'] is True


def test_explicit_openai_hotel_assistance_preserves_editorial_facts(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'openai')
    monkeypatch.setenv('OPENAI_API_KEY', 'mock-openai-key')
    monkeypatch.setattr(hotel_companion, 'generate', lambda *_a, **_kw: pytest.fail('Gemini was called'))
    monkeypatch.setattr(hotel_companion, 'generate_openai', lambda *_a, **_kw: json.dumps({
        'acknowledgement': 'أقدر أساعدك تختار إقامة مناسبة.',
        'follow_up': 'تحب تقيم في وسط القاهرة ولا الجيزة؟',
    }, ensure_ascii=False))
    editorial = {'mode': 'hotel-editorial', 'answer': 'فنادق موثقة، بدون أسعار مباشرة',
                 'sources': [{'url': 'https://example.org/hotel'}]}
    reply = hotel_companion.enhance_hotel_reply('رشح فندق', 'Arabic', [], editorial)
    assert reply['mode'] == 'hotel-openai-assisted'
    assert editorial['answer'] in reply['answer']
    assert editorial['sources'] == reply['sources']


def test_openai_selected_without_key_never_silently_switches_to_gemini(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'openai')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('GEMINI_API_KEY', 'mock-gemini-key')
    result = client.post('/api/chat', json={'message': 'Tell me about Karnak Temple'})
    assert result.status_code == 200
    assert result.json()['mode'] == 'offline-preview'
    assert client.get('/api/health').json()['guide_mode'] == 'offline-preview'
