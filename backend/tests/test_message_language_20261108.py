"""A visitor's English message must get an English answer on an Arabic site."""

from app.conversation_router import detect_language
from app.database import initialize
from app.schemas import ConsultRequest
from app.travel_agent import consult_travel


def test_message_script_overrides_site_language_but_short_ack_keeps_context():
    assert detect_language('Tell me about Karnak', 'Arabic') == 'English'
    assert detect_language('Hello', 'Arabic') == 'English'
    assert detect_language('حدثني عن الكرنك', 'English') == 'Arabic'
    assert detect_language('I want to visit الأهرامات', 'Arabic') == 'English'
    assert detect_language('عايز أزور Karnak', 'English') == 'Arabic'
    assert detect_language('ok', 'Arabic') == 'Arabic'
    assert detect_language('Cairo', 'Arabic') == 'Arabic'
    assert detect_language('رد بالإنجليزي عن القاهرة', 'Arabic') == 'English'


def test_english_arrival_and_family_plan_work_with_arabic_site_setting(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'guide.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    initialize()
    arrival = consult_travel(ConsultRequest(message="I'm coming to Egypt soon", language='Arabic'))
    assert arrival['answer'].startswith('Welcome to Egypt!')
    plan = consult_travel(ConsultRequest(
        message='Plan a 14-day family trip to Cairo, Luxor and Hurghada', language='Arabic'))
    assert plan['trip_state']['days'] == 14
    assert plan['trip_state']['family'] is True
    assert 'Here is a draft itinerary' in plan['answer']
