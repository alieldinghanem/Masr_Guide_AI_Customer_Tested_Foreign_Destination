"""Additional AI release review: provider completion and safe fallback."""
import io
import json

import pytest
from fastapi import HTTPException

from app import gemini_client, guide


class StubReply:
    def __init__(self, data):
        self.data = json.dumps(data).encode('utf-8')

    def __enter__(self):
        return io.BytesIO(self.data)

    def __exit__(self, *_args):
        return False


@pytest.mark.parametrize('finish_reason', ['MAX_TOKENS', 'SAFETY', 'RECITATION', 'OTHER'])
@pytest.mark.parametrize('grounded', [False, True])
def test_partial_or_blocked_gemini_response_is_never_a_completed_answer(monkeypatch, finish_reason, grounded):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-test-key')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-2.5-flash')
    provider_reply = {'candidates': [{
        'finishReason': finish_reason,
        'content': {'parts': [{'text': 'This is a partial sentence that must not be shown'}]},
        'groundingMetadata': {'webSearchQueries': ['Luxor museum'],
                              'groundingChunks': [{'web': {'uri': 'https://egymonuments.gov.eg/en',
                                                           'title': 'Official'}}]}
    }]}
    monkeypatch.setattr(gemini_client, 'urlopen', lambda *_args, **_kwargs: StubReply(provider_reply))
    with pytest.raises(HTTPException) as error:
        if grounded:
            gemini_client.generate_grounded('Question', 'Instructions')
        else:
            gemini_client.generate('Question', 'Instructions')
    assert error.value.status_code == 502
    assert 'partial sentence' not in error.value.detail


@pytest.mark.parametrize('grounded', [False, True])
def test_complete_gemini_response_is_accepted(monkeypatch, grounded):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-test-key')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-2.5-flash')
    provider_reply = {'candidates': [{
        'finishReason': 'STOP',
        'content': {'parts': [{'text': 'Please verify the venue opening hours.'}]},
        'groundingMetadata': {'webSearchQueries': ['official venue hours'],
                              'groundingChunks': [{'web': {'uri': 'https://egymonuments.gov.eg/en',
                                                           'title': 'Official'}}]}
    }]}
    monkeypatch.setattr(gemini_client, 'urlopen', lambda *_args, **_kwargs: StubReply(provider_reply))
    result = (gemini_client.generate_grounded('Question', 'Instructions') if grounded
              else gemini_client.generate('Question', 'Instructions'))
    text = result['answer'] if grounded else result
    assert text == 'Please verify the venue opening hours.'


def test_user_chat_gets_explicit_offline_fallback_on_truncation(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-test-key')
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_SEARCH_GROUNDING', 'true')
    def partial(*args, **kwargs):
        raise HTTPException(502, 'Gemini is unavailable')
    monkeypatch.setattr(guide, 'generate_grounded', partial)
    result = client.post('/api/chat', json={'message': 'Tell me about the Valley of the Kings'})
    assert result.status_code == 200
    assert result.json()['mode'] == 'offline-fallback'
    assert 'live search' in result.json()['answer'].lower()
