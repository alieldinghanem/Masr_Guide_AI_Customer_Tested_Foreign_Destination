"""Regression tests for long-stay itinerary integrity and legitimate stop coverage.

These use the real application API without requiring any LLM credentials.
They deliberately check unique catalogue IDs and honest limitations; they do
not equate 'one attraction day' with a fully feasible real travel itinerary.
"""
import pytest
from app.main import _chat_calls
from app.catalog import PLACES

@pytest.fixture(autouse=True)
def isolate_rate_limit(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', '')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    _chat_calls.clear()
    yield
    _chat_calls.clear()


def consult(client, message):
    response = client.post('/api/consult', json={'message':message})
    assert response.status_code == 200, response.text
    return response.json()


def assert_genuine_coverage(result, minimum=0.60):
    itinerary = result['itinerary']
    assert itinerary is not None
    days = itinerary['days']
    assert len(days) == result['trip_state']['days']
    covered = [d for d in days if d['stops']]
    assert len(covered) / len(days) >= minimum, (len(covered),len(days))
    ids = [s['place']['id'] for d in days for s in d['stops']]
    assert len(ids) == len(set(ids)), 'No duplicate curated attractions'
    catalog = {p['id']:p for p in PLACES}
    assert all(slug in catalog for slug in ids)
    for day in days:
        assert all(stop['place']['city'] == day['city'] for stop in day['stops'])
        if not day['stops']:
            assert day.get('note') or day.get('travel'), 'Empty stops must be honest'


def test_14_day_history_and_beach_preserves_phase_lengths(client):
    result = consult(client, 'Plan a 14 day trip: first 7 days in Cairo and Luxor for history, second 7 days on Red Sea beaches in Hurghada')
    assert [p['days'] for p in result['trip_state']['phases']] == [7,7]
    assert [day['city'] for day in result['itinerary']['days']][7:] == ['Hurghada']*7
    assert_genuine_coverage(result)


def test_20_day_cairo_beach_respects_requested_cities(client):
    result = consult(client, 'عايز رحلة 20 يوم 13 يوم في القاهرة و7 أيام على البحر')
    assert [p['days'] for p in result['trip_state']['phases']] == [13,7]
    assert [d['city'] for d in result['itinerary']['days']] == ['Cairo']*13+['Hurghada']*7
    assert_genuine_coverage(result)


def test_30_day_unspecified_country_is_explicit_suggestion(client):
    result = consult(client, 'Plan a 30 day trip in Egypt')
    state = result['trip_state']
    assert state['days'] == 30
    assert len(state['phases'][0]['cities']) >= 4
    assert 'provisional' in result['answer'].lower()
    assert_genuine_coverage(result)


def test_30_day_explicit_cairo_is_not_overridden(client):
    result = consult(client, 'Plan 30 days in Cairo')
    assert result['trip_state']['phases'][0]['cities'] == ['Cairo']
    assert all(d['city']=='Cairo' for d in result['itinerary']['days'])
    assert 'provisional' not in result['answer'].lower()


def test_replacing_hurghada_updates_state_instead_of_reporting_failure(client):
    start = consult(client, 'Plan 14 days: 7 days Cairo and Luxor, then 7 days Hurghada')
    response = client.post('/api/consult', json={
        'message':'Replace Hurghada with Sharm El Sheikh',
        'trip_state':start['trip_state'],
    })
    assert response.status_code==200
    result=response.json()
    cities=[city for p in result['trip_state']['phases'] for city in p['cities']]
    assert 'Sharm El Sheikh' in cities and 'Hurghada' not in cities
    assert 'could not identify' not in result['answer'].lower()


def test_expanded_catalog_records_have_credible_source_and_bilingual_text(client):
    ids = {p['id']:p for p in client.get('/api/places').json()['places']}
    assert len(ids)>=50
    for slug in ('museum-of-islamic-art','gayer-anderson-museum','sultan-hassan-mosque','manial-palace-museum'):
        p=ids[slug]
        assert p['source_url'].startswith('https://')
        assert p['name_ar'] and p['summary_ar']
        assert p['city']=='Cairo'
