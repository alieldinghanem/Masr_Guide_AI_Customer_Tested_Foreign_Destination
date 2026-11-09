from unittest.mock import patch


def test_two_week_historical_beach_route(client):
    res = client.post('/api/consult', json={
        'message': 'I am visiting Egypt for two weeks, first week history in Cairo and Luxor and second week by the sea in Hurghada',
        'language': 'English', 'history': []
    })
    assert res.status_code == 200, res.text
    p = res.json()
    assert p['mode'] == 'local-planner'
    assert p['trip_state']['days'] == 14
    assert [x['days'] for x in p['trip_state']['phases']] == [7, 7]
    assert len(p['itinerary']['days']) == 14
    assert p['itinerary']['days'][0]['city'] == 'Cairo'
    assert p['itinerary']['days'][-1]['city'] == 'Hurghada'
    assert len({stop['place']['id'] for day in p['itinerary']['days'] for stop in day['stops']}) == p['itinerary']['total_places']


def test_edit_replace_beach_destination(client):
    start = client.post('/api/consult', json={'message': 'Plan Egypt two weeks history and beach'}).json()
    edited = client.post('/api/consult', json={'message': 'Replace Hurghada with Sharm El Sheikh', 'trip_state': start['trip_state']}).json()
    assert edited['itinerary']
    assert edited['trip_state']['days'] == 14
    assert edited['trip_state']['phases'][-1]['cities'] == ['Sharm El Sheikh']
    assert edited['itinerary']['days'][-1]['city'] == 'Sharm El Sheikh'


def test_ambiguous_extra_luxor_day_preserves_original_trip(client):
    start = client.post('/api/consult', json={'message': 'I am visiting for 14 days: history in Cairo and Luxor, beach in Hurghada'}).json()
    edited = client.post('/api/consult', json={'message': 'Add one more day to Luxor', 'trip_state': start['trip_state']}).json()
    assert edited['mode'] == 'needs-clarification'
    assert edited['trip_state'] == start['trip_state']
    assert edited['itinerary'] is None
    assert 'unchanged' in edited['answer']


def test_arabic_two_weeks(client):
    r = client.post('/api/consult', json={'message':'انا نازل مصر اسبوعين اول اسبوع آثار والقاهرة والأقصر والاسبوع التاني بحر الغردقة', 'language':'Arabic'}).json()
    assert r['itinerary'] is not None
    assert r['trip_state']['days'] == 14
    assert len(r['itinerary']['days']) == 14


def test_missing_duration_asks_clarification(client):
    r = client.post('/api/consult', json={'message':'Plan a trip to Cairo and Hurghada'}).json()
    assert r['itinerary'] is None
    assert 'How many days' in r['answer']


def test_long_trip_is_supported(client):
    r = client.post('/api/consult', json={'message':'Plan 21 days in Egypt for history and beaches'}).json()
    assert r['itinerary'] is not None
    assert len(r['itinerary']['days']) == 21


def test_gemini_configured_health_does_not_claim_live(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'placeholder-not-live')
    r = client.get('/api/health').json()
    assert r['guide_mode'] == 'gemini-configured'


def test_gemini_planning_failure_falls_back_offline(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'placeholder')
    with patch('app.travel_agent._extract_gemini', side_effect=RuntimeError('not connected')):
        r = client.post('/api/consult', json={'message':'Plan 14 days history and beach'}).json()
    assert r['mode'] == 'local-planner'
    assert len(r['itinerary']['days']) == 14


def test_bad_trip_state_rejected(client):
    r = client.post('/api/consult', json={'message':'Replace Hurghada with Sharm', 'trip_state': {'days':100, 'phases': []}})
    assert r.status_code == 422


def test_general_question_uses_guide_without_trip(client):
    r = client.post('/api/consult', json={'message':'Tell me about the Great Pyramid'}).json()
    assert r['itinerary'] is None
    assert r['mode'] == 'offline-preview'
