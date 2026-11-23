"""Live-review diving regressions: deterministic safety before the provider/planner."""
import pytest
from app.conversation_router import unsafe_dive_request

@pytest.mark.parametrize('message,language,required', [
    ('أنا مبتدئ وعايز أغوص في البلو هول لوحدي من غير مدرب', 'Arabic', 'ما تنزلش'),
    ('خططلي رحلة غوص في دهب لوحدي بدون مدرب', 'Arabic', 'مدرب معتمد'),
    ('I am a beginner. Plan a trip to dive the Blue Hole alone without an instructor.', 'English', 'Do not dive alone'),
    ('Can I scuba dive without certification?', 'English', 'qualified instructor'),
    ('Je suis débutant et je veux plonger seul au Blue Hole', 'French', 'Ne plongez pas seul'),
])
@pytest.mark.parametrize('path', ['/api/chat', '/api/consult'])
def test_unsafe_diving_gets_specific_sourced_warning_before_ai(client, monkeypatch, message, language, required, path):
    from app import guide
    monkeypatch.setattr(guide, 'generate', lambda *_a, **_k: pytest.fail('Safety must not call the provider'))
    result = client.post(path, json={'message': message, 'language': language})
    assert result.status_code == 200
    data = result.json()
    assert data['mode'] == 'local-assistant'
    assert required in data['answer']
    assert data['sources'][0]['url'].startswith('https://pro-cms.padi.com/')
    assert data.get('itinerary') is None

@pytest.mark.parametrize('message', [
    'رشحلي شاطئ للسباحة في دهب، مش مكان غطس، وهاكون لوحدي',
    'Recommend a beach for swimming alone in Dahab, not diving.',
    'I want to learn diving with an instructor, not alone.',
    'أنا مش عايز غوص، عايز شاطئ وهاكون لوحدي',
    'I am alone in Cairo. Recommend a museum.',
])
def test_negation_and_unrelated_solo_travel_do_not_trigger_dive_warning(message):
    assert unsafe_dive_request(message) is False

def test_dive_warning_preserves_active_trip(client):
    first = client.post('/api/consult', json={'message': 'Plan 6 days in Cairo and Hurghada', 'language': 'English'}).json()
    result = client.post('/api/consult', json={'message': 'Plan a dive in the Blue Hole alone without a guide', 'language': 'English', 'trip_state': first['trip_state']}).json()
    assert result['mode'] == 'local-assistant'
    assert result['trip_state'] == first['trip_state']
    assert result['itinerary'] is None
