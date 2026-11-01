"""Business-critical chat acceptance: honest outages, source provenance, language.

Provider failures are simulated, not live API tests.  Each test exercises the
same HTTP route a traveler uses rather than a private function alone.
"""
import pytest
from fastapi import HTTPException
from app import guide
from app.main import _chat_calls


@pytest.mark.parametrize('language,query,needle', [
    ('Arabic', 'احكيلي عن معبد الكرنك في الأقصر', 'غير متاحة مؤقتًا'),
    ('English', 'Tell me about Karnak Temple in Luxor', 'temporarily unavailable'),
    ('French', 'Parlez-moi du temple de Karnak à Louxor', 'temporairement indisponibles'),
])
def test_gemini_grounding_outage_degrades_without_misleading_user(client, monkeypatch, language, query, needle):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-not-real')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING', 'true')
    monkeypatch.setattr(guide, 'generate_grounded', lambda *a, **k: (_ for _ in ()).throw(HTTPException(502, 'sensitive secret info')))
    response = client.post('/api/chat', json={'message': query, 'language': language})
    assert response.status_code == 200
    data = response.json()
    assert data['mode'] == 'offline-fallback'
    assert needle in data['answer']
    assert 'sensitive secret info' not in response.text
    assert 'gemini-search-grounded' not in response.text
    assert not any(s.get('type') == 'google_search' for s in data['sources'])


def test_grounded_restaurant_outage_does_not_fabricate_properties(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-not-real')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING', 'true')
    monkeypatch.setattr(guide, 'generate_grounded', lambda *a, **k: (_ for _ in ()).throw(HTTPException(502, 'upstream')))
    response = client.post('/api/chat', json={'message':'رشحلي مطاعم نباتية مفتوحة النهارده في الزمالك', 'language': 'Arabic'})
    assert response.status_code == 200
    assert response.json()['mode'] == 'offline-fallback'
    assert response.json()['sources'] == []
    assert 'غير متاحة مؤقتًا' in response.json()['answer']


def test_plain_gemini_failure_has_honest_fallback(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-not-real')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING', 'false')
    monkeypatch.setattr(guide, 'generate', lambda *a, **k: (_ for _ in ()).throw(HTTPException(502, 'provider error')))
    data = client.post('/api/chat', json={'message': 'Tell me about Aswan history'}).json()
    assert data['mode'] == 'offline-fallback'
    assert 'not live prices or hours' in data['answer']


def test_non_provider_errors_not_swallowed(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-not-real')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING', 'true')
    monkeypatch.setattr(guide, 'generate_grounded', lambda *a, **k: (_ for _ in ()).throw(HTTPException(429, 'quota')))
    response = client.post('/api/chat', json={'message': 'Tell me about Luxor temples'})
    assert response.status_code == 429


def test_google_grounding_instructions_allow_sourced_fresh_information(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-not-real')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING', 'true')
    captured = {}
    def mock(prompt, instructions, **kwargs):
        captured['instructions'] = instructions
        return {'answer': 'Source-backed visitor guidance.',
                'sources': [{'number': 1, 'url':'https://egymonuments.gov.eg/en', 'title':'Official', 'type':'google_search'}],
                'grounding': {'requested':True,'search_performed':True,'grounded':True,'queries':['official'], 'search_suggestions_html':''}}
    monkeypatch.setattr(guide, 'generate_grounded', mock)
    data = client.post('/api/chat', json={'message':'What can I see in Luxor today?'}).json()
    assert data['mode'] == 'gemini-search-grounded'
    assert 'provider-retrieved web evidence' in captured['instructions']
    assert data['sources'][-1]['type'] == 'google_search'


def test_auto_openai_path_uses_shared_adapter_instead_of_legacy(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'auto')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setenv('OPENAI_API_KEY', 'mock-key')
    called = []
    def mock(prompt, instructions, **kwargs):
        called.append((prompt, kwargs))
        return 'Karnak is a temple complex in Luxor.'
    monkeypatch.setattr(guide, 'generate_openai', mock)
    data = client.post('/api/chat', json={'message':'Tell me about Karnak Temple'}).json()
    assert data['mode'] == 'llm-rag'
    assert called[0][1]['max_tokens'] == 1050
    assert called[0][1]['history'] == []


def test_dynamic_price_without_citations_does_not_disclose_model_guess(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'mock-key')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING', 'true')
    monkeypatch.setattr(guide, 'generate_grounded', lambda *a, **k: {
        'answer': 'The museum is open now and costs $42.', 'sources': [],
        'grounding': {'requested':True,'search_performed':False,'grounded':False,'queries':[], 'search_suggestions_html':''}
    })
    data = client.post('/api/chat', json={'message': 'What is the price today for the Luxor Museum?'}).json()
    assert data['mode'] == 'gemini-search-unverified'
    assert '$42' not in data['answer']
