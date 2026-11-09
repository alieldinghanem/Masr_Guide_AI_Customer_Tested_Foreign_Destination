"""Visitor-level regression scenarios discovered in the 2026-10-29 review.

These checks deliberately inspect answer semantics, not only HTTP 200. They do
not claim live hotel inventory, accessible routes, or Gemini quality.
"""
import pytest


def ask(client, message, **kwargs):
    result = client.post('/api/consult', json={'message': message, **kwargs})
    assert result.status_code == 200, result.text
    return result.json()


@pytest.mark.parametrize('message', [
    "I'm arriving at Cairo airport at 2 am, how do I reach Zamalek safely?",
    'How do I reach Zamalek from Cairo International Airport?',
    'مواصلات من مطار القاهرة للزمالك لو سمحت',
])
def test_airport_transfer_is_relevant_and_not_live_fare(client, message):
    result = ask(client, message)
    assert result['mode'] == 'local-assistant'
    answer = result['answer'].lower()
    assert 'zamalek' in answer or 'الزمالك' in answer
    assert 'airport' in answer or 'المطار' in answer or 'مطار' in answer
    assert 'live' in answer or 'مباشر' in answer


@pytest.mark.parametrize('message', [
    'Can you book me a hotel and pay with my card?',
    'Book our trip and pay with my card now.',
    'احجز الفندق وخليني ادفع بالكارت',
])
def test_card_payment_refused_before_booking_or_planner(client, message):
    result = ask(client, message)
    assert result['mode'] == 'local-assistant'
    assert result.get('itinerary') is None
    assert 'card' in result['answer'].lower() or 'بطاقت' in result['answer'] or 'كارت' in result['answer']
    assert 'cannot' in result['answer'].lower() or 'لا يمكن' in result['answer'] or 'ماتشاركش' in result['answer']


def test_wheelchair_question_is_not_fake_accessibility_verification(client):
    data = ask(client, 'أنا معايا طفل يستخدم كرسي متحرك هل معبد الكرنك متاح للكراسي؟')
    assert data['mode'] == 'local-assistant'
    assert 'ما عنديش تأكيد' in data['answer']
    assert 'معبد الكرنك' not in data['answer'] or 'بدون درجات' in data['answer']


def test_after_hours_question_has_no_unverified_access_claim(client):
    result = ask(client, 'هل أقدر أزور الأهرامات بالليل؟')
    assert result['mode'] == 'local-assistant'
    assert 'ماقدرش أؤكد' in result['answer']


def test_first_time_family_week_builds_trip_instead_of_generic_advice(client):
    result = ask(client, 'أنا جاي مصر أول مرة لمدة أسبوع مع زوجتي وطفلين، اقترح خطة عائلية')
    assert result['trip_state']['days'] == 7
    assert result['trip_state']['family'] is True
    assert len(result['itinerary']['days']) == 7
    assert 'لم يُحفظ' in result['answer']


def test_french_plan_is_answered_in_french(client):
    result = ask(client, 'Je vais au Caire avec mes enfants pour 5 jours, peux-tu proposer un programme?')
    assert result['trip_state']['days'] == 5
    assert result['trip_state']['family'] is True
    assert 'Votre itinéraire' in result['answer']
    assert '5 jours' in result['answer']
    assert 'Aucun tarif' in result['answer']


def test_mobility_requirement_persists_through_edit(client):
    initial = ask(client, 'Plan 6 days in Cairo for a wheelchair user')
    assert initial['trip_state']['accessibility_needs'] is True
    assert 'NOT verified' in ' '.join(initial['itinerary']['warnings']).replace('NOT been verified','NOT verified') or \
           any('accessibility' in warning.lower() for warning in initial['itinerary']['warnings'])
    edited = ask(client, 'Make the whole trip 7 days', trip_state=initial['trip_state'])
    assert edited['trip_state']['accessibility_needs'] is True
    assert edited['trip_state']['days'] == 7
    assert any('accessibility' in warning.lower() for warning in edited['itinerary']['warnings'])


def test_mobility_requirement_persists_full_reallocation(client):
    initial = ask(client, 'Plan 6 days: 4 Cairo and 2 Luxor for someone using a wheelchair')
    assert initial['trip_state']['accessibility_needs'] is True
    edited = ask(client, 'Change the trip: 3 days Cairo and 3 days Aswan', trip_state=initial['trip_state'])
    assert edited['trip_state']['accessibility_needs'] is True
    assert edited['trip_state']['days'] == 6
    assert edited['itinerary'] is not None


def test_accessibility_flag_survives_account_save_and_invalid_flag_is_rejected(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app, _chat_calls
    from app import accounts
    monkeypatch.setenv('MASR_USER_DB', str(tmp_path / 'users.sqlite3'))
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'places.sqlite3'))
    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.setattr(accounts, '_DB', None)
    _chat_calls.clear()
    with TestClient(app) as client:
        plan = ask(client, 'Plan 4 days in Cairo for a wheelchair user')
        assert plan['itinerary']['accessibility_needs'] is True
        user = client.post('/api/auth/register', json={
            'email': 'mobility-traveler@example.org', 'password': 'Secure-Visitor-Password-001'})
        assert user.status_code == 201
        headers = {'Authorization': 'Bearer ' + user.json()['token']}
        saved = client.post('/api/my/trips', headers=headers, json={
            'title': 'Accessible needs (unverified stops)', 'itinerary': plan['itinerary']})
        assert saved.status_code == 201, saved.text
        restored = client.get('/api/my/trips/' + saved.json()['id'], headers=headers)
        assert restored.json()['itinerary']['accessibility_needs'] is True
        assert any('accessibility' in w.lower() for w in restored.json()['itinerary']['warnings'])
        corrupt = {**plan['itinerary'], 'accessibility_needs': 'yes'}
        assert client.post('/api/my/trips', headers=headers, json={
            'title': 'Corrupted flag', 'itinerary': corrupt}).status_code == 422
    _chat_calls.clear()
