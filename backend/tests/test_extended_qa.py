"""Independent release QA cases in addition to the base suite."""
import random

from app.guide import retrieve
from app.planner import PACE_LIMITS, build_plan
from app.schemas import PlanRequest


def test_multilingual_specific_landmarks_rank_first(client):
    samples = {
        'المتحف النوبي': 'nubian-museum',
        'المتحف المصري الكبير': 'grand-egyptian-museum',
        'متحف الحضارة': 'nmec',
        'معبد الكرنك': 'karnak',
        'قلعة قايتباي': 'qaitbay',
        'Parlez-moi des pyramides de Gizeh': 'giza-pyramids',
    }
    for question, expected in samples.items():
        matches = retrieve(question)
        assert matches and matches[0]['id'] == expected, question


def test_randomized_plans_keep_constraints(client):
    rng = random.Random(421)
    cities = client.get('/api/cities').json()['cities']
    interests = client.get('/api/cities').json()['interests']
    available_ids = {p['id'] for p in client.get('/api/places').json()['places']}
    for _ in range(250):
        requested_cities = rng.sample(cities, rng.randint(1, 6))
        days = rng.randint(len(requested_cities), 14)
        pace = rng.choice(tuple(PACE_LIMITS))
        family = bool(rng.getrandbits(1))
        request = PlanRequest(
            cities=requested_cities, days=days, pace=pace, family=family,
            interests=rng.sample(interests, rng.randint(0, 5)))
        plan = build_plan(request)
        assert len(plan['days']) == days
        assert [day['city'] for day in plan['days']] == [
            city for city in requested_cities
            for _ in range(plan['day_allocation'][city])]
        stops = [stop['place'] for day in plan['days'] for stop in day['stops']]
        assert len({p['id'] for p in stops}) == len(stops) == plan['total_places']
        assert all(p['id'] in available_ids for p in stops)
        assert all(day['estimated_activity_minutes'] <= PACE_LIMITS[pace]
                   for day in plan['days'])
        assert all(stop['place']['city'] == day['city'] for day in plan['days']
                   for stop in day['stops'])
        assert not family or all(p['family_friendly'] for p in stops)
        assert all(bool(day['note']) != bool(day['stops']) for day in plan['days'])


def test_catalog_coordinates_unique_https_and_minutes(client):
    places = client.get('/api/places').json()['places']
    from app.catalog import PLACES
    assert len(places) == len(PLACES) >= 40
    assert len({p['id'] for p in places}) == len(places)
    assert len({p['city'] for p in places}) == 12
    for place in places:
        assert 20 < place['lat'] < 33 and 24 < place['lng'] < 36
        assert place['visit_minutes'] > 0
        assert place['source_url'].startswith('https://')


def test_requested_heritage_sites_have_distinct_verified_catalog_entries(client):
    places = {place['id']: place for place in client.get('/api/places').json()['places']}
    assert places['hanging-church']['name_ar'] == 'الكنيسة المعلّقة'
    assert places['hanging-church']['source_url'] == 'https://egymonuments.gov.eg/monuments/the-hanging-church/'
    assert places['bab-zuwayla']['name_ar'] == 'باب زويلة'
    assert places['bab-zuwayla']['source_url'] == 'https://egymonuments.gov.eg/monuments/bab-zuwayla'
    assert places['st-catherine-monastery']['city'] == 'Saint Catherine'
    assert 'Christian monastery' in places['st-catherine-monastery']['details']


def test_bad_json_and_query_inputs_never_return_server_error(client):
    cases = [
        ('POST', '/api/plan', {'cities': ['Cairo'], 'days': 'oops'}),
        ('POST', '/api/plan', {'cities': [None], 'days': 2}),
        ('POST', '/api/plan', {'cities': ['Cairo'], 'days': 1, 'interests': [None]}),
        ('POST', '/api/plan', {'cities': ['Cairo'], 'days': 1, 'budget_usd': -1}),
        ('POST', '/api/plan', {'cities': ['Cairo', 'Luxor'], 'days': 1}),
        ('POST', '/api/chat', {'message': 'A'}),
        ('POST', '/api/chat', {'message': 'What to see?', 'language': 'German'}),
        ('POST', '/api/chat', {'message': 'What to see?', 'history': [{'role': 'system','content':'hi'}]}),
    ]
    for method, url, payload in cases:
        result = client.request(method, url, json=payload)
        assert result.status_code == 422, (url, payload, result.text)
    assert client.get('/api/places', params={'q': 'x' * 121}).status_code == 422
    assert client.get('/api/places/does-not-exist').status_code == 404


def test_sql_query_injection_strings_not_executed(client):
    r = client.get('/api/places', params={'q': "'; DROP TABLE places; --"})
    assert r.status_code == 200
    assert r.json()['places'] == []
    assert client.get('/api/places').status_code == 200
    from app.catalog import PLACES
    assert len(client.get('/api/places').json()['places']) == len(PLACES)


def test_offline_three_languages_dont_claim_ai_answer(client):
    for lang in ['English', 'Arabic', 'French']:
        r = client.post('/api/chat', json={'message': 'Tell me about Karnak', 'language': lang})
        assert r.status_code == 200
        assert r.json()['mode'] == 'offline-preview'
        assert any(item['id'] == 'karnak' for item in r.json()['sources'])


def test_cors_authorized_and_blocked(client):
    ok = client.options('/api/chat', headers={'Origin': 'http://localhost:5173',
                              'Access-Control-Request-Method': 'POST'})
    assert ok.status_code == 200
    assert ok.headers['access-control-allow-origin'] == 'http://localhost:5173'
    bad = client.options('/api/chat', headers={'Origin': 'https://evil.example',
                              'Access-Control-Request-Method': 'POST'})
    assert bad.headers.get('access-control-allow-origin') != 'https://evil.example'


def test_missing_openai_sdk_returns_safe_local_fallback(client, monkeypatch):
    import sys
    import types
    from app.main import _chat_calls
    _chat_calls.clear()
    monkeypatch.setenv('OPENAI_API_KEY', 'test-not-secret')
    monkeypatch.setenv('AI_PROVIDER', 'auto')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setitem(sys.modules, 'openai', types.ModuleType('openai'))
    response = client.post('/api/chat', json={'message': 'Tell me about Karnak Temple'})
    assert response.status_code == 200
    assert response.json()['mode'] == 'offline-fallback'
    assert 'temporarily unavailable' in response.json()['answer']
    assert 'test-not-secret' not in response.text
