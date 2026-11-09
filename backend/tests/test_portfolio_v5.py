"""Release gates: CMS, controlled partner offers, admin isolation and long itineraries."""
from fastapi.testclient import TestClient
from app.main import app
from app import accounts


def test_cms_and_staff_isolation(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'accounts.sqlite3')
    monkeypatch.setenv('ADMIN_API_TOKEN', 'admin-test-token-with-at-least-24-characters')
    admin = {'X-Admin-Key': 'admin-test-token-with-at-least-24-characters'}
    with TestClient(app) as client:
        articles = client.get('/api/content/articles').json()['articles']
        assert len(articles) == 4
        assert client.get('/api/admin/overview').status_code == 403
        assert client.get('/api/admin/overview', headers={'X-Admin-Key':'wrong'}).status_code == 403
        assert client.get('/api/admin/overview', headers=admin).status_code == 200
        draft = {'slug':'original-test', 'title':'Test editorial story',
                 'summary':'A longer introduction for readers',
                 'body':'A longer original editorial text for the traveller to read on the website.',
                 'category':'Guide','published':False}
        created = client.post('/api/admin/articles', headers=admin, json=draft)
        assert created.status_code == 201, created.text
        assert not any(a['slug']=='original-test' for a in client.get('/api/content/articles').json()['articles'])
        assert client.post('/api/admin/articles', headers=admin, json=draft).status_code == 409
        ident = created.json()['id']
        published = client.put('/api/admin/articles/'+ident, headers=admin, json={**draft,'published':True})
        assert published.status_code == 200
        assert any(a['slug']=='original-test' for a in client.get('/api/content/articles').json()['articles'])
        assert client.delete('/api/admin/articles/'+ident, headers=admin).status_code == 200
        assert not any(a['slug']=='original-test' for a in client.get('/api/content/articles').json()['articles'])


def test_offers_are_not_bookable_or_public_until_approved(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'partners.sqlite3')
    monkeypatch.setenv('ADMIN_API_TOKEN', 'admin-test-token-with-at-least-24-characters')
    admin = {'X-Admin-Key': 'admin-test-token-with-at-least-24-characters'}
    offer = {'title':'Sample guided cultural tour', 'city':'Cairo',
             'description':'An example external experience offer from a contracted provider.',
             'partner':'Demo provider','target_url':'https://example.org/tour',
             'disclosure':'External provider; demonstration only.', 'enabled':False}
    with TestClient(app) as client:
        assert client.get('/api/partner-offers').json()['offers'] == []
        assert client.post('/api/admin/offers', json=offer).status_code == 403
        assert client.post('/api/admin/offers', headers=admin, json={**offer,'target_url':'javascript:alert(1)'}).status_code == 422
        created = client.post('/api/admin/offers', headers=admin, json=offer)
        assert created.status_code == 201, created.text
        ident = created.json()['id']
        assert client.get('/api/go/'+ident, follow_redirects=False).status_code == 404
        enabled = client.put('/api/admin/offers/'+ident, headers=admin, json={**offer, 'enabled':True})
        assert enabled.status_code == 200
        assert len(client.get('/api/partner-offers').json()['offers']) == 1
        redirect = client.get('/api/go/'+ident, follow_redirects=False)
        assert redirect.status_code == 302
        assert redirect.headers['location'] == 'https://example.org/tour'
        assert redirect.headers['referrer-policy'] == 'no-referrer'
        stats = client.get('/api/admin/overview', headers=admin).json()['counts']
        assert stats['affiliate_clicks'] == 1
        assert 'bookings' not in stats
        assert client.delete('/api/admin/offers/'+ident, headers=admin).status_code == 200
        assert client.get('/api/go/'+ident, follow_redirects=False).status_code == 404


def test_partner_request_review(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'interest.sqlite3')
    monkeypatch.setenv('PARTNER_INQUIRIES_ENABLED','1')
    monkeypatch.setenv('ADMIN_API_TOKEN','admin-test-token-with-at-least-24-characters')
    admin = {'X-Admin-Key':'admin-test-token-with-at-least-24-characters'}
    with TestClient(app) as c:
        response = c.post('/api/partners/apply', json={'company':'Local Tour Partner','email':'contact@example.org','city':'Luxor'})
        assert response.status_code == 201, response.text
        uid = response.json()['reference']
        assert c.get('/api/admin/partner-applications').status_code == 403
        apps = c.get('/api/admin/partner-applications',headers=admin).json()['applications']
        assert len(apps) == 1 and apps[0]['status'] == 'new'
        assert c.put('/api/admin/partner-applications/'+uid, headers=admin, json={'status':'approved'}).status_code == 422
        assert c.put('/api/admin/partner-applications/'+uid, headers=admin, json={'status':'contacted'}).status_code == 200


def test_long_trips_expose_honest_activity_ideas(client):
    response = client.post('/api/consult',json={'message':'Plan a 20 day trip, 13 in Cairo and 7 on Hurghada beaches'})
    assert response.status_code == 200, response.text
    days = response.json()['itinerary']['days']
    assert len(days) == 20
    assert all(day['stops'] or day.get('activity_ideas') for day in days if not day.get('travel'))
    assert any(day.get('activity_ideas') for day in days)
