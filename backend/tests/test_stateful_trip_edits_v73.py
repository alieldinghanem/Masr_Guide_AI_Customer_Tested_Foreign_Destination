"""New independent trip-edit regressions; the legacy 52 checks remain unmodified."""
import pytest
from app.main import _chat_calls

@pytest.fixture(autouse=True)
def offline_isolation(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', '')
    monkeypatch.setenv('CHAT_RATE_LIMIT_PER_MINUTE', '999')
    _chat_calls.clear()
    yield
    _chat_calls.clear()


def ask(client, text, state=None):
    body={'message':text}
    if state is not None: body['trip_state']=state
    response=client.post('/api/consult',json=body)
    assert response.status_code==200, response.text
    return response.json()


def start(client):
    return ask(client,'Plan 14 days: 7 days Cairo and Luxor, then 7 days Hurghada')['trip_state']


def assert_split(result, expected):
    state=result['trip_state']
    assert [p['days'] for p in state['phases']]==expected
    assert state['days']==sum(expected)
    assert len(result['itinerary']['days'])==state['days']


def test_replace_destination_is_successful_not_fake_failure(client):
    out=ask(client,'Replace Hurghada with Sharm El Sheikh',start(client))
    coast=out['trip_state']['phases'][1]['cities']
    assert coast==['Sharm El Sheikh']
    assert 'Hurghada' not in [c for p in out['trip_state']['phases'] for c in p['cities']]
    assert 'could not identify' not in out['answer'].lower()


def test_full_explicit_13_7_edit(client):
    out=ask(client,'خلي 13 يوم في القاهرة و7 أيام على البحر',start(client))
    assert_split(out,[13,7])


def test_partial_arabic_beach_edit_preserves_total(client):
    out=ask(client,'خلي 5 أيام على البحر',start(client))
    assert_split(out,[9,5])


def test_partial_english_beach_edit_preserves_total(client):
    out=ask(client,'Change the beach to 5 days',start(client))
    assert_split(out,[9,5])


def test_explicit_total_and_beach_together(client):
    out=ask(client,'Make the whole trip 20 days, with 7 days at the beach',start(client))
    assert_split(out,[13,7])


def test_total_after_phase_is_not_confused(client):
    out=ask(client,'7 days on beach, but change the whole trip to 20 days',start(client))
    assert_split(out,[13,7])


def test_family_update_in_a_followup(client):
    out=ask(client,'I am traveling with two kids',start(client))
    assert out['trip_state']['family'] is True
    assert_split(out,[7,7])


def test_incompatible_total_and_split_is_not_fabricated(client):
    original=start(client)
    out=ask(client,'Make the whole trip 14 days, 13 days in Cairo and 7 days on the beach',original)
    assert out['trip_state']==original
    assert out['itinerary'] is None
    assert 'could not identify' in out['answer'].lower()
