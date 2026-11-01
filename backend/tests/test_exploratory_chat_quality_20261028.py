"""Regression from actual multi-turn exploratory chat QA (not mocked model responses)."""
import pytest
from app.main import _chat_calls

@pytest.fixture(autouse=True)
def reset_limits():
    _chat_calls.clear()
    yield
    _chat_calls.clear()

def ask(client, message, **kwargs):
    r = client.post('/api/consult', json={'message': message, **kwargs})
    assert r.status_code == 200, r.text
    return r.json()

@pytest.mark.parametrize('text', ['أهلاً', 'أهلًا', 'اهلا', 'أهلا', 'مرحبًا', 'السلام عليكم'])
def test_visitor_greetings_with_hamza_or_tashkeel(client, text):
    response = ask(client, text)
    assert response['mode'] == 'local-assistant'
    assert not response['sources']

@pytest.mark.parametrize('message', ['أحسن مطاعم في الزمالك؟', 'Suggest restaurants in Zamalek', 'مطاعم في القاهرة'])
def test_unverified_restaurant_query_does_not_mislabel_places(client, message):
    response = ask(client, message)
    assert response['mode'] == 'restaurant-guide-limited'
    assert not response['sources']
    assert 'Hurghada Marina' not in response['answer']
    assert 'خليج نعمة' not in response['answer']

def test_unsupported_city_day_edit_never_reallocates_another_city(client):
    first = ask(client, 'خطط رحلة 20 يوم، 13 يوم القاهرة و7 أيام الغردقة')
    assert first['itinerary']['day_allocation'] == {'Cairo': 13, 'Hurghada': 7}
    second = ask(client, 'بدل الغردقة بشرم الشيخ', trip_state=first['trip_state'])
    assert second['itinerary']['day_allocation'] == {'Cairo': 13, 'Sharm El Sheikh': 7}
    third = ask(client, 'زود 3 أيام في الغردقة وخلي المجموع 20', trip_state=second['trip_state'])
    assert third['mode'] == 'needs-clarification'
    assert third['trip_state'] == second['trip_state']
    assert third['itinerary'] is None

def test_tomorrow_hours_do_not_return_generic_exhibit_facts(client):
    response = ask(client, 'هل المتحف المصري الكبير مفتوح بكرة؟')
    assert response['mode'] == 'local-assistant'
    assert not response['sources']
    assert 'موقع' in response['answer'] or 'تأكد' in response['answer']

def test_city_allocation_survives_a_valid_update(client):
    initial = ask(client, 'خطط رحلة 20 يوم، 13 يوم القاهرة و7 أيام الغردقة')
    changed = ask(client, 'بدل الغردقة بشرم الشيخ', trip_state=initial['trip_state'])
    assert changed['itinerary']['day_allocation'] == {'Cairo': 13, 'Sharm El Sheikh': 7}



def test_hotel_area_switch_to_unsupported_city_keeps_hotel_intent(client):
    history = [{'role': 'user', 'content': 'رشح لي فندق في القاهرة'}]
    r = ask(client, 'طيب لو في الأقصر؟', history=history)
    assert r['mode'] == 'hotel-guide-limited'
    assert not r['sources']


def test_switch_from_unsupported_city_back_to_cairo_is_not_poisoned(client):
    history = [{'role': 'user', 'content': 'رشح فندق في الغردقة'}]
    r = ask(client, 'طيب في القاهرة؟', history=history)
    assert r['mode'] == 'hotel-editorial'
    assert len(r['sources']) == 4
