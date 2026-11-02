"""Direct regression tests for the customer-reported chatbot failures."""
from collections import Counter

from app.database import initialize
from app.guide import offline_answer
from app.conversation_router import special_reply
from app.schemas import ChatTurn, ConsultRequest
from app.travel_agent import consult_travel


def _allocation(reply):
    return dict(Counter(day['city'] for day in reply['itinerary']['days']))


def test_explicit_arabic_total_extension_preserves_every_other_city(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    original = consult_travel(ConsultRequest(
        message='رحلة ٧ أيام: ٣ أيام في القاهرة، ويومين الأقصر، ويومين الغردقة',
        language='Arabic',
    ))
    reply = consult_travel(ConsultRequest(
        message='زوّد إجمالي مدة الرحلة يوم واحد، من غير ما نقلل باقي المدن',
        language='Arabic', trip_state=original['trip_state'],
        history=[
            ChatTurn(role='user', content='زود يوم للقاهرة'),
            ChatTurn(role='assistant', content='هل تريد زيادة الإجمالي أم نقل يوم من مدينة أخرى؟'),
        ],
    ))
    assert reply['mode'] == 'local-planner'
    assert reply['trip_state']['days'] == 8
    assert _allocation(reply) == {'Cairo': 4, 'Luxor': 2, 'Hurghada': 2}


def test_hyphenated_english_family_trip_keeps_context_on_replacement(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    first = consult_travel(ConsultRequest(
        message='Plan a 14-day family trip to Egypt with Cairo, Luxor, and Hurghada.',
        language='English',
    ))
    assert first['trip_state']['days'] == 14
    assert first['trip_state']['family'] is True
    assert {'Cairo', 'Luxor', 'Hurghada'} <= set(_allocation(first))

    second = consult_travel(ConsultRequest(
        message='Replace Hurghada with Sharm El Sheikh and keep the same duration.',
        language='English', trip_state=first['trip_state'],
        history=[
            ChatTurn(role='user', content='Plan a 14-day family trip to Egypt with Cairo, Luxor, and Hurghada.'),
            ChatTurn(role='assistant', content=first['answer'][:1500]),
        ],
    ))
    assert second['trip_state']['days'] == 14
    assert second['trip_state']['family'] is True
    assert _allocation(first)['Luxor'] >= 2
    assert _allocation(second) == {'Cairo': 5, 'Luxor': 2, 'Sharm El Sheikh': 7}


def test_total_extension_without_a_city_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    original = consult_travel(ConsultRequest(
        message='رحلة ٧ أيام: ٣ أيام في القاهرة، ويومين الأقصر، ويومين الغردقة',
        language='Arabic',
    ))
    reply = consult_travel(ConsultRequest(
        message='زوّد إجمالي مدة الرحلة يوم واحد، من غير ما نقلل باقي المدن',
        language='Arabic', trip_state=original['trip_state'],
    ))
    assert reply['mode'] == 'needs-clarification'
    assert reply['trip_state'] == original['trip_state']
    assert reply['itinerary'] is None


def test_ambiguous_city_increase_never_steals_a_day(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    original = consult_travel(ConsultRequest(
        message='رحلة ٧ أيام: ٣ أيام في القاهرة، ويومين الأقصر، ويومين الغردقة',
        language='Arabic',
    ))
    reply = consult_travel(ConsultRequest(
        message='زود يوم للقاهرة', language='Arabic',
        trip_state=original['trip_state'],
    ))
    assert reply['mode'] == 'needs-clarification'
    assert reply['trip_state'] == original['trip_state']
    assert reply['itinerary'] is None


def test_empty_catalog_fallback_never_shows_the_dead_end_message():
    answer = offline_answer([], 'Arabic')
    assert 'مدة الرحلة' in answer
    assert 'الآثار' in answer
    assert 'لا توجد معلومات كافية' not in answer
    assert 'مزود الذكاء الاصطناعي' not in answer


def test_colloquial_single_city_two_day_stay_creates_a_plan(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    reply = consult_travel(ConsultRequest(message='عايز أزور اسكندريه يومين', language='Arabic'))
    assert reply['trip_state']['days'] == 2
    assert [day['city'] for day in reply['itinerary']['days']] == ['Alexandria', 'Alexandria']


def test_current_admission_price_variants_do_not_return_catalogue_description():
    for message in ('سعر تذكرة قلعة صلاح الدين النهارده كام؟',
                    'بكام دخول قلعة صلاح الدين؟',
                    'What is the entry fee for the Citadel today?'):
        language = 'Arabic' if 'قلعة' in message else 'English'
        reply = special_reply(message, language)
        assert reply['mode'] == 'local-assistant'
        assert 'سعر' in reply['answer'] or 'price' in reply['answer']


def test_compound_citadel_history_and_evening_outing_answers_both_parts(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    reply = consult_travel(ConsultRequest(
        message='ممكن تحكيلي عن قلعة صلاح الدين وتساعدني أختار مكان للفسحة بالليل؟',
        language='Arabic',
    ))
    assert 'قلعة صلاح الدين' in reply['answer']
    assert 'خان الخليلي' in reply['answer']
    assert 'مفتوحة مساءً' in reply['answer']
    assert [source['id'] for source in reply['sources']] == ['citadel', 'khan-el-khalili']


def test_vague_followup_uses_existing_trip_duration(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'travel.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    initialize()
    original = consult_travel(ConsultRequest(
        message='رحلة ٧ أيام: ٣ أيام في القاهرة، ويومين الأقصر، ويومين الغردقة',
        language='Arabic',
    ))
    reply = consult_travel(ConsultRequest(
        message='طيب إيه أحسن حاجة أعملها؟', language='Arabic',
        trip_state=original['trip_state'],
    ))
    assert reply['trip_state'] == original['trip_state']
    assert reply['itinerary'] is None
    assert '7 أيام' in reply['answer']
    assert 'كام يوم' not in reply['answer']
