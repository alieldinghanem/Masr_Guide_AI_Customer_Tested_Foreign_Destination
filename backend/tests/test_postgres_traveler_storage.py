"""Exercise the real PostgreSQL path on CI's temporary database."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import accounts, security
from app.main import app


@pytest.mark.skipif(not os.getenv('MASR_TEST_POSTGRES_URL'), reason='PostgreSQL service not configured')
def test_traveler_account_and_reviews_survive_catalog_rebuild_and_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', None)
    monkeypatch.setenv('NEON_DATABASE_URL', os.environ['MASR_TEST_POSTGRES_URL'])
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'derived_catalog.sqlite3'))
    monkeypatch.setenv('APP_ENV', 'portfolio')
    monkeypatch.setenv('MASR_DURABLE_STORAGE_CONFIRMED', 'true')
    monkeypatch.setenv('ADMIN_API_TOKEN', 'postgres-test-staff-key-not-for-live')
    staff = {'X-Admin-Key': 'postgres-test-staff-key-not-for-live'}
    security._guard_hits.clear()
    email = f'postgres-qa-{uuid4().hex}@example.org'
    password = 'Postgres-Test-Password-2026!'
    with TestClient(app) as first:
        assert first.get('/api/ready').status_code == 200
        assert first.get('/api/health').json()['registration_enabled'] is True
        created = first.post('/api/auth/register', json={'email': email, 'password': password})
        assert created.status_code == 201, created.text
        duplicate = first.post('/api/auth/register', json={'email': email, 'password': password})
        assert duplicate.status_code == 409, duplicate.text
        headers = {'Authorization': f"Bearer {created.json()['token']}"}
        assert first.post('/api/my/favorites/karnak', headers=headers).status_code == 200
        assert first.post('/api/ratings/giza-pyramids', json={'rating': 5}, headers=headers).status_code == 200
        assert first.post('/api/ratings/giza-pyramids/comments',
                          json={'comment': 'A memorable visit.'}, headers=headers).status_code == 200
        published_offer = first.post('/api/admin/offers', headers=staff, json={
            'title': 'Synthetic Giza experience', 'city': 'Giza',
            'description': 'A synthetic listing to test durable storage.',
            'partner': 'Demo agency', 'target_url': 'https://example.org/booking?campaign=test',
            'enabled': True, 'itinerary_place_id': 'giza-pyramids',
        })
        assert published_offer.status_code == 201, published_offer.text
        offer_id = published_offer.json()['id']
        redirect = first.get(f'/api/go/{offer_id}?from_itinerary=true', follow_redirects=False)
        assert redirect.status_code == 302

    with TestClient(app) as restarted:
        published = restarted.get('/api/partner-offers?itinerary_only=true').json()['offers']
        assert any(row['id'] == offer_id and row['itinerary_place_id'] == 'giza-pyramids' for row in published)
        staff_offers = restarted.get('/api/admin/offers', headers=staff).json()['offers']
        recorded = next(row for row in staff_offers if row['id'] == offer_id)
        assert (recorded['outbound_clicks'], recorded['itinerary_clicks']) == (1, 1)
        assert restarted.delete(f'/api/admin/offers/{offer_id}', headers=staff).status_code == 200
        assert all(row['id'] != offer_id for row in restarted.get('/api/partner-offers?itinerary_only=true').json()['offers'])
        login = restarted.post('/api/auth/login', json={'email': email, 'password': password})
        assert login.status_code == 200, login.text
        headers = {'Authorization': f"Bearer {login.json()['token']}"}
        assert restarted.get('/api/my/favorites', headers=headers).json() == {'place_ids': ['karnak']}
        assert restarted.get('/api/ratings').json() == {
            'ratings': {'giza-pyramids': {'average': 5.0, 'count': 1}},
            'temporary_storage': False,
        }
        comments = restarted.get('/api/ratings/giza-pyramids/comments').json()
        assert comments['comments'][0]['comment'] == 'A memorable visit.'
        deleted = restarted.request('DELETE', '/api/my/account', headers=headers, json={
            'password': password, 'confirmation': 'DELETE MY ACCOUNT'})
        assert deleted.status_code == 200, deleted.text
        assert restarted.get('/api/ratings').json()['ratings'] == {}
