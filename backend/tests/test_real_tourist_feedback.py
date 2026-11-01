"""Regression coverage based on an actual tourist's failed 20-day planning conversation."""
from app.travel_agent import _budget_egp


def test_arabic_twenty_days_in_cairo_and_sea(client):
    response = client.post('/api/consult', json={
        'message': 'أنا نازل مصر رحلة 20 يوم، عايز أسبوع على البحر والباقي في القاهرة بميزانية 15000 جنيه',
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data['itinerary']['days']) == 20
    assert [p['days'] for p in data['trip_state']['phases']] == [13, 7]
    assert data['trip_state']['phases'][0]['cities'] == ['Cairo']
    assert data['trip_state']['phases'][1]['cities'] == ['Hurghada']
    assert data['trip_state']['budget_egp'] == 15000
    assert 'هل الميزانية تشمل الإقامة' in data['answer']
    assert 'يوم' in data['answer']


def test_ambiguous_budget_does_not_invent_spend(client):
    response = client.post('/api/consult', json={'message': 'رحلة 20 يوم، أسبوع بحر وباقي القاهرة، ميزانية 15000 ألف جنيه'})
    assert response.status_code == 200
    data = response.json()
    assert len(data['itinerary']['days']) == 20
    assert data['trip_state']['budget_egp'] is None
    assert 'توضيح مهم' in data['answer']


def test_arabic_guide_reply_follows_user_not_default(client):
    result = client.post('/api/consult', json={'message': 'أريد زيارة الأهرامات في الجيزة'}).json()
    assert result['itinerary'] is None
    assert any(c in result['answer'] for c in ('الهرم', 'الأهرامات', 'معاينة', 'معلومات'))


def test_english_twenty_days_historical_and_beach(client):
    result = client.post('/api/consult', json={'message': 'Plan 20 days in Egypt: a week on the beach, rest in Cairo'}).json()
    assert [p['days'] for p in result['trip_state']['phases']] == [13, 7]
    assert result['trip_state']['days'] == 20


def test_longer_than_thirty_days_rejected(client):
    response = client.post('/api/consult', json={'message': 'Plan 31 days history and beaches'}).json()
    assert response['itinerary'] is None
    assert '30 days' in response['answer']


def test_stored_budget_survives_edit(client):
    first = client.post('/api/consult', json={'message': '20 days Cairo and Hurghada beach with 15000 EGP'}).json()
    edited = client.post('/api/consult', json={'message': 'Replace Hurghada with Sharm El Sheikh', 'trip_state': first['trip_state']}).json()
    assert edited['trip_state']['budget_egp'] == 15000
    assert edited['trip_state']['phases'][-1]['cities'] == ['Sharm El Sheikh']


def test_budgets_no_confident_cost_claims():
    assert _budget_egp('15 ألف جنيه') == (15000, False)
    assert _budget_egp('15000 ألف جنيه') == (None, True)
