"""Planning preferences supplied before duration survive the next chat turn."""

from app.database import initialize
from app.schemas import ChatTurn, ConsultRequest
from app.travel_agent import consult_travel


def _offline(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'guide.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    initialize()


def test_arabic_preferences_before_duration_become_a_family_trip(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    request = 'عايز آثار وبحر مع الأطفال، بس الرحلة تكون مريحة'
    first = consult_travel(ConsultRequest(message=request, language='Arabic'))
    assert first['trip_state'] is None
    assert first['mode'] == 'needs-clarification'
    assert 'القاهرة' in first['answer'] and 'الغردقة' in first['answer']
    assert 'كام يوم' in first['answer']

    second = consult_travel(ConsultRequest(
        message='7 أيام', language='Arabic',
        history=[ChatTurn(role='user', content=request),
                 ChatTurn(role='assistant', content=first['answer'])],
    ))
    assert second['trip_state'] is not None, second
    assert second['trip_state']['days'] == 7
    assert second['trip_state']['family'] is True
    assert second['trip_state']['pace'] == 'relaxed'
    assert {phase['kind'] for phase in second['trip_state']['phases']} == {'history', 'beach'}
    assert {city for phase in second['trip_state']['phases'] for city in phase['cities']} == {
        'Cairo', 'Hurghada'}


def test_english_preferences_before_duration_are_retained(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    request = 'We want history and beaches with our kids, at an easy pace'
    first = consult_travel(ConsultRequest(message=request, language='English'))
    assert first['mode'] == 'needs-clarification'
    assert 'Cairo' in first['answer'] and 'Hurghada' in first['answer']
    second = consult_travel(ConsultRequest(
        message='Seven days', language='English',
        history=[ChatTurn(role='user', content=request),
                 ChatTurn(role='assistant', content=first['answer'])],
    ))
    assert second['trip_state']['days'] == 7
    assert second['trip_state']['family'] is True
    assert second['trip_state']['pace'] == 'relaxed'
    assert {phase['kind'] for phase in second['trip_state']['phases']} == {'history', 'beach'}


def test_french_preferences_wait_for_duration_and_keep_context(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    request = 'Je voudrais histoire et mer avec mes enfants, rythme plus lent'
    first = consult_travel(ConsultRequest(message=request, language='French'))
    assert first['mode'] == 'needs-clarification'
    assert 'Combien de jours' in first['answer']
    second = consult_travel(ConsultRequest(
        message='sept jours', language='French',
        history=[ChatTurn(role='user', content=request),
                 ChatTurn(role='assistant', content=first['answer'])],
    ))
    assert second['trip_state']['days'] == 7
    assert second['trip_state']['family'] is True
    assert second['trip_state']['pace'] == 'relaxed'
    assert {phase['kind'] for phase in second['trip_state']['phases']} == {'history', 'beach'}
