"""The chat and beach pages must recommend the same documented swim areas."""

import json
from pathlib import Path

import pytest

from app.coastal_guide import DESTINATIONS
from app.database import initialize
from app.schemas import ChatTurn, ConsultRequest
from app.travel_agent import consult_travel


@pytest.fixture
def offline_guide(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'guide.sqlite3'))
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    initialize()


def _ask(message, language='Arabic', history=None):
    return consult_travel(ConsultRequest(message=message, language=language, history=history or []))


def test_shared_beach_data_has_a_source_and_distinct_destination_for_every_ui_card():
    source = Path(__file__).resolve().parents[2] / 'frontend' / 'src' / 'coastalDestinations.json'
    assert DESTINATIONS == json.loads(source.read_text(encoding='utf-8'))
    assert len(DESTINATIONS) == 10
    assert len({item['id'] for item in DESTINATIONS}) == len(DESTINATIONS)
    assert all(item['url'].startswith('https://') and item['spotAr'] and item['spotEn']
               for item in DESTINATIONS)


@pytest.mark.parametrize('destination', DESTINATIONS, ids=lambda item: item['id'])
def test_every_ui_beach_destination_can_be_recommended_in_arabic(offline_guide, destination):
    reply = _ask(f"تنصحني بشاطئ للسباحة في {destination['ar']}؟")
    assert reply['mode'] == 'local-assistant'
    assert destination['spotAr'] in reply['answer']
    assert reply['sources'][0]['url'] == destination['url']
    assert reply['sources'][0]['id'] == 'coast:' + destination['id']
    assert 'حالة البحر' in reply['answer']


def test_english_beach_question_and_arabic_city_followup_keep_beach_context(offline_guide):
    english = _ask('Where should I swim in Marsa Alam?', language='English')
    assert english['sources'][0]['id'] == 'coast:marsa-alam'
    assert 'Sharm El Luli Beach' in english['answer']
    first = _ask('تنصحني بشاطئ للسباحة في شرم الشيخ؟')
    history = [ChatTurn(role='user', content='تنصحني بشاطئ للسباحة في شرم الشيخ؟'),
               ChatTurn(role='assistant', content=first['answer'])]
    followup = _ask('وماذا عن مرسى مطروح؟', history=history)
    assert followup['sources'][0]['id'] == 'coast:marsa-matruh'
    assert 'رحلة قارب' in followup['answer']


def test_broad_quiet_beach_question_offers_documented_options(offline_guide):
    reply = _ask('عايز شاطئ هادي في مصر، ترشحلي إيه؟')
    assert reply['mode'] == 'local-assistant'
    assert reply['sources'][0]['id'] == 'coast:nuweiba'
    assert len(reply['sources']) == 3


def test_named_beach_without_city_uses_its_destination(offline_guide):
    reply = _ask('تنصحني أسبح في شرم اللولي؟')
    assert reply['sources'][0]['id'] == 'coast:marsa-alam'
    assert 'شرم اللولي' in reply['answer']


def test_live_sea_condition_question_does_not_claim_current_safety(offline_guide):
    reply = _ask('هل شاطئ المعمورة في الإسكندرية آمن للسباحة اليوم؟')
    assert reply['sources'] == []
    assert 'ماقدرش أؤكد' in reply['answer']
    assert 'المنقذين' in reply['answer']


def test_current_beach_access_question_does_not_claim_opening(offline_guide):
    reply = _ask('شاطئ المعمورة مفتوح اليوم؟')
    assert reply['sources'] == []
    assert 'ما عنديش تأكيد مباشر' in reply['answer']
