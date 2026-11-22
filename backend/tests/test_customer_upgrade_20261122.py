import pytest

from app.guide import answer_chat, _requested_recommendation_count
from app.schemas import ChatRequest, ChatTurn, ConsultRequest
from app.travel_agent import consult_travel


@pytest.mark.parametrize('query,count', [
    ('Recommend two historical places in Cairo', 2),
    ('Suggest 1 museum in Cairo', 1),
    ('رشحلي مكانين في القاهرة', 2),
    ('اقترح ٣ متاحف في القاهرة', 3),
    ('Recommande deux musées au Caire', 2),
    ('Plan a two day trip to Cairo', None),
])
def test_recommendation_count_is_not_trip_duration(query, count):
    assert _requested_recommendation_count(query) == count


@pytest.mark.parametrize('provider', ['offline', 'gemini'])
def test_explicit_count_is_sourced_and_truthfully_local(monkeypatch, provider):
    monkeypatch.setenv('AI_PROVIDER', provider)
    monkeypatch.setenv('GEMINI_API_KEY', 'configured-but-no-call-expected')
    result = answer_chat(ChatRequest(message='Recommend two historical places in Cairo', language='English'))
    assert result['mode'] == 'local-assistant'
    assert len(result['sources']) == 2
    assert all(source['city'] == 'Cairo' and source['url'].startswith('https://') for source in result['sources'])
    assert '[1]' in result['answer'] and '[2]' in result['answer']
    assert '[3]' not in result['answer']


def test_followup_keeps_second_attraction_and_adds_visit_advice(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    initial = answer_chat(ChatRequest(message='Recommend two historical places in Cairo', language='English'))
    follow = answer_chat(ChatRequest(message='Tell me more about the second one', language='English', history=[
        ChatTurn(role='user', content='Recommend two historical places in Cairo'),
        ChatTurn(role='assistant', content=initial['answer']),
    ]))
    assert [s['id'] for s in follow['sources']] == [initial['sources'][1]['id']]
    assert 'Suggested visit time' in follow['answer']


def test_inland_plan_does_not_claim_beach_days(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    result = consult_travel(ConsultRequest(message='Plan 5 days in Cairo and Alexandria with two children', language='English'))
    assert result['itinerary']['route'] == ['Cairo', 'Alexandria']
    assert 'beach days' not in result['itinerary']['disclaimer']
    assert 'approximate' in result['itinerary']['disclaimer']
