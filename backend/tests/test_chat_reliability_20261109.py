"""End-to-end regressions for day edits, intent, recommendations and memory."""

from app.schemas import ChatRequest, ChatTurn, ConsultRequest, TripState
from app.guide import answer_chat, retrieve
from app.travel_agent import consult_travel


def test_single_family_activity_edit_changes_only_day_three(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    original = consult_travel(ConsultRequest(
        message='خطط 7 أيام في القاهرة والغردقة مع الأطفال آثار وبحر',
        language='Arabic'))
    state = TripState.model_validate(original['trip_state'])
    before = original['itinerary']['days']
    edited = consult_travel(ConsultRequest(
        message='خلي اليوم الثالث نشاط واحد مناسب للأطفال',
        language='Arabic', trip_state=state))
    assert edited['mode'] == 'local-planner', edited
    assert edited['trip_state']['day_overrides'][3] == {
        'max_stops': 1, 'family_friendly': True}
    assert len(edited['itinerary']['days'][2]['stops']) == 1
    assert edited['itinerary']['days'][2]['stops'][0]['place']['family_friendly']
    assert edited['itinerary']['days'][2]['rest_minutes'] == 45
    assert [day for i, day in enumerate(edited['itinerary']['days']) if i != 2] == [
        day for i, day in enumerate(before) if i != 2]
    assert edited['trip_state']['days'] == original['trip_state']['days']
    assert edited['trip_state']['phases'] == original['trip_state']['phases']
    followup = consult_travel(ConsultRequest(
        message='ايه خطة اليوم الثالث؟', language='Arabic',
        trip_state=TripState.model_validate(edited['trip_state'])))
    assert edited['itinerary']['days'][2]['stops'][0]['place']['name_ar'] in followup['answer']


def test_out_of_range_day_edit_does_not_change_trip(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    first = consult_travel(ConsultRequest(message='Plan 3 days in Cairo', language='English'))
    state = TripState.model_validate(first['trip_state'])
    result = consult_travel(ConsultRequest(
        message='Make day 9 one activity', language='English', trip_state=state))
    assert result['mode'] == 'needs-clarification'
    assert result['trip_state'] == first['trip_state']


def test_negated_diving_routes_to_sourced_swimming_beach(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    result = answer_chat(ChatRequest(
        message='رشحلي شاطئ للسباحة في دهب، مش مكان غطس', language='Arabic'))
    assert result['sources'][0]['id'] == 'coast:dahab'
    assert result['sources'][0]['url'].startswith('https://')
    assert 'شواطئ دهب' in result['answer']
    assert 'ماقدرش أؤكد إن البحر آمن للغوص' not in result['answer']
    assert all(place['category'] == 'Beach' for place in retrieve('شاطئ للسباحة في دهب مش غطس'))
    assert all(place['id'] != 'blue-hole-dahab' for place in retrieve('شاطئ للسباحة في دهب مش غطس'))


def test_genuine_current_diving_safety_question_keeps_warning():
    result = answer_chat(ChatRequest(message='هل الغوص آمن اليوم في دهب؟', language='Arabic'))
    assert 'ماقدرش أؤكد إن البحر آمن للغوص' in result['answer']
    english = answer_chat(ChatRequest(message='Is diving safe in Dahab today?', language='English'))
    assert 'cannot confirm that diving' in english['answer']


def test_english_negated_diving_still_recommends_a_beach(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    result = answer_chat(ChatRequest(
        message='Recommend a swimming beach in Dahab, not a diving spot', language='English'))
    assert result['sources'][0]['id'] == 'coast:dahab'


def test_national_family_recommendation_is_specific_and_cited(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    result = answer_chat(ChatRequest(
        message='رشحلي آثار في مصر مناسبة للأطفال', language='Arabic'))
    assert result['sources']
    assert result['sources'][0]['url'].startswith('https://')
    assert result['sources'][0]['title_ar'] in result['answer']
    assert '[1]' in result['answer']


def test_family_plan_has_rest_and_avoids_extra_city_transfer(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    result = consult_travel(ConsultRequest(
        message='Plan 8 days in Egypt for our family with kids, history and beaches at an easy pace',
        language='English'))
    assert result['trip_state']['family'] is True
    assert result['itinerary']['route'] == ['Cairo', 'Hurghada']
    assert all(len(day['stops']) <= 2 for day in result['itinerary']['days'])
    assert all(day['rest_minutes'] == 45 for day in result['itinerary']['days'] if day['stops'])
    assert all(not day['stops'] for day in result['itinerary']['days']
               if day.get('travel') and day['travel']['minutes'] >= 180)


def test_second_recommendation_survives_english_followup(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    first = answer_chat(ChatRequest(message='Recommend historical places in Cairo', language='English'))
    assert len(first['sources']) >= 2
    followup = answer_chat(ChatRequest(
        message='Tell me more about the second one', language='English',
        history=[ChatTurn(role='user', content='Recommend historical places in Cairo'),
                 ChatTurn(role='assistant', content=first['answer'])]))
    assert followup['sources'][0]['id'] == first['sources'][1]['id']
    assert first['sources'][1]['title'] in followup['answer']


def test_second_recommendation_survives_arabic_followup(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    first = answer_chat(ChatRequest(message='رشحلي آثار في القاهرة', language='Arabic'))
    assert len(first['sources']) >= 2
    followup = answer_chat(ChatRequest(
        message='احكيلي عن المكان التاني', language='Arabic',
        history=[ChatTurn(role='user', content='رشحلي آثار في القاهرة'),
                 ChatTurn(role='assistant', content=first['answer'])]))
    assert followup['sources'][0]['id'] == first['sources'][1]['id']
