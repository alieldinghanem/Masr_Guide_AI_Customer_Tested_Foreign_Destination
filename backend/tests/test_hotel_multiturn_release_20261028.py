"""Release regression tests: real API routing, not a Gemini live invocation."""
import pytest

from app.main import _chat_calls


def post(client, message, history=None):
    _chat_calls.clear()
    response = client.post('/api/consult', json={
        'message': message,
        'language': 'Arabic',
        'history': history or [],
    })
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize('question', [
    'هل Marriott Mena House متاح الليلة وبكام؟',
    'مينا هاوس سعر الليلة؟',
    'Is Marriott Mena House available tonight?',
])
def test_direct_named_property_routes_to_credible_hotel_sources(client, question):
    r = post(client, question)
    assert r['mode'] == 'hotel-editorial'
    assert [h['id'] for h in r['sources']] == ['hotel-mena-house']
    assert 'marriott.com/' in r['answer']
    assert '100 دولار' not in r['answer']
    assert r['itinerary'] is None


def test_named_hotel_stays_in_follow_up_without_recommending_unrelated_properties(client):
    first = 'مينا هاوس بكام الليلة؟'
    result = post(client, first)
    assert len(result['sources']) == 1
    history = [
        {'role': 'user', 'content': first},
        {'role': 'assistant', 'content': result['answer'][:1500]},
    ]
    second = post(client, 'طيب مناسب لعيلة؟', history)
    assert second['mode'] == 'hotel-editorial'
    assert [h['id'] for h in second['sources']] == ['hotel-mena-house']
    assert 'Steigenberger' not in second['answer']


def test_named_hotel_context_allows_explicit_new_area(client):
    history = [{'role': 'user', 'content': 'مينا هاوس بكام الليلة؟'}]
    second = post(client, 'طيب ورشح فندق في وسط البلد', history)
    assert {s['id'] for s in second['sources']} == {'hotel-steigenberger-tahrir', 'hotel-sofitel-gezirah'}


def test_no_fake_availability_or_payment_collection(client):
    first = post(client, 'هل مينا هاوس متاح النهارده؟')
    assert 'ما عنديش اتصال مباشر بأسعار الغرف أو توافرها' in first['answer']
    second = post(client, 'احجزه وخد رقم الكارت')
    assert second['mode'] == 'local-assistant'
    assert not second['sources']


def test_unsupported_hotel_city_does_not_recommend_cairo_properties(client):
    r = post(client, 'رشح فندق في الغردقة')
    assert r['mode'] == 'hotel-guide-limited'
    assert r['sources'] == []


def test_follow_up_does_not_request_budget_again(client):
    history = [{'role': 'user', 'content': 'رشح فندق في القاهرة'},
               {'role': 'assistant', 'content': 'أمثلة بإحالات لمواقع رسمية.'}]
    r = post(client, 'ميزانيتي 100 دولار في الليلة', history)
    assert r['mode'] == 'hotel-editorial'
    assert 'قولّي موعد الوصول والمغادرة وعدد المسافرين عشان نكمّل المقارنة.' in r['answer']
    assert 'ما أقدرش أؤكد إن الفندق مناسب ليها' in r['answer']
