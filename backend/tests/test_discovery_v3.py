from fastapi.testclient import TestClient
from app.main import app


def test_discover_destinations_are_derived_from_curated_catalog():
    with TestClient(app) as client:
        data = client.get('/api/discover/destinations').json()['destinations']
        assert len(data) >= 10
        cairo = next(d for d in data if d['city'] == 'Cairo')
        assert cairo['attraction_count'] > 0
        assert len(cairo['highlights']) > 0
        assert cairo['name_ar'] == 'القاهرة'
        assert any(d['city'] == 'Hurghada' for d in data)


def test_discover_experiences_counts_are_live_from_catalog():
    with TestClient(app) as client:
        data = client.get('/api/discover/experiences').json()['experiences']
        assert {'history', 'beaches', 'culture', 'food', 'nature', 'adventure', 'museums', 'family'} == {x['id'] for x in data}
        assert all(x['place_count'] >= 0 for x in data)
        assert next(x for x in data if x['id']=='history')['place_count'] > 0


def test_essentials_only_link_to_https_institutional_sources_and_no_fares():
    with TestClient(app) as client:
        data = client.get('/api/discover/essentials').json()['essentials']
        assert len(data) >= 3
        assert all(item['url'].startswith('https://') for item in data)
        assert all('price' not in item for item in data)
