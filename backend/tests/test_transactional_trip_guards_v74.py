"""Safety regressions: state mutations must be explicit, atomic and structurally valid.

These are additional tests; the historical 52-check test source is unchanged.
"""
import copy
from unittest.mock import patch

import pytest

from app.main import _chat_calls


@pytest.fixture(autouse=True)
def force_offline(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', '')
    monkeypatch.setenv('CHAT_RATE_LIMIT_PER_MINUTE', '999')
    _chat_calls.clear()
    yield
    _chat_calls.clear()


def query(client, text, trip_state=None):
    request = {'message': text}
    if trip_state is not None:
        request['trip_state'] = trip_state
    response = client.post('/api/consult', json=request)
    assert response.status_code == 200, response.text
    return response.json()


def initial(client):
    state = query(client, 'Plan 14 days: 7 days Cairo and Luxor, then 7 days Hurghada')['trip_state']
    assert state['days'] == 14
    return state


def trip_cities(state):
    return [c for p in state['phases'] for c in p['cities']]


def test_budget_change_with_other_cities_does_not_swap_destinations(client):
    state = initial(client)
    result = query(client, 'Change my budget to 5000 EGP; I might travel from Cairo to Aswan.', state)
    assert result['trip_state']['budget_egp'] == 5000
    assert [p['cities'] for p in result['trip_state']['phases']] == [p['cities'] for p in state['phases']]
    assert 'Aswan' not in trip_cities(result['trip_state'])


def test_ai_generated_replacement_not_authorized_by_user_text(client, monkeypatch):
    state = initial(client)
    monkeypatch.setenv('GEMINI_API_KEY', 'not-a-real-secret')
    suggestion = {'action': 'edit', 'replace_from': 'Hurghada', 'replace_to': 'Sharm El Sheikh'}
    with patch('app.travel_agent._extract_gemini', return_value=suggestion):
        result = query(client, 'My budget is 9000 EGP', state)
    assert result['trip_state']['budget_egp'] == 9000
    assert 'Hurghada' in trip_cities(result['trip_state'])
    assert 'Sharm El Sheikh' not in trip_cities(result['trip_state'])


def test_cross_category_destination_replacement_rolls_back_entire_request(client):
    state = initial(client)
    result = query(client, 'Replace Hurghada with Cairo and budget 5000 EGP', state)
    assert result['trip_state'] == state
    assert result['itinerary'] is None
    assert 'Cairo' not in result['trip_state']['phases'][-1]['cities']


def test_ambiguous_thousands_cannot_partially_change_trip(client):
    state = initial(client)
    result = query(client, 'Budget 15000 ألف جنيه and change my trip to 20 days', state)
    assert result['trip_state'] == state
    assert result['mode'] == 'needs-clarification'
    assert result['itinerary'] is None


def test_unsupported_remove_with_budget_is_not_partially_applied(client):
    state = initial(client)
    result = query(client, 'Remove Luxor and set budget to 6000 EGP', state)
    assert result['mode'] == 'needs-clarification'
    assert result['trip_state'] == state


def test_incomplete_destination_swap_never_guesses_city(client):
    state = initial(client)
    result = query(client, 'Replace Hurghada with another city and set my budget 5000 EGP', state)
    assert result['mode'] == 'needs-clarification'
    assert result['trip_state'] == state


def test_valid_city_replacement_still_works(client):
    state = initial(client)
    result = query(client, 'Replace Hurghada with Sharm El Sheikh', state)
    assert 'Hurghada' not in trip_cities(result['trip_state'])
    assert 'Sharm El Sheikh' in trip_cities(result['trip_state'])
    assert result['itinerary'] is not None


def test_valid_city_addition_still_works(client):
    state = initial(client)
    result = query(client, 'I want to add Aswan', state)
    assert 'Aswan' in trip_cities(result['trip_state'])
    assert result['itinerary'] is not None


@pytest.mark.parametrize('tampering', [
    lambda state: state['phases'][0].update(days=8),
    lambda state: state['phases'][0].update(cities=['Cairo', 'Luxor', 'Aswan', 'Giza', 'Fayoum', 'Alexandria']),
    lambda state: state['phases'][1].update(cities=['Hurghada', 'Hurghada']),
    lambda state: state.update(booking_confirmed=True),
])
def test_invalid_client_trip_state_is_rejected_before_processing(client, tampering):
    state = copy.deepcopy(initial(client))
    tampering(state)
    response = client.post('/api/consult', json={'message': 'Tell me about Karnak', 'trip_state': state})
    assert response.status_code == 422, response.text


def test_valid_partial_day_edit_preserves_total_and_phase_constraints(client):
    state = initial(client)
    result = query(client, 'Change the beach to 5 days', state)
    assert result['trip_state']['days'] == 14
    assert [p['days'] for p in result['trip_state']['phases']] == [9, 5]
    assert len(result['itinerary']['days']) == 14


def test_incompatible_explicit_split_is_rejected_without_changes(client):
    state = initial(client)
    result = query(client, 'Make the whole trip 14 days, 13 days Cairo and 7 days beach', state)
    assert result['trip_state'] == state
    assert result['itinerary'] is None


def test_internal_bug_cannot_silently_alter_unrequested_duration(client):
    state = initial(client)
    corrupt = copy.deepcopy(state)
    corrupt['days'] = 20
    corrupt['phases'][0]['days'] = 13
    with patch('app.travel_agent._apply_edit', return_value=corrupt):
        out = query(client, 'My budget is 9000 EGP', state)
    assert out['trip_state'] == state
    assert out['itinerary'] is None


def test_internal_bug_cannot_silently_shuffle_phase_days(client):
    state = initial(client)
    corrupt = copy.deepcopy(state)
    corrupt['phases'][0]['days'] = 9
    corrupt['phases'][1]['days'] = 5
    with patch('app.travel_agent._apply_edit', return_value=corrupt):
        out = query(client, 'My budget is 9000 EGP', state)
    assert out['trip_state'] == state
    assert out['itinerary'] is None


def test_arabic_explicit_coastal_replacement(client):
    state = initial(client)
    result = query(client, 'بدل الغردقة بشرم الشيخ', state)
    assert result['trip_state']['phases'][1]['cities'] == ['Sharm El Sheikh']
    assert result['itinerary'] is not None
