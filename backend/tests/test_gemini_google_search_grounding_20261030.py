"""Offline contract tests: Google Search opt-in, provenance and security."""
import io
import json
import pytest
from fastapi import HTTPException
from app import gemini_client, guide
from app.main import _chat_calls
from app.schemas import ChatTurn


class FakeResponse:
    def __init__(self, response):
        self._body = json.dumps(response).encode()
    def __enter__(self): return io.BytesIO(self._body)
    def __exit__(self, *_): return False


def _stub(monkeypatch, response):
    requests = []
    def fake_urlopen(request, **kwargs):
        requests.append(request)
        return FakeResponse(response)
    monkeypatch.setattr(gemini_client, 'urlopen', fake_urlopen)
    monkeypatch.setenv('GEMINI_API_KEY', 'not-a-real-secret')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-2.5-flash')
    return requests


def _sample(metadata=None):
    return {'candidates':[{'content': {'parts':[{'text':'Visit the museum after checking official hours.'}]},
                           'groundingMetadata': metadata or {}}]}


def test_gemini_rest_payload_has_real_search_tool_and_roles(monkeypatch):
    calls = _stub(monkeypatch, _sample({
        'webSearchQueries':['Egyptian museum official visiting hours'],
        'groundingChunks':[{'web': {'uri':'https://egymonuments.gov.eg/', 'title':'Official museum source'}}],
        'searchEntryPoint':{'renderedContent':'<div>Google Search suggestion</div>'},
    }))
    history = [ChatTurn(role='user',content='Cairo museums'), ChatTurn(role='assistant',content='Which museum?')]
    result = gemini_client.generate_grounded('Tomorrow?', 'Use reliable sources.', history=history)
    payload = json.loads(calls[-1].data)
    assert payload['tools'] == [{'google_search':{}}]
    assert [c['role'] for c in payload['contents']] == ['user','model','user']
    assert 'not-a-real-secret' not in str(payload)
    assert result['grounding']['grounded'] is True
    assert result['grounding']['search_performed'] is True
    assert result['sources'][0]['url'] == 'https://egymonuments.gov.eg/'
    assert result['grounding']['search_suggestions_html'].startswith('<div>')


def test_search_not_claimed_without_grounding_metadata(monkeypatch):
    _stub(monkeypatch, _sample())
    response = gemini_client.generate_grounded('What is open today?', 'Be accurate')
    assert response['grounding']['requested'] is True
    assert response['grounding']['search_performed'] is False
    assert response['grounding']['grounded'] is False
    assert response['sources'] == []


def test_rejects_malicious_or_invalid_search_urls(monkeypatch):
    _stub(monkeypatch, _sample({'groundingChunks':[
        {'web': {'uri':'javascript:alert(1)','title':'XSS'}},
        {'web': {'uri':'http://example.com','title':'Insecure'}},
        {'web': {'uri':'https://trusted.example.com/page','title':'Valid'}},
        {'web': {'uri':'https://trusted.example.com/page','title':'Duplicate'}},
    ]}))
    assert [s['url'] for s in gemini_client.generate_grounded('Question','Instructions')['sources']] == ['https://trusted.example.com/page']


def test_missing_key_has_no_network_access(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setattr(gemini_client, 'urlopen', lambda *_a,**_kw:pytest.fail('Network request attempted'))
    with pytest.raises(ValueError):
        gemini_client.generate_grounded('Hello','Instruction')


def test_guide_grounding_mode_reports_real_sources(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER','gemini')
    monkeypatch.setenv('GEMINI_API_KEY','mock-key')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING','true')
    def fake_generate(prompt,instructions,**kwargs):
        assert kwargs['history'][0].role == 'user'
        return {'answer':'The official site lists visiting details.',
                'sources':[{'number':1,'title':'Official','url':'https://egymonuments.gov.eg/en', 'type':'google_search'}],
                'grounding':{'requested':True,'search_performed':True,'grounded':True,'queries':['Egypt official'], 'search_suggestions_html':''}}
    monkeypatch.setattr(guide,'generate_grounded',fake_generate)
    result=client.post('/api/chat',json={'message':'What are the landmarks to visit in Luxor?',
                                          'history':[{'role':'user','content':'I like history'}]})
    assert result.status_code == 200, result.text
    data=result.json()
    assert data['mode']=='gemini-search-grounded'
    assert any(src.get('type') == 'google_search' for src in data['sources'])
    assert client.get('/api/health').json()['gemini_search_configured'] is True


def test_without_web_sources_time_sensitive_answer_not_verified(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER','gemini')
    monkeypatch.setenv('GEMINI_API_KEY','mock-key')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING','true')
    monkeypatch.setattr(guide,'generate_grounded',lambda *_a,**_kw:{
        'answer':'This restaurant is open now at a confirmed price!', 'sources':[],
        'grounding':{'requested':True,'search_performed':False,'grounded':False, 'queries':[], 'search_suggestions_html':''}})
    result=client.post('/api/chat',json={'message':'Is Karnak Temple open today?'})
    assert result.status_code == 200
    data=result.json()
    assert data['mode'] == 'gemini-search-unverified'
    assert 'confirmed price' not in data['answer']


def test_restaurant_query_requires_real_search_citations(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER','gemini')
    monkeypatch.setenv('GEMINI_API_KEY','mock-key')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING','true')
    monkeypatch.setattr(guide,'generate_grounded',lambda *_a,**_kw:{
        'answer':'Invented famous restaurant with 5 stars', 'sources':[],
        'grounding':{'requested':True,'search_performed':False,'grounded':False, 'queries':[], 'search_suggestions_html':''}})
    result=client.post('/api/chat',json={'message':'رشحلي مطاعم في الزمالك'})
    assert result.status_code == 200
    assert result.json()['mode']=='restaurant-search-unverified'
    assert 'Invented' not in result.json()['answer']


def test_gpt_keeps_priority_even_when_search_enabled(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER','openai')
    monkeypatch.setenv('OPENAI_API_KEY','mock-key')
    monkeypatch.setenv('GEMINI_API_KEY','mock-key')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING','true')
    monkeypatch.setattr(guide,'generate_grounded',lambda *_a,**_kw:pytest.fail('Gemini was called'))
    monkeypatch.setattr(guide,'generate_openai',lambda *_a,**_kw:'A helpful Cairo answer')
    data=client.post('/api/chat',json={'message':'Tell me about the pyramids in Giza'}).json()
    assert data['mode']=='openai-rag'


def test_search_disabled_keeps_original_gemini_path(client, monkeypatch):
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER','gemini')
    monkeypatch.setenv('GEMINI_API_KEY','mock-key')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING','false')
    monkeypatch.setattr(guide,'generate_grounded',lambda *_a,**_kw:pytest.fail('Grounded call attempted'))
    monkeypatch.setattr(guide,'generate',lambda *_a,**_kw:'The pyramids are in Giza.')
    data=client.post('/api/chat',json={'message':'Tell me about the pyramids in Giza'}).json()
    assert data['mode']=='gemini-rag'


def test_502_does_not_expose_provider_key(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','my-secret-key')
    monkeypatch.setenv('GEMINI_MODEL','gemini-2.5-flash')
    from urllib.error import URLError
    monkeypatch.setattr(gemini_client,'urlopen',lambda *_a,**_kw: (_ for _ in ()).throw(URLError('my-secret-key')))
    with pytest.raises(HTTPException) as err:
        gemini_client.generate_grounded('question','instructions')
    assert err.value.status_code == 502
    assert 'my-secret-key' not in str(err.value.detail)
