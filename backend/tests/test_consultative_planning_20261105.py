"""The guide must act on the preferences it explicitly asks visitors for."""
from collections import Counter

from app.database import initialize
from app.schemas import ChatTurn, ConsultRequest
from app.travel_agent import consult_travel
from app import travel_dialogue


def _offline(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()


def _ask(message, state=None, language='Arabic'):
    return consult_travel(ConsultRequest(message=message, language=language, trip_state=state))


def _cities(reply):
    return Counter(day['city'] for day in reply['itinerary']['days'])


def test_duration_without_cities_proposes_routes_before_building(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    answer = _ask('هقعد ١٤ يوم مع عيلتي')
    assert answer['trip_state'] is None and answer['itinerary'] is None
    assert 'القاهرة والأقصر' in answer['answer']
    assert 'القاهرة والغردقة' in answer['answer']
    selected = consult_travel(ConsultRequest(
        message='الاختيار الثاني', language='Arabic', history=[
            ChatTurn(role='user', content='هقعد ١٤ يوم مع عيلتي'),
            ChatTurn(role='assistant', content=answer['answer']),
        ],
    ))
    assert selected['trip_state']['days'] == 14
    assert selected['trip_state']['family'] is True
    assert {'Cairo', 'Hurghada'} <= set(_cities(selected))
    open_ended = _ask('خطط رحلة ١٤ يوم لمصر')
    assert open_ended['trip_state'] is None and open_ended['itinerary'] is None
    assert 'القاهرة والأقصر' in open_ended['answer']


def test_museum_feedback_changes_suggestions_without_moving_days(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    first = _ask('رحلة ١٤ يوم مع عيلتي: ٥ أيام القاهرة، يومين الأقصر، و٧ أيام الغردقة')
    assert 'تفضّل المتاحف' in first['answer']
    second = _ask('أفضل المتاحف', first['trip_state'])
    assert second['trip_state']['days'] == first['trip_state']['days'] == 14
    assert second['trip_state']['family'] is True
    assert _cities(second) == _cities(first)
    assert all(phase['interests'] == ['museums'] for phase in second['trip_state']['phases']
               if phase['kind'] != 'beach')
    assert all(phase['interests'] == old['interests'] for phase, old in
               zip(second['trip_state']['phases'], first['trip_state']['phases']) if phase['kind'] == 'beach')
    assert first['itinerary']['days'][0]['stops'][0]['place']['category'] != 'Museum'
    assert second['itinerary']['days'][0]['stops'][0]['place']['category'] == 'Museum'
    assert 'عدّلت اقتراحات الأنشطة' in second['answer']
    assert 'وتيرة الرحلة كلها أهدى' in second['answer']

    third = _ask('خلّي وتيرة الرحلة كلها أهدى', second['trip_state'])
    assert third['trip_state']['pace'] == 'relaxed'
    assert _cities(third) == _cities(second)
    assert third['trip_state']['phases'] == second['trip_state']['phases']
    assert 'هل توزيع الأيام مناسب' in third['answer']

    accepted = _ask('تمام', third['trip_state'])
    assert accepted['trip_state'] == third['trip_state']
    assert accepted['itinerary'] is None
    assert 'زي ما هي' in accepted['answer']
    unhappy = _ask('مش عاجبني', third['trip_state'])
    assert unhappy['trip_state'] == third['trip_state'] and unhappy['itinerary'] is None
    assert 'المدن، توزيع الأيام، نوع الأنشطة' in unhappy['answer']


def test_english_market_feedback_updates_historic_phase_only(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    first = _ask('Plan a 14-day family trip to Egypt with Cairo, Luxor, and Hurghada.', language='English')
    assert 'museums and history or markets and local food' in first['answer']
    second = _ask('I prefer markets and local food', first['trip_state'], 'English')
    assert second['trip_state']['days'] == 14
    assert _cities(second) == _cities(first)
    assert all(phase['interests'] == ['food'] for phase in second['trip_state']['phases']
               if phase['kind'] != 'beach')
    assert 'preference for markets and local food' in second['answer']
    scoped = _ask('I prefer museums in Cairo', first['trip_state'], 'English')
    assert scoped['trip_state'] == first['trip_state'] and scoped['itinerary'] is None
    assert 'share one itinerary segment' in scoped['answer']


def test_beach_feedback_proposes_safe_next_step_without_moving_days(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    first = _ask('رحلة ٧ أيام: ٣ أيام القاهرة، يومين الأقصر، ويومين الغردقة')
    opinion = _ask('عايز بحر أكتر', first['trip_state'])
    assert opinion['trip_state'] == first['trip_state'] and opinion['itinerary'] is None
    assert 'تزود إجمالي الرحلة' in opinion['answer']
    explicit = _ask('زود إجمالي الرحلة يومين في الغردقة', first['trip_state'])
    assert explicit['trip_state']['days'] == 9
    assert _cities(explicit) == {'Cairo': 3, 'Luxor': 2, 'Hurghada': 4}


def test_model_cannot_append_a_second_unactionable_question(tmp_path, monkeypatch):
    _offline(tmp_path, monkeypatch)
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-key')
    monkeypatch.setattr(travel_dialogue, 'generate', lambda *_args, **_kwargs:
                        'This is a balanced family itinerary. Would you like an unverified excursion?')
    first = _ask('Plan a 14-day family trip to Egypt with Cairo, Luxor, and Hurghada.', language='English')
    assert 'unverified excursion?' not in first['answer']
    assert first['answer'].count('?') == 1
    assert 'museums and history or markets and local food?' in first['answer']
