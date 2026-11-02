"""Direct regression tests for the customer-reported chatbot failures."""
from collections import Counter

from app.database import initialize
from app.conversation_router import special_reply
from app.schemas import ChatTurn, ConsultRequest
from app.travel_agent import consult_travel


def _allocation(reply):
    return dict(Counter(day['city'] for day in reply['itinerary']['days']))


def test_explicit_arabic_total_extension_preserves_every_other_city(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    original = consult_travel(ConsultRequest(
        message='رحلة ٧ أيام: ٣ أيام في القاهرة، ويومين الأقصر، ويومين الغردقة',
        language='Arabic',
    ))
    reply = consult_travel(ConsultRequest(
        message='زوّد إجمالي مدة الرحلة يوم واحد، من غير ما نقلل باقي المدن',
        language='Arabic', trip_state=original['trip_state'],
        history=[
            ChatTurn(role='user', content='زود يوم للقاهرة'),
            ChatTurn(role='assistant', content='هل تريد زيادة الإجمالي أم نقل يوم من مدينة أخرى؟'),
        ],
    ))
    assert reply['mode'] == 'local-planner'
    assert reply['trip_state']['days'] == 8
    assert _allocation(reply) == {'Cairo': 4, 'Luxor': 2, 'Hurghada': 2}


def test_hyphenated_english_family_trip_keeps_context_on_replacement(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    first = consult_travel(ConsultRequest(
        message='Plan a 14-day family trip to Egypt with Cairo, Luxor, and Hurghada.',
        language='English',
    ))
    assert first['trip_state']['days'] == 14
    assert first['trip_state']['family'] is True
    assert {'Cairo', 'Luxor', 'Hurghada'} <= set(_allocation(first))

    second = consult_travel(ConsultRequest(
        message='Replace Hurghada with Sharm El Sheikh and keep the same duration.',
        language='English', trip_state=first['trip_state'],
        history=[
            ChatTurn(role='user', content='Plan a 14-day family trip to Egypt with Cairo, Luxor, and Hurghada.'),
            ChatTurn(role='assistant', content=first['answer'][:1500]),
        ],
    ))
    assert second['trip_state']['days'] == 14
    assert second['trip_state']['family'] is True
    assert _allocation(second) == {'Cairo': 6, 'Luxor': 1, 'Sharm El Sheikh': 7}


def test_total_extension_without_a_city_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    original = consult_travel(ConsultRequest(
        message='رحلة ٧ أيام: ٣ أيام في القاهرة، ويومين الأقصر، ويومين الغردقة',
        language='Arabic',
    ))
    reply = consult_travel(ConsultRequest(
        message='زوّد إجمالي مدة الرحلة يوم واحد، من غير ما نقلل باقي المدن',
        language='Arabic', trip_state=original['trip_state'],
    ))
    assert reply['mode'] == 'needs-clarification'
    assert reply['trip_state'] == original['trip_state']
    assert reply['itinerary'] is None


def test_ambiguous_city_increase_never_steals_a_day(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    original = consult_travel(ConsultRequest(
        message='رحلة ٧ أيام: ٣ أيام في القاهرة، ويومين الأقصر، ويومين الغردقة',
        language='Arabic',
    ))
    reply = consult_travel(ConsultRequest(
        message='زود يوم للقاهرة', language='Arabic',
        trip_state=original['trip_state'],
    ))
    assert reply['mode'] == 'needs-clarification'
    assert reply['trip_state'] == original['trip_state']
    assert reply['itinerary'] is None


def test_offline_upcoming_trip_statement_gets_a_conversational_followup():
    reply = special_reply('انا جاي مصر قريب', 'Arabic', [
        ChatTurn(role='user', content='هلا'),
        ChatTurn(role='assistant', content='أهلًا بيك، تحب نبدأ بإيه؟'),
    ])
    assert reply['mode'] == 'local-assistant'
    assert 'كام يوم' in reply['answer']
    assert 'الآثار' in reply['answer']
    assert 'لا توجد معلومات كافية' not in reply['answer']
