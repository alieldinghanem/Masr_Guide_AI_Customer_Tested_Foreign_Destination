"""Real visitor QA for Egyptian-colloquial, context-sensitive trip edits."""
from collections import Counter
import pytest
from app.main import _chat_calls

@pytest.fixture(autouse=True)
def qa_rate_limit_isolation(monkeypatch):
    monkeypatch.setenv('CHAT_RATE_LIMIT_PER_MINUTE', '999')
    _chat_calls.clear()
    yield
    _chat_calls.clear()



def ask(client, message, state=None):
    payload = {'message': message, 'language': 'Arabic'}
    if state is not None:
        payload['trip_state'] = state
    result = client.post('/api/consult', json=payload)
    assert result.status_code == 200, result.text
    return result.json()


def allocations(response):
    plan = response['itinerary']
    assert plan is not None, response['answer']
    return dict(Counter(day['city'] for day in plan['days']))


def test_arabic_hala_responds_to_greeting_without_catalog_error(client):
    reply = ask(client, 'هلا')
    assert reply['itinerary'] is None
    assert 'أهل' in reply['answer']
    assert 'لا توجد معلومات كافية' not in reply['answer']


def test_family_7_day_split_and_currency_are_preserved(client):
    first = ask(client, 'أهلا، عايز أزور مصر أنا ومراتي وطفلين لمدة ٧ أيام، ومهتم بالآثار والبحر. اقترح رحلة مناسبة.')
    assert first['trip_state']['days'] == 7
    assert first['trip_state']['family'] is True

    second = ask(client, 'خلّي ٣ أيام في القاهرة، ويومين الأقصر، ويومين الغردقة. الميزانية ٣٠٠٠ دولار.', first['trip_state'])
    assert second['trip_state']['days'] == 7, second['answer']
    assert allocations(second) == {'Cairo': 3, 'Luxor': 2, 'Hurghada': 2}
    assert second['trip_state']['budget_usd'] == 3000
    assert second['trip_state']['family'] is True


def test_diacritized_swap_preserves_other_city_days_and_budget(client):
    original = ask(client, 'رحلة ٧ أيام: ٣ أيام في القاهرة، ويومين الأقصر، ويومين الغردقة بميزانية ٣٠٠٠ دولار')
    assert allocations(original) == {'Cairo': 3, 'Luxor': 2, 'Hurghada': 2}
    edit = ask(client, 'بدّل الغردقة بشرم الشيخ واحتفظ بنفس عدد الأيام والميزانية', original['trip_state'])
    assert edit['trip_state']['days'] == 7
    assert edit['trip_state']['budget_usd'] == 3000
    assert allocations(edit) == {'Cairo': 3, 'Luxor': 2, 'Sharm El Sheikh': 2}


def test_cairo_day_and_evening_asks_before_changing_total(client):
    original = ask(client, 'رحلة ٧ أيام: ٣ أيام في القاهرة، ويومين الأقصر، ويومين الغردقة')
    edit = ask(client, 'زوّد يوم في القاهرة يكون فيه مكان أثري الصبح وبالليل خروجة لطيفة زي خان الخليلي', original['trip_state'])
    assert edit['trip_state'] == original['trip_state']
    assert edit['itinerary'] is None
    assert 'خان الخليلي' in edit['answer']
    assert edit['mode'] == 'needs-clarification'


def test_outside_egypt_does_not_silently_replace_destination(client):
    original = ask(client, 'رحلة ٧ أيام في القاهرة')
    new = ask(client, 'طب ممكن تطلعني رحلة لروما بدل مصر؟', original['trip_state'])
    assert new['mode'] == 'unsupported-destination'
    assert new['trip_state'] == original['trip_state']
