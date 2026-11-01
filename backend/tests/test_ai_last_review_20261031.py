"""Regression tests for provider completeness and user-facing trust guarantees."""
import sys
import types
import pytest
from fastapi import HTTPException
from app.openai_client import generate


class _FakeClient:
    response = None
    def __init__(self, **kw):
        self.responses = self
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def create(self, **kwargs): return self.response


@pytest.mark.parametrize('status,details,should_fail', [
    ('incomplete', types.SimpleNamespace(reason='max_output_tokens'), True),
    ('failed', None, True),
    ('completed', None, False),
    (None, None, False),
])
def test_openai_never_presents_incomplete_message_as_finished(monkeypatch, status, details, should_fail):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    monkeypatch.setitem(sys.modules, 'openai', types.SimpleNamespace(OpenAI=_FakeClient))
    _FakeClient.response = types.SimpleNamespace(status=status, incomplete_details=details, output_text='Here is half an itinerary: day one...')
    if should_fail:
        with pytest.raises(HTTPException) as exc:
            generate('Plan a trip', 'Only return reliable completed results.')
        assert exc.value.status_code == 502
    else:
        assert generate('Plan a trip', 'Only return reliable completed results.').startswith('Here is half')

@pytest.mark.parametrize('utterance', [
    'انقل يومين من القاهرة للغردقة',
    'Move 2 days from Cairo to Hurghada',
])
def test_existing_city_day_transfer_is_exact_and_persists_context(client, monkeypatch, utterance):
    from app.main import _chat_calls
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    start = client.post('/api/consult', json={'message': 'خطط 30 يوم: 10 أيام القاهرة و5 أيام الأقصر و7 أيام أسوان و8 أيام الغردقة', 'language': 'Arabic'}).json()
    state = start['trip_state']
    assert [p['days'] for p in state['phases']] == [10,5,7,8]
    r = client.post('/api/consult', json={'message': utterance, 'language': 'Arabic', 'trip_state': state})
    assert r.status_code == 200, r.text
    changed = r.json()['trip_state']
    assert [p['days'] for p in changed['phases']] == [8,5,7,10]
    assert changed['days'] == 30
    assert len(r.json()['itinerary']['days']) == 30
    assert r.json()['itinerary']['day_allocation']['Cairo'] == 8
    assert r.json()['itinerary']['day_allocation']['Hurghada'] == 10


def test_day_transfer_rejects_overdraw_without_mutation(client, monkeypatch):
    from app.main import _chat_calls
    _chat_calls.clear()
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    init = client.post('/api/consult', json={'message': 'خطط 7 أيام: 4 أيام القاهرة و3 أيام الغردقة', 'language': 'Arabic'}).json()
    r = client.post('/api/consult', json={'message': 'انقل 4 أيام من القاهرة للغردقة', 'trip_state': init['trip_state'], 'language': 'Arabic'})
    assert r.status_code == 200
    assert r.json()['trip_state'] == init['trip_state']
    assert r.json()['itinerary'] is None
