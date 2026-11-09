"""Product-grade conversational hotel tests: never invent inventory or prices."""
import pytest

@pytest.fixture(autouse=True)
def local_only(monkeypatch):
    from app.main import _chat_calls
    _chat_calls.clear()
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)


def ask(client, message, history=None, language='Arabic'):
    r = client.post('/api/consult', json={'message': message, 'history': history or [], 'language': language})
    assert r.status_code == 200, r.text
    return r.json()


def test_hotels_real_sites_and_relevant_choices(client):
    resp = ask(client, 'رشح لي فندق في القاهرة')
    assert resp['mode'] == 'hotel-editorial'
    assert len(resp['sources']) == 4
    assert all(x['url'].startswith('https://') for x in resp['sources'])
    assert 'حجز مؤكدة' in resp['answer']


def test_pyramids_family_followup_keeps_context_without_price_claim(client):
    prior = [{'role':'user','content':'عايز فندق قريب من الأهرامات ومناسب لعيلة'}]
    resp = ask(client,'الميزانية 100 دولار في الليلة، عندك خيارات؟', prior)
    assert len(resp['sources']) == 2
    assert all('pyramids' in x['url'] or 'mena-house' in x['url'] for x in resp['sources'])
    assert 'ما أقدرش أؤكد' in resp['answer']


def test_specific_hotel_live_availability_must_not_fabricate(client):
    resp = ask(client,'هل فندق Marriott Mena House متاح الليلة وبكام؟')
    assert resp['mode'] == 'hotel-editorial'
    assert len(resp['sources']) == 1
    assert resp['sources'][0]['id'] == 'hotel-mena-house'
    assert 'ما عنديش اتصال مباشر' in resp['answer']


def test_unseeded_city_does_not_return_cairo_hotels(client):
    resp = ask(client,'رشح فندق في الأقصر')
    assert resp['mode'] == 'hotel-guide-limited'
    assert not resp['sources']


def test_hotel_booking_refuses_payment(client):
    resp = ask(client,'ممكن تحجز لي الفندق وتاخد بيانات الكارت؟')
    assert resp['mode'] == 'local-assistant'
    assert 'CVV' in resp['answer']


def test_no_verified_restaurants_refrains_from_hallucinating(client):
    resp = ask(client, 'رشح مطاعم قريبة من الفندق')
    assert resp['mode'] == 'hotel-guide-limited'
    assert resp['sources'] == []


def test_english_hotels(client):
    resp = ask(client,'Recommend a hotel in Cairo',language='English')
    assert resp['mode'] == 'hotel-editorial'
    assert 'live' in resp['answer'].lower()


def test_same_session_cairo_to_hurghada_day_transfer(client):
    initial = ask(client,'عايز أخطط رحلة 5 أيام في القاهرة')
    assert initial['trip_state']['days'] == 5
    changed = client.post('/api/consult', json={'message':'ضيف يومين في الغردقة بدل يومين من القاهرة',
                                                 'language':'Arabic', 'trip_state':initial['trip_state']})
    assert changed.status_code == 200, changed.text
    data = changed.json()
    assert data['itinerary'] is not None, data
    assert data['trip_state']['days'] == 5
    assert [(p['cities'],p['days']) for p in data['trip_state']['phases']] == [(['Cairo'],3),(['Hurghada'],2)]
    assert data['itinerary']['day_allocation'] == {'Cairo':3,'Hurghada':2}


def test_day_transfer_does_not_silently_alter_total_or_allow_invalid_city(client):
    state=ask(client,'عايز أخطط رحلة 5 أيام في القاهرة')['trip_state']
    for text in ('ضيف 2 يوم في الغردقة بدل 3 يوم من القاهرة',
                 'ضيف 8 يوم في الغردقة بدل 8 يوم من القاهرة',
                 'ضيف يومين في الأقصر بدل يومين من الإسكندرية'):
        r=client.post('/api/consult',json={'message':text,'language':'Arabic','trip_state':state})
        assert r.status_code == 200
        assert r.json()['trip_state']==state
        assert r.json()['itinerary'] is None
