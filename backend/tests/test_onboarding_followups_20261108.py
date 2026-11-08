"""Visitor answers to the assistant's planning questions must become a plan."""

from app.database import initialize
from app.schemas import ChatTurn, ConsultRequest
from app.travel_agent import consult_travel, total_days


def _offline(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'guide.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    initialize()


def test_bare_week_answer_builds_relaxed_family_history_and_beach_trip(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    first = consult_travel(ConsultRequest(message='انا جاي مصر قريب', language='Arabic'))
    assert first['mode'] == 'needs-clarification'
    followup = consult_travel(ConsultRequest(
        message='أسبوع مع مراتي وطفلين، عايزين آثار وبحر ومش عايزين يومنا يبقى مرهق',
        language='Arabic',
        history=[ChatTurn(role='user', content='انا جاي مصر قريب'),
                 ChatTurn(role='assistant', content=first['answer'])],
    ))
    assert followup['trip_state'] is not None, followup
    assert followup['trip_state']['days'] == 7
    assert followup['trip_state']['family'] is True
    assert followup['trip_state']['pace'] == 'relaxed'
    assert {phase['kind'] for phase in followup['trip_state']['phases']} == {'history', 'beach'}
    assert {city for phase in followup['trip_state']['phases'] for city in phase['cities']} == {
        'Cairo', 'Hurghada'}
    assert len(followup['itinerary']['days']) == 7
    assert 'تحب وتيرة الرحلة كلها أهدى' not in followup['answer']


def test_duration_answer_keeps_cities_from_previous_turn(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    first = consult_travel(ConsultRequest(message='عايز رحلة القاهرة والغردقة مع الأطفال', language='Arabic'))
    assert first['trip_state'] is None
    followup = consult_travel(ConsultRequest(
        message='أسبوع', language='Arabic',
        history=[ChatTurn(role='user', content='عايز رحلة القاهرة والغردقة مع الأطفال'),
                 ChatTurn(role='assistant', content=first['answer'])],
    ))
    assert followup['trip_state']['days'] == 7
    assert followup['trip_state']['family'] is True
    assert {city for phase in followup['trip_state']['phases'] for city in phase['cities']} == {
        'Cairo', 'Hurghada'}


def test_english_family_followup_respects_easy_pace(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    first = consult_travel(ConsultRequest(message="I'm coming to Egypt soon", language='English'))
    followup = consult_travel(ConsultRequest(
        message='One week with my wife and two kids. We want history and beach, not too hectic.',
        language='English',
        history=[ChatTurn(role='user', content="I'm coming to Egypt soon"),
                 ChatTurn(role='assistant', content=first['answer'])],
    ))
    assert followup['trip_state']['days'] == 7
    assert followup['trip_state']['family'] is True
    assert followup['trip_state']['pace'] == 'relaxed'
    assert {phase['kind'] for phase in followup['trip_state']['phases']} == {'history', 'beach'}
    assert {city for phase in followup['trip_state']['phases'] for city in phase['cities']} == {
        'Cairo', 'Hurghada'}
    assert 'Here is a draft itinerary' in followup['answer']


def test_bare_week_does_not_confuse_a_named_week_in_longer_trip():
    assert total_days('أسبوع مع الأسرة') == 7
    assert total_days('الأسبوع الأول بحر من رحلة 14 يوم') == 14
