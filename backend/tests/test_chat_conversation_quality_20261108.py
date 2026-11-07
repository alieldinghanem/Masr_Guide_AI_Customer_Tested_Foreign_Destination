"""A tourist's short replies and questions must work against the open trip."""
from collections import Counter
from io import BytesIO
from urllib.error import HTTPError

import pytest
from fastapi import HTTPException

from app import gemini_client, guide, travel_agent, travel_dialogue
from app.database import initialize
from app.schemas import ConsultRequest
from app.travel_agent import consult_travel


def _ask(message, state=None, language='Arabic'):
    return consult_travel(ConsultRequest(message=message, language=language, trip_state=state))


def test_short_answer_to_own_question_changes_stops_without_moving_days(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'guide.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    initialize()
    first = _ask('رحلة ٧ أيام: ٣ أيام القاهرة ويومين الأقصر ويومين الغردقة')
    assert 'الأسواق والأكل المحلي؟' in first['answer']
    second = _ask('الأسواق والأكل المحلي', first['trip_state'])
    assert second['trip_state']['days'] == 7
    assert Counter(d['city'] for d in second['itinerary']['days']) == Counter(
        d['city'] for d in first['itinerary']['days'])
    assert all(p['interests'] == ['food'] for p in second['trip_state']['phases'] if p['kind'] != 'beach')
    assert 'الأسواق والأكل المحلي' in second['answer']


def test_asking_about_a_day_uses_current_itinerary_and_keeps_state(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'guide.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    initialize()
    first = _ask('رحلة ٧ أيام: ٣ أيام القاهرة ويومين الأقصر ويومين الغردقة')
    day = first['itinerary']['days'][0]
    detail = _ask('وريني تفاصيل اليوم الأول', first['trip_state'])
    assert detail['trip_state'] == first['trip_state']
    assert detail['itinerary'] is None
    assert 'اليوم 1 في القاهرة' in detail['answer']
    assert day['stops'][0]['place']['name_ar'] in detail['answer']
    assert len(detail['sources']) == len(day['stops'])
    assert all(source['id'] in {s['place']['id'] for s in day['stops']}
               for source in detail['sources'])
    invalid = _ask('تفاصيل اليوم ٨', first['trip_state'])
    assert invalid['trip_state'] == first['trip_state']
    assert invalid['itinerary'] is None
    assert 'مفيش يوم 8' in invalid['answer']


def test_english_day_followup_and_bare_answer(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'guide.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    initialize()
    first = _ask('Plan a 7-day trip: 3 days in Cairo, 2 days in Luxor, 2 days in Hurghada.',
                 language='English')
    detail = _ask('What about day one?', first['trip_state'], 'English')
    assert 'Day 1 in Cairo' in detail['answer']
    assert detail['trip_state'] == first['trip_state']
    chosen = _ask('markets and local food', first['trip_state'], 'English')
    assert all(p['interests'] == ['food'] for p in chosen['trip_state']['phases'] if p['kind'] != 'beach')


def test_gemini_503_cools_down_instead_of_delaying_every_visitor(monkeypatch):
    model = 'gemini-test-503'
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-key')
    monkeypatch.setenv('GEMINI_MODEL', model)
    calls = []

    def provider(_request, **_kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise HTTPError('https://generativelanguage.googleapis.com', 503,
                            'Service unavailable', None, None)
        return BytesIO(b'{"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":"Welcome to Egypt"}]}}]}')

    monkeypatch.setattr(gemini_client, 'urlopen', provider)
    try:
        with pytest.raises(HTTPException):
            gemini_client.generate('Hello', 'Be helpful')
        with pytest.raises(HTTPException):
            gemini_client.generate('Hello again', 'Be helpful')
        assert len(calls) == 1
        gemini_client._unavailable_until[model] = 0
        assert gemini_client.generate('Hello again', 'Be helpful') == 'Welcome to Egypt'
        assert len(calls) == 2
    finally:
        gemini_client._unavailable_until.pop(model, None)


def test_clear_trip_and_short_preference_use_one_model_reply_each(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'guide.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-key')
    monkeypatch.setenv('AI_TRIP_NARRATION_ENABLED', 'true')
    initialize()
    monkeypatch.setattr(travel_agent, '_extract_gemini',
                        lambda *_a, **_kw: pytest.fail('Unnecessary intent request'))
    replies = []

    def narrate(*_args, **_kwargs):
        replies.append(1)
        return 'A draft that follows the visitor preferences.'

    monkeypatch.setattr(travel_dialogue, 'generate', narrate)
    first = _ask('رحلة ٧ أيام: ٣ أيام القاهرة ويومين الأقصر ويومين الغردقة')
    second = _ask('الأسواق والأكل المحلي', first['trip_state'])
    assert second['trip_state']['days'] == 7
    assert len(replies) == 2


def test_broad_history_question_gets_concrete_cairo_places_even_offline(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'guide.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    initialize()
    question = 'أنا بحب التاريخ، تنصحني أبدأ بإيه في القاهرة وليه؟'
    reply = _ask(question)
    assert reply['mode'] == 'local-assistant'
    assert 'قلعة صلاح الدين' in reply['answer']
    assert 'المتحف المصري' in reply['answer']
    assert reply['sources'][0]['id'] == 'citadel'


def test_model_deferral_cannot_replace_a_grounded_recommendation(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'guide.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-key')
    initialize()
    monkeypatch.setattr(guide, 'generate', lambda *_a, **_kw:
                        'I do not have enough information. Ask about a specific place.')
    reply = _ask('I love history. Where should I start in Cairo and why?', language='English')
    assert reply['mode'] == 'local-assistant'
    assert 'Citadel of Saladin' in reply['answer']
    assert len(reply['sources']) == 3
