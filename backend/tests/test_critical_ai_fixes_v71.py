"""Independent regression tests for the first verified v7.1 QA remediation.

Tests exercise real HTTP endpoints without a provider key. No live weather, legal,
financial, medical or booking availability is claimed by the app.
"""
import pytest
from app.main import _chat_calls


@pytest.fixture(autouse=True)
def clear_rate_limit():
    _chat_calls.clear()
    yield
    _chat_calls.clear()


def consult(client, msg, state=None, history=None):
    payload = {'message': msg}
    if state is not None:
        payload['trip_state'] = state
    if history is not None:
        payload['history'] = history
    r = client.post('/api/consult', json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_unsupported_destination_never_substituted(client):
    r = consult(client, 'Plan 3 days in Marsa Matrouh')
    assert r['trip_state'] is None and r['itinerary'] is None
    assert 'Marsa Matrouh' in r['answer'] and 'not' in r['answer']


@pytest.mark.parametrize('msg, expected', [
    ('I have chest pain while touring the pyramids, what should I do?', 'emergency'),
    ('السواق بيهددني في مصر، أعمل إيه؟', 'الشرطة'),
    ('هل الجو مناسب للغوص النهاردة في الغردقة؟', 'طقس'),
    ('Can I send you my credit card number to book?', 'Do not share'),
])
def test_critical_safety_and_privacy(client, msg, expected):
    r = consult(client, msg)
    assert r['itinerary'] is None
    assert r['mode'] == 'local-assistant'
    assert expected.lower() in r['answer'].lower()


def test_a_medical_warning_not_misread_as_trip_request(client):
    r = consult(client, 'I have chest pain during my trip to Luxor')
    assert r['itinerary'] is None and 'medical' in r['answer']


def test_city_as_beach_without_explicit_beach_keyword(client):
    r = consult(client, 'Plan a 14 day trip: 7 days Cairo and Luxor, then 7 days Hurghada')
    assert [phase['days'] for phase in r['trip_state']['phases']] == [7, 7]
    assert r['trip_state']['phases'][-1]['cities'] == ['Hurghada']


def test_first_week_is_seven_days(client):
    r = consult(client, 'Plan 10 days first week at the beach and rest for ancient history in Cairo')
    assert [p['days'] for p in r['trip_state']['phases']] == [7, 3]
    assert r['trip_state']['phases'][0]['kind'] == 'beach'


def test_family_preference_is_saved(client):
    r = consult(client, 'عايز رحلة 5 أيام في القاهرة مع طفلين')
    assert r['trip_state']['family'] is True


def test_duration_and_budget_edits_preserve_intent(client):
    first = consult(client, 'Plan 14 days: Cairo and Luxor history, Hurghada beach')
    extended = consult(client, 'Change to 20 days', first['trip_state'])
    assert extended['trip_state']['days'] == 20
    assert len(extended['itinerary']['days']) == 20
    assert sum(p['days'] for p in extended['trip_state']['phases']) == 20
    added = consult(client, 'ميزانيتي 15000 جنيه', extended['trip_state'])
    assert added['trip_state']['days'] == 20
    assert added['trip_state']['budget_egp'] == 15000
    new_city = consult(client, 'I want to add Aswan', added['trip_state'])
    assert any('Aswan' in p['cities'] for p in new_city['trip_state']['phases'])
    assert new_city['trip_state']['budget_egp'] == 15000


def test_egyptian_visa_and_booking_no_false_confirmation(client):
    r = consult(client, 'Do I need a visa to visit Egypt as a British citizen?')
    assert 'visa2egypt.gov.eg' in r['answer']
    r = consult(client, 'Book a hotel in Luxor tomorrow for 2 people')
    assert 'no booking' in r['answer'].lower()


def test_french_language_and_transport_context(client):
    assert 'français' in consult(client, 'Parlez en français')['answer']
    r = consult(client, 'Comment aller du Caire à Louxor?')
    assert 'Pour aller' in r['answer']
    r = consult(client, 'طيب بكام؟', history=[{'role':'user','content':'إزاي أروح من القاهرة للغردقة؟'}])
    assert 'سعر' in r['answer']


def test_one_day_trip_and_overlimit_days(client):
    r = consult(client, 'Plan one day in Cairo')
    assert r['trip_state']['days'] == 1
    r = consult(client, 'Plan 300 days in Egypt')
    assert r['itinerary'] is None and '30 days' in r['answer']
