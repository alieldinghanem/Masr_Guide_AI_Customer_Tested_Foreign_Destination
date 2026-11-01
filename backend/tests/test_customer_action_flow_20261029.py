"""Customer-facing acceptance checks: natural city splits and real account actions.

Do not fake Gemini responses. These are the deterministic backend contracts;
provider quality and browser E2E require separate live verification.
"""
from fastapi.testclient import TestClient
from app.main import app, _chat_calls
from app import accounts


def _ask(client, text, state=None, token=None):
    response = client.post('/api/consult',
        headers={'Authorization': f'Bearer {token}'} if token else {},
        json={'message': text, 'language': 'Arabic', 'trip_state': state})
    return response


def test_family_day_split_and_follow_up_edit(client):
    start = _ask(client, 'أنا جاي مصر 6 أيام: 4 أيام القاهرة ويومين الأقصر مع زوجتي وطفلي')
    assert start.status_code == 200
    a = start.json()
    assert a['itinerary']['day_allocation'] == {'Cairo': 4, 'Luxor': 2}
    assert a['trip_state']['family'] is True
    assert 'لم يُحفظ في حسابك' in a['answer']
    changed = _ask(client, 'غيرها إلى 3 أيام القاهرة و3 أيام أسوان', a['trip_state'])
    assert changed.status_code == 200
    b = changed.json()
    assert b['itinerary']['day_allocation'] == {'Cairo': 3, 'Aswan': 3}
    assert b['trip_state']['days'] == 6
    assert b['trip_state']['family'] is True
    assert b['trip_state']['budget_egp'] == a['trip_state']['budget_egp']


def test_conflicting_overall_duration_rejected(client):
    response = _ask(client, 'خطط رحلة 6 أيام: 4 أيام القاهرة و3 أيام الأقصر')
    assert response.status_code == 200
    assert response.json()['mode'] == 'needs-clarification'
    assert response.json()['itinerary'] is None


def test_save_action_is_real_and_owned(tmp_path, monkeypatch):
    monkeypatch.setenv('MASR_USER_DB', str(tmp_path/'accounts.sqlite3'))
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path/'places.sqlite3'))
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.setattr(accounts, '_DB', None)
    _chat_calls.clear()
    with TestClient(app) as client:
        first = _ask(client, 'خطط رحلة 6 أيام: 4 أيام القاهرة ويومين الأقصر')
        assert first.status_code == 200
        state = first.json()['trip_state']

        unauth = _ask(client, 'احفظ الرحلة في حسابي', state).json()
        assert unauth['mode'] == 'needs-authentication'
        assert 'saved_trip_id' not in unauth

        empty = _ask(client, 'احفظ الرحلة في حسابي').json()
        assert empty['mode'] == 'needs-clarification'

        r1 = client.post('/api/auth/register', json={
            'email': 'visitor1@example.com', 'password': 'test-password-long-001'})
        r2 = client.post('/api/auth/register', json={
            'email': 'visitor2@example.com', 'password': 'test-password-long-002'})
        assert r1.status_code == 201 and r2.status_code == 201
        t1, t2 = r1.json()['token'], r2.json()['token']

        saved = _ask(client, 'ممكن تحفظ الرحلة باسمي', state, t1)
        assert saved.status_code == 200, saved.text
        assert saved.json()['mode'] == 'trip-saved'
        trip_id = saved.json()['saved_trip_id']
        own = client.get(f'/api/my/trips/{trip_id}', headers={'Authorization': f'Bearer {t1}'})
        assert own.status_code == 200
        assert own.json()['itinerary']['day_allocation'] == {'Cairo': 4, 'Luxor': 2}
        outsider = client.get(f'/api/my/trips/{trip_id}', headers={'Authorization': f'Bearer {t2}'})
        assert outsider.status_code == 404
        assert client.get('/api/my/trips', headers={'Authorization': f'Bearer {t2}'}).json()['trips'] == []

        invalid = _ask(client, 'احفظ الرحلة في حسابي', state, 'not_a_real_token_at_least_35_chars_1234567')
        assert invalid.status_code == 401
        assert len(client.get('/api/my/trips', headers={'Authorization': f'Bearer {t1}'}).json()['trips']) == 1
        client.post('/api/auth/logout', headers={'Authorization': f'Bearer {t1}'})
        assert _ask(client, 'احفظ الرحلة في حسابي', state, t1).status_code == 401
    _chat_calls.clear()


def test_airport_and_family_questions_do_not_misroute(client):
    airport = _ask(client, 'ازاي اروح من مطار القاهرة للزمالك؟')
    assert airport.status_code == 200
    a = airport.json()
    assert a['mode'] == 'local-assistant'
    assert 'الزمالك' in a['answer'] and 'مطار' in a['answer']
    assert 'سعر' in a['answer']
    family = _ask(client, 'أنا أول مرة أزور مصر مع زوجتي وطفلين، تنصحنا بإيه؟')
    assert family.status_code == 200
    b = family.json()
    assert b['mode'] == 'local-assistant'
    assert 'الأهرامات' in b['answer'] and 'أعمار الأطفال' in b['answer']
