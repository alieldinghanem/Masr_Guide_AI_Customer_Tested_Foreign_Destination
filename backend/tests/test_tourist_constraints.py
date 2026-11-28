import pytest
from app.schemas import ConsultRequest, TripState
from app.travel_agent import consult_travel


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')


def ask(message, state=None):
    return consult_travel(ConsultRequest(message=message, trip_state=state, language='English'))


def test_real_visitor_compound_arrival_pyramids_and_swimming():
    result = ask('I am visiting Egypt for 7 days with my children aged 4 and 9. '
                 'We arrive in Cairo at 8 pm. We want the pyramids, a museum and two relaxed swimming days. '
                 'Please suggest a practical plan with few transfers.')
    assert result['itinerary'], result['answer']
    days = result['itinerary']['days']
    assert len(days) == 7
    assert not days[0]['stops']
    assert 'giza-pyramids' in {s['place']['id'] for d in days for s in d['stops']}
    assert sum(d.get('swimming_day', False) for d in days) == 2
    assert all(not d.get('travel') for d in days if d.get('swimming_day'))
    assert result['trip_state']['traveler_profile']['children_ages'] == [4, 9]


@pytest.mark.parametrize('message,day_number', [
    ('Day 1 must be arrival and rest only. Please fix it.', 1),
    ('خلي اليوم الأول وصول وراحة فقط بدون زيارات', 1),
    ('خلي اليوم التاني راحة فقط بدون زيارات', 2),
    ('خلي تالت يوم راحة فقط بدون زيارات', 3),
    ('خلي اليوم الرابع راحة فقط بدون زيارات', 4),
])
def test_rest_edit_persists_without_moving_other_days(message, day_number):
    start = ask('Plan 5 days in Cairo for history with children')
    language = 'Arabic' if message.startswith('خلي') else 'English'
    edited = consult_travel(ConsultRequest(message=message, trip_state=start['trip_state'], language=language))
    assert edited['itinerary'], edited['answer']
    assert edited['trip_state']['day_overrides'][day_number]['max_stops'] == 0
    assert not edited['itinerary']['days'][day_number - 1]['stops']
    def other_visits(response):
        return [(d['city'], [s['place']['id'] for s in d['stops']])
                for d in response['itinerary']['days'] if d['day'] != day_number]
    assert other_visits(edited) == other_visits(start)
    restored = ask(f'Explain day {day_number}', edited['trip_state'])
    assert restored['answer'].startswith(f'Day {day_number} in Cairo:')
    assert restored['sources'] == []


def test_ambiguous_arabic_ordinal_and_overlong_day_number_do_not_change_the_trip():
    start = ask('Plan 5 days in Cairo for history with children')
    for message in ('خلي يوم تاني راحة فقط بدون زيارات', 'خلي اليوم 200 راحة فقط بدون زيارات'):
        result = ask(message, start['trip_state'])
        assert result['mode'] == 'needs-clarification'
        assert result['trip_state'] == start['trip_state']


def test_compound_correction_asks_before_reallocating_cities():
    start = ask('Plan 7 days in Cairo')
    correction = ask('You missed the pyramids and the two swimming days. Also, I arrive at 8 pm, '
                     'so Day 1 must be arrival and rest only. Please fix those points.', start['trip_state'])
    assert correction['mode'] == 'needs-clarification'
    assert correction['trip_state'] == start['trip_state']
    assert correction['itinerary'] is None
    assert 'swim' in correction['answer'].lower() or 'beach' in correction['answer'].lower()


def test_negated_pyramids_and_swimming_are_not_added():
    result = ask('Plan 4 days in Cairo. No pyramids and no swimming, just museums.')
    assert all(d['city'] == 'Cairo' for d in result['itinerary']['days'])
    assert not any(d.get('swimming_day') for d in result['itinerary']['days'])


def test_zero_stop_override_is_valid_but_negative_is_not():
    start = ask('Plan 3 days in Cairo')['trip_state']
    start['day_overrides'] = {1: {'max_stops': 0, 'family_friendly': False}}
    TripState.model_validate(start)
    start['day_overrides'][1]['max_stops'] = -1
    with pytest.raises(ValueError):
        TripState.model_validate(start)


def test_young_child_rest_is_budgeted_not_added_after_scheduling():
    from app.planner import build_plan
    from app.schemas import PlanRequest
    plan = build_plan(PlanRequest(cities=['Cairo'], days=2, family=True, pace='relaxed', traveler_profile={'children_ages':[4]}))
    assert all(d['estimated_activity_minutes'] + d['rest_minutes'] + d['estimated_travel_minutes'] <= 240 for d in plan['days'])


def test_arrival_time_needs_an_actual_clock_and_handles_terminal_numbers():
    from app.trip_constraints import late_arrival
    assert late_arrival('We arrive at terminal 3 at 8 pm')
    assert not late_arrival('I arrive at 8')
    assert not late_arrival('I do not arrive at 8 pm')
    assert not late_arrival('I arrive at 8:99 pm')


def test_save_contract_rejects_rest_day_with_visits():
    from app.accounts import _check_phase_allocation
    from fastapi import HTTPException
    start = ask('Plan 3 days in Cairo')
    state = TripState.model_validate({**start['trip_state'], 'day_overrides':{1:{'max_stops':0,'family_friendly':False}}})
    with pytest.raises(HTTPException) as exc:
        _check_phase_allocation(state, start['itinerary'])
    assert exc.value.status_code == 422


def test_cairo_only_request_is_clarified_before_adding_giza():
    result = ask('Plan 4 days in Cairo only, including the pyramids')
    assert result['mode'] == 'needs-clarification'
    assert result['itinerary'] is None and 'Giza' in result['answer']


def test_hotel_pool_is_not_misread_as_coastal_swimming_days():
    from app.trip_constraints import swimming_days
    assert swimming_days('two relaxed swimming days at the hotel pool') == 0


def test_day_override_rejects_booleans_as_stop_counts():
    from app.schemas import DayOverride
    with pytest.raises(ValueError):
        DayOverride(max_stops=False)
