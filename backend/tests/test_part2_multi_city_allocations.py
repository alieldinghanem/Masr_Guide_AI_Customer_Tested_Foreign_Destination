"""Explicit named-city duration must override attraction-density heuristics."""
from collections import Counter
import pytest


@pytest.mark.parametrize('message, expected', [
    ('Plan 20 days: 10 days Cairo, 3 days Luxor, 7 days Hurghada',
     {'Cairo': 10, 'Luxor': 3, 'Hurghada': 7}),
    ('Plan 10 days in Cairo, 3 days in Luxor and 7 days in Hurghada',
     {'Cairo': 10, 'Luxor': 3, 'Hurghada': 7}),
    ('رحلة ٢٠ يوم: ١٠ أيام في القاهرة، ٣ أيام في الأقصر، ٧ أيام للغردقة',
     {'Cairo': 10, 'Luxor': 3, 'Hurghada': 7}),
])
def test_respects_per_city_duration_in_three_city_trips(client, message, expected):
    response = client.post('/api/consult', json={'message': message})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get('itinerary') is not None, payload['answer']
    assert payload['trip_state']['days'] == 20
    actual = Counter(day['city'] for day in payload['itinerary']['days'])
    assert dict(actual) == expected
    assert payload['itinerary']['day_allocation'] == expected


def test_refuses_conflicting_named_city_and_total_durations(client):
    response = client.post('/api/consult', json={
        'message': 'Plan 21 days: 10 days Cairo, 3 days Luxor, 7 days Hurghada'
    })
    assert response.status_code == 200, response.text
    assert response.json()['itinerary'] is None
    assert response.json()['mode'] == 'needs-clarification'


def test_reports_actual_allocation_even_when_one_phase_covers_two_cities(client):
    reply = client.post('/api/consult', json={
        'message': 'Plan 14 days: 7 days between Cairo and Luxor, 7 days in Hurghada'
    })
    assert reply.status_code == 200
    plan = reply.json()['itinerary']
    assert plan is not None
    assert plan['day_allocation'] == dict(Counter(day['city'] for day in plan['days']))
