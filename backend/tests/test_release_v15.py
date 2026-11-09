"""Release v1.5 regressions for indicator accuracy and city grouping."""
import os
from unittest.mock import patch

def test_health_does_not_claim_live_provider(client):
    with patch.dict(os.environ, {"OPENAI_API_KEY": "qa-placeholder"}):
        resp = client.get('/api/health')
    assert resp.status_code == 200
    assert resp.json()['guide_mode'] == 'llm-configured'
    from app.main import app
    assert resp.json()['version'] == app.version
    assert 'qa-placeholder' not in resp.text

def test_contiguous_city_days(client):
    body = {"cities": ["Aswan", "Cairo", "Giza"], "days": 11, "interests": ["history"]}
    resp = client.post('/api/plan', json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['days']) == body['days']
    expected = [city for city in body['cities'] for _ in range(data['day_allocation'][city])]
    assert [day['city'] for day in data['days']] == expected
    assert len({stop['place']['id'] for day in data['days'] for stop in day['stops']}) == data['total_places']

def test_offline_mode_truthful(client):
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        assert client.get('/api/health').json()['guide_mode'] == 'offline-preview'
        response = client.post('/api/chat', json={"message": "Tell me about the Sphinx"})
        assert response.status_code == 200
        assert response.json()['mode'] == 'offline-preview'
