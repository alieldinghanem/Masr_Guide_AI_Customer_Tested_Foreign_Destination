"""Regression tests discovered in the v1.4 final-release review."""
import pytest

@pytest.mark.parametrize('message', ['   ', ' \n\t ', '\u2003'])
def test_blank_guide_question_rejected(client, message):
    response = client.post('/api/chat', json={'message': message})
    assert response.status_code == 422


def test_normal_guide_question_stripped(client):
    response = client.post('/api/chat', json={'message': '  Tell me about Karnak Temple  '})
    assert response.status_code == 200
    assert response.json()['sources'][0]['id'] == 'karnak'


def test_trip_one_city_per_day_and_budget_only_recorded(client):
    response = client.post('/api/plan', json={
        'cities': ['Cairo', 'Luxor', 'Aswan'], 'days': 4,
        'interests': ['history', 'culture'], 'budget_usd': 200,
    })
    assert response.status_code == 200
    payload = response.json()
    assert len(payload['days']) == 4
    assert set(x['city'] for x in payload['days']) == {'Cairo','Luxor','Aswan'}
    assert payload['budget_usd'] == 200
    assert 'NOT used' in payload['disclaimer']


def test_invalid_body_shapes_produce_validation_not_500(client):
    examples = [
        ('/api/plan', []),
        ('/api/plan', {'cities': 'Cairo', 'days': 1}),
        ('/api/plan', {'cities': ['Cairo'], 'days': 'nonsense'}),
        ('/api/chat', {'message': {'text': 'hello'}}),
        ('/api/chat', {'message': 'hello', 'language': 'Spanish'}),
        ('/api/chat', {'message': 'hello', 'history': [{'role':'system','content':'hey'}]}),
    ]
    for url, payload in examples:
        response = client.post(url, json=payload)
        assert response.status_code == 422, (url, payload, response.text)


def test_reference_numbers_match_ranked_matches(client):
    question = 'Tell me about the Nubian Museum'
    response = client.post('/api/chat', json={'message': question})
    assert response.status_code == 200
    refs = response.json()['sources']
    assert len(refs) <= 4
    assert [x['number'] for x in refs] == list(range(1, len(refs) + 1))
    assert refs[0]['id'] == 'nubian-museum'


def test_catalog_has_no_secrets_or_private_http_references(client):
    places = client.get('/api/places').json()['places']
    from app.catalog import PLACES
    assert len(places) == len(PLACES) >= 40
    for p in places:
        assert p['source_url'].startswith('https://')
        assert all(x not in p['source_url'].lower() for x in ('localhost', '127.0.0.1', '@'))
        assert p['visit_minutes'] > 0
