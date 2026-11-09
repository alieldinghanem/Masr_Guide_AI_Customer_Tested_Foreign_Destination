"""Customer-discovered regression: never silently plan Cairo instead of foreign city."""
import pytest
from app.main import _chat_calls


@pytest.mark.parametrize('prompt', [
    'خططلي رحلة 5 أيام في روما',
    'Plan a 5 day trip to Rome',
    'Je veux un voyage de 5 jours à Paris',
    'خططلي 7 أيام بين القاهرة ودبي',
    'Plan 4 days in Istanbul',
    'عايز 3 أيام في لندن',
])
def test_customer_foreign_city_never_becomes_cairo(client, prompt):
    _chat_calls.clear()
    response = client.post('/api/consult', json={'message': prompt})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['mode'] == 'unsupported-destination'
    assert result['itinerary'] is None and result['trip_state'] is None


def test_known_egypt_city_keeps_working(client):
    _chat_calls.clear()
    result = client.post('/api/consult', json={'message': 'خططلي رحلة 5 أيام في القاهرة'})
    assert result.status_code == 200
    assert result.json()['itinerary']['day_allocation'] == {'Cairo': 5}
