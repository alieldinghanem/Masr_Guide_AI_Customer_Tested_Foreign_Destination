from uuid import uuid4
import pytest


@pytest.fixture(autouse=True)
def rating_limit_isolation(monkeypatch):
    from app.security import _guard_hits
    monkeypatch.setenv('RATING_RATE_PER_MINUTE', '100')
    for key in list(_guard_hits):
        if key[0] == 'rating':
            del _guard_hits[key]


def test_visitors_can_rate_catalog_and_coastal_guides_without_duplicate_votes(client):
    voter = str(uuid4())
    second_voter = str(uuid4())
    assert client.get('/api/ratings').json()['ratings'] == {}
    first = client.post('/api/ratings/giza-pyramids', json={'visitor_id': voter, 'rating': 5})
    assert first.status_code == 200
    assert first.json()['count'] == 1
    assert first.json()['average'] == 5.0
    edited = client.post('/api/ratings/giza-pyramids', json={'visitor_id': voter, 'rating': 3})
    assert edited.status_code == 200
    assert edited.json()['count'] == 1
    assert edited.json()['average'] == 3.0
    other = client.post('/api/ratings/giza-pyramids', json={'visitor_id': second_voter, 'rating': 5})
    assert other.status_code == 200
    assert other.json()['count'] == 2
    assert other.json()['average'] == 4.0
    coast = client.post('/api/ratings/coast:sharm-el-sheikh', json={'visitor_id': voter, 'rating': 4})
    assert coast.status_code == 200
    assert coast.json()['count'] == 1
    listing = client.get('/api/ratings')
    assert listing.status_code == 200
    assert listing.headers['cache-control'] == 'no-store'
    assert listing.json()['ratings'] == {
        'giza-pyramids': {'average': 4.0, 'count': 2},
        'coast:sharm-el-sheikh': {'average': 4.0, 'count': 1},
    }


def test_rating_validation_and_unknown_targets(client):
    voter = str(uuid4())
    for rating in (0, 6, 'five'):
        assert client.post('/api/ratings/giza-pyramids', json={'visitor_id': voter, 'rating': rating}).status_code == 422
    assert client.post('/api/ratings/giza-pyramids', json={'visitor_id': 'not-a-uuid', 'rating': 5}).status_code == 422
    assert client.post('/api/ratings/no-such-place', json={'visitor_id': voter, 'rating': 5}).status_code == 404
    assert client.post('/api/ratings/coast:no-such-place', json={'visitor_id': voter, 'rating': 5}).status_code == 404


def test_ratings_survive_catalog_rebuild_and_expose_temporary_storage(client):
    from app.database import initialize
    voter = str(uuid4())
    assert client.post('/api/ratings/ben-ezra-synagogue', json={'visitor_id': voter, 'rating': 5}).status_code == 200
    initialize()
    listing = client.get('/api/ratings').json()
    assert listing['ratings']['ben-ezra-synagogue'] == {'average': 5.0, 'count': 1}
    assert listing['temporary_storage'] is True
