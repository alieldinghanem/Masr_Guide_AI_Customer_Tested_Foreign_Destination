"""Customer acceptance: a one-week or undated month-long trip is an editable,
truthful travel draft, never a live-price or booked itinerary.
"""
import pytest
from app.main import _chat_calls


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', '')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    _chat_calls.clear()
    yield
    _chat_calls.clear()


def ask(client, message, state=None):
    payload = {'message': message}
    if state is not None:
        payload['trip_state'] = state
    response = client.post('/api/consult', json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def assert_valid_coverage(result, duration):
    assert result['trip_state']['days'] == duration
    assert len(result['itinerary']['days']) == duration
    assert sum(p['days'] for p in result['trip_state']['phases']) == duration
    assert sum(result['itinerary']['day_allocation'].values()) == duration
    attraction_ids = [stop['place']['id'] for day in result['itinerary']['days'] for stop in day['stops']]
    assert len(attraction_ids) == len(set(attraction_ids)), 'curated attractions must not repeat'
    for day in result['itinerary']['days']:
        if not day['stops']:
            assert day['note'] or day['travel']


def test_arabic_week_family(client):
    result = ask(client, 'أنا جاي مصر أسبوع مع زوجتي وطفلين وعايز القاهرة والأقصر والغردقة')
    assert_valid_coverage(result, 7)
    assert result['trip_state']['family'] is True
    assert {'Cairo','Luxor','Hurghada'} <= {d['city'] for d in result['itinerary']['days']}
    assert 'لا توجد حجوزات أو أسعار مؤكدة' in result['answer']


def test_arabic_undated_month_four_cities(client):
    result = ask(client, 'أنا جاي مصر شهر مع أسرتي وعايز القاهرة والأقصر وأسوان والغردقة')
    assert_valid_coverage(result, 30)
    assert {'Cairo','Luxor','Aswan','Hurghada'} <= {d['city'] for d in result['itinerary']['days']}
    assert 'اعتبرت «شهر» 30 يومًا' in result['answer']


def test_english_undated_month(client):
    result = ask(client, 'Plan a one month trip in Egypt with children: Cairo, Luxor, Aswan and Hurghada')
    assert_valid_coverage(result, 30)
    assert 'assumed a month means 30 days' in result['answer']


def test_calendar_reference_not_forced_to_30(client):
    from app.travel_agent import total_days
    assert total_days('I want to visit Egypt next month') is None
    assert total_days('Visiting Cairo in November') is None


def test_long_month_trip_exact_reallocation(client):
    initial = ask(client, 'خطط رحلة 30 يوم: 10 أيام القاهرة و5 أيام الأقصر و5 أيام أسوان و10 أيام الغردقة')
    assert_valid_coverage(initial, 30)
    changed = ask(client, 'غير التوزيع: 8 أيام القاهرة و5 أيام الأقصر و7 أيام أسوان و10 أيام الغردقة', initial['trip_state'])
    assert_valid_coverage(changed, 30)
    assert [p['days'] for p in changed['trip_state']['phases']] == [8,5,7,10]
    assert [p['cities'][0] for p in changed['trip_state']['phases']] == ['Cairo','Luxor','Aswan','Hurghada']


def test_months_above_thirty_are_rejected(client):
    result = ask(client, 'Plan a 2 months trip across Egypt')
    assert result['itinerary'] is None
    assert '30 days' in result['answer']
