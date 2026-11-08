"""Regression: the rolling Gemini alias must not inherit pinned-model settings."""
import json
from unittest.mock import patch
import pytest
from app.gemini_client import generate


@pytest.mark.parametrize('model,has_thinking', [
    ('gemini-flash-latest', False),
    ('gemini-2.5-flash', True),
    ('gemini-2.5-flash-lite', True),
    ('gemini-3.1-flash-lite', False),
    ('gemini-3-flash-preview', False),
])
def test_model_specific_generation_settings(monkeypatch, model, has_thinking):
    monkeypatch.setenv('GEMINI_API_KEY', 'only-a-mock-do-not-publish')
    monkeypatch.setenv('GEMINI_MODEL', model)
    seen = []
    class Reply:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, *args):
            return json.dumps({'candidates':[{'content':{'parts':[{'text':'OK'}]}}]}).encode()
    def mock_open(req, timeout):
        body = json.loads(req.data)
        seen.append(body['generationConfig'])
        assert req.full_url.endswith(f'models/{model}:generateContent')
        assert req.headers['X-goog-api-key'] == 'only-a-mock-do-not-publish'
        return Reply()
    with patch('app.gemini_client.urlopen', mock_open):
        assert generate('Hello', 'Instruction') == 'OK'
    assert ('thinkingConfig' in seen[0]) == has_thinking
