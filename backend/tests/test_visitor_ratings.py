from uuid import uuid4

import pytest


@pytest.fixture(autouse=True)
def rating_limit_isolation(monkeypatch):
    from app.security import _guard_hits
    monkeypatch.setenv('RATING_RATE_PER_MINUTE', '100')
    for key in list(_guard_hits):
        if key[0] == 'rating':
            del _guard_hits[key]


@pytest.fixture
def member(client, tmp_path, monkeypatch):
    from app import accounts
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'accounts.sqlite3')
    accounts.setup()

    def register():
        email = f'qa-{uuid4().hex}@example.org'
        response = client.post('/api/auth/register', json={'email': email, 'password': 'Long-Test-Password-2026'})
        assert response.status_code == 201
        return {'Authorization': f"Bearer {response.json()['token']}"}, response.json()['user']

    return register


def test_account_required_and_client_cannot_claim_an_identity(client, member):
    target = '/api/ratings/giza-pyramids'
    assert client.post(target, json={'rating': 5}).status_code == 401
    assert client.post(target + '/comments', json={'comment': 'Beautiful place.'}).status_code == 401
    headers, _ = member()
    assert client.post(target, json={'rating': 5, 'visitor_id': str(uuid4())}, headers=headers).status_code == 422
    assert client.post(target + '/comments', json={'comment': 'Beautiful place.', 'name': 'Someone else'}, headers=headers).status_code == 422


def test_members_rate_and_edit_without_duplicate_votes(client, member):
    first, _ = member()
    second, _ = member()
    target = '/api/ratings/giza-pyramids'
    assert client.get('/api/ratings').json()['ratings'] == {}
    assert client.post(target, json={'rating': 5}, headers=first).json()['count'] == 1
    edited = client.post(target, json={'rating': 3}, headers=first).json()
    assert (edited['average'], edited['count']) == (3.0, 1)
    assert client.get('/api/ratings/mine', headers=first).json()['ratings']['giza-pyramids'] == 3
    assert client.get('/api/ratings/mine').status_code == 401
    other = client.post(target, json={'rating': 5}, headers=second).json()
    assert (other['average'], other['count']) == (4.0, 2)
    assert client.post('/api/ratings/coast:sharm-el-sheikh', json={'rating': 4}, headers=first).json()['count'] == 1
    listing = client.get('/api/ratings')
    assert listing.headers['cache-control'] == 'no-store'
    assert listing.json()['ratings'] == {
        'giza-pyramids': {'average': 4.0, 'count': 2},
        'coast:sharm-el-sheikh': {'average': 4.0, 'count': 1},
    }


def test_review_validation_catalog_rebuild_and_storage_notice(client, member):
    from app.database import initialize
    headers, _ = member()
    for rating in (0, 6, 'five'):
        assert client.post('/api/ratings/giza-pyramids', json={'rating': rating}, headers=headers).status_code == 422
    assert client.post('/api/ratings/no-such-place', json={'rating': 5}, headers=headers).status_code == 404
    assert client.get('/api/ratings/no-such-place/comments').status_code == 404
    assert client.post('/api/ratings/ben-ezra-synagogue', json={'rating': 5}, headers=headers).status_code == 200
    target = '/api/ratings/giza-pyramids/comments'
    for comment in ('https://spam.example', 'mail me a@b.com', '    '):
        assert client.post(target, json={'comment': comment}, headers=headers).status_code == 422
    assert client.post(target, json={'comment': 'The pyramids were memorable.'}, headers=headers).status_code == 200
    edited = client.post(target, json={'comment': 'Go early in the morning.'}, headers=headers).json()
    assert edited['count'] == 1
    assert edited['comments'][0]['comment'] == 'Go early in the morning.'
    assert edited['comments'][0]['name'].startswith('Traveler #')
    initialize()
    assert client.get('/api/ratings').json()['ratings']['ben-ezra-synagogue'] == {'average': 5.0, 'count': 1}
    assert client.get(target).json()['temporary_storage'] is True


def test_public_community_feed_shows_account_comments_without_identity(client, member):
    headers, user = member()
    target = '/api/ratings/coast:marsa-alam/comments'
    assert client.get('/api/ratings/recent-comments').json() == {'comments': []}
    posted = client.post(target, json={'comment': 'Check the beach access before visiting.'}, headers=headers)
    assert posted.status_code == 200
    feed = client.get('/api/ratings/recent-comments')
    assert feed.status_code == 200
    assert feed.json()['comments'] == [{
        'target_id': 'coast:marsa-alam',
        'name': posted.json()['comments'][0]['name'],
        'comment': 'Check the beach access before visiting.',
        'updated_at': posted.json()['comments'][0]['updated_at'],
    }]
    assert user['email'] not in str(feed.json())
    assert user['id'] not in str(feed.json())


def test_account_export_and_deletion_include_reviews(client, member):
    headers, user = member()
    target = '/api/ratings/coast:marsa-alam/comments'
    assert client.post(target, json={'comment': 'Lovely coastline.'}, headers=headers).status_code == 200
    assert client.post('/api/ratings/coast:marsa-alam', json={'rating': 4}, headers=headers).status_code == 200
    assert user['email'] not in str(client.get(target).json())
    exported = client.get('/api/my/export', headers=headers).json()
    assert exported['visitor_reviews']['comments'][0]['comment'] == 'Lovely coastline.'
    assert exported['visitor_reviews']['ratings'][0]['rating'] == 4
    deleted = client.request('DELETE', '/api/my/account', json={
        'password': 'Long-Test-Password-2026', 'confirmation': 'DELETE MY ACCOUNT'}, headers=headers)
    assert deleted.status_code == 200
    assert client.get(target).json()['count'] == 0
    assert client.get('/api/ratings').json()['ratings'] == {}
    assert client.post(target, json={'comment': 'Another comment.'}, headers=headers).status_code == 401


def test_confirmed_file_storage_keeps_account_and_review_across_restart(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app import accounts
    from app.main import app

    monkeypatch.setattr(accounts, '_DB', tmp_path / 'traveler.sqlite3')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'tourism.sqlite3'))
    monkeypatch.setenv('APP_ENV', 'portfolio')
    monkeypatch.setenv('MASR_DURABLE_STORAGE_CONFIRMED', 'true')
    email = f'persist-{uuid4().hex}@example.org'
    password = 'Long-Test-Password-2026'
    with TestClient(app) as first:
        assert first.get('/api/health').json()['registration_enabled'] is True
        created = first.post('/api/auth/register', json={'email': email, 'password': password})
        assert created.status_code == 201
        headers = {'Authorization': f"Bearer {created.json()['token']}"}
        assert first.post('/api/ratings/giza-pyramids', json={'rating': 5}, headers=headers).status_code == 200
        assert first.post('/api/ratings/giza-pyramids/comments', json={'comment': 'A memorable visit.'}, headers=headers).status_code == 200

    with TestClient(app) as restarted:
        login = restarted.post('/api/auth/login', json={'email': email, 'password': password})
        assert login.status_code == 200
        headers = {'Authorization': f"Bearer {login.json()['token']}"}
        assert restarted.get('/api/ratings').json() == {
            'ratings': {'giza-pyramids': {'average': 5.0, 'count': 1}},
            'temporary_storage': False,
        }
        assert restarted.get('/api/ratings/giza-pyramids/comments').json()['comments'][0]['comment'] == 'A memorable visit.'
        assert restarted.get('/api/ratings/mine', headers=headers).json()['ratings']['giza-pyramids'] == 5
