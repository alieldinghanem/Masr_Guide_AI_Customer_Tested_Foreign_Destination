from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app import accounts
from app.main import app


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'pilot.sqlite3')
    monkeypatch.setenv('ADMIN_API_TOKEN', 'pilot-test-credential-not-for-live-use')
    headers = {'X-Admin-Key': 'pilot-test-credential-not-for-live-use'}
    with TestClient(app) as client:
        yield client, headers


def offer(client, headers, enabled=True):
    response = client.post('/api/admin/offers', headers=headers, json={
        'title': 'Test museum experience', 'city': 'Cairo',
        'description': 'Synthetic museum offer for testing only.',
        'partner': 'Test venue', 'target_url': 'https://example.com/tickets?keep=1&masr_ref=old#entry',
        'disclosure': 'We may earn a commission. Payment and booking are with the provider.',
        'enabled': enabled})
    assert response.status_code == 201
    return response.json()['id']


def contract(client, headers, offer_id, **changes):
    data = {'offer_id': offer_id, 'agreement_reference': 'signed-test-agreement',
            'currency': 'EGP', 'commission_bps': 1000,
            'expires_at': (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
            'agreement_confirmed': True, **changes}
    return client.post('/api/admin/pilot/contracts', headers=headers, json=data)


def test_full_referral_fulfilment_and_reversal(pilot):
    client, headers = pilot
    ident = offer(client, headers)
    # Existing non-contracted outbound URLs remain unchanged.
    plain = client.get('/api/go/' + ident, follow_redirects=False)
    assert 'masr_ref=old' in plain.headers['location']
    agreement = contract(client, headers, ident).json()['id']
    link = client.get('/api/go/' + ident, follow_redirects=False)
    query = parse_qs(urlsplit(link.headers['location']).query)
    assert query['keep'] == ['1']
    assert len(query['masr_ref']) == 1 and query['masr_ref'] != ['old']
    assert urlsplit(link.headers['location']).fragment == 'entry'
    before = client.get('/api/admin/pilot/report', headers=headers).json()['agreements'][0]
    assert before['referrals'] == 1 and before['commission_minor'] == 0
    body = {'contract_id': agreement, 'referral_id': query['masr_ref'][0],
            'external_booking_id': 'VENUE-001', 'eligible_amount_minor': 10005,
            'evidence_reference': 'partner-statement-001', 'fulfilled_confirmed': True}
    assert client.post('/api/admin/pilot/bookings', headers=headers,
                       json={**body, 'fulfilled_confirmed': False}).status_code == 422
    booking = client.post('/api/admin/pilot/bookings', headers=headers, json=body)
    assert booking.status_code == 201, booking.text
    assert booking.json()['commission_minor'] == 1001
    assert client.post('/api/admin/pilot/bookings', headers=headers, json=body).status_code == 409
    other_ref = parse_qs(urlsplit(client.get('/api/go/' + ident, follow_redirects=False).headers['location']).query)['masr_ref'][0]
    assert client.post('/api/admin/pilot/bookings', headers=headers,
                       json={**body, 'referral_id': other_ref}).status_code == 409
    report = client.get('/api/admin/pilot/report', headers=headers).json()['agreements'][0]
    assert report['commission_minor'] == 1001 and report['confirmed_bookings'] == 1
    path = '/api/admin/pilot/bookings/' + booking.json()['id'] + '/reverse'
    assert client.post(path, headers=headers, json={'evidence_reference': 'full-refund-001'}).status_code == 200
    assert client.post(path, headers=headers, json={'evidence_reference': 'duplicate'}).status_code == 409
    report = client.get('/api/admin/pilot/report', headers=headers).json()['agreements'][0]
    assert report['commission_minor'] == 0 and report['reversed_bookings'] == 1
    with accounts._open() as c:
        assert c.execute('SELECT commission_minor FROM pilot_bookings').fetchone()[0] == 1001


def test_staff_and_contract_guards(pilot):
    client, headers = pilot
    ident = offer(client, headers)
    assert client.get('/api/admin/pilot/report').status_code == 403
    assert client.post('/api/admin/pilot/contracts', json={}).status_code in (403, 422)
    assert contract(client, headers, ident, agreement_confirmed=False).status_code == 422
    assert contract(client, headers, ident, expires_at='2020-01-01T00:00:00Z').status_code == 422
    assert contract(client, headers, ident, commission_bps=True).status_code == 422
    assert contract(client, headers, ident, currency='JPY').status_code == 422
    assert contract(client, headers, 'missing').status_code == 404
    assert contract(client, headers, ident).status_code == 201
    assert contract(client, headers, ident).status_code == 409
    assert client.post('/api/admin/pilot/bookings', headers=headers, json={
        'contract_id': 'another-contract', 'referral_id': 'invented',
        'external_booking_id': 'fake', 'eligible_amount_minor': 100,
        'evidence_reference': 'statement', 'fulfilled_confirmed': True}).status_code == 404
    with accounts._open() as c:
        c.execute("UPDATE partner_offers SET target_url='https://example.com/changed' WHERE id=?", (ident,))
    assert client.get('/api/go/' + ident, follow_redirects=False).status_code == 409


def test_disabled_and_expired_offers_do_not_create_referrals(pilot):
    client, headers = pilot
    ident = offer(client, headers, enabled=False)
    contract(client, headers, ident)
    assert client.get('/api/go/' + ident, follow_redirects=False).status_code == 404
    with accounts._open() as c:
        c.execute('UPDATE partner_offers SET enabled=1 WHERE id=?', (ident,))
        c.execute("UPDATE pilot_contracts SET expires_at='2020-01-01T00:00:00+00:00'")
    assert client.get('/api/go/' + ident, follow_redirects=False).status_code == 409
    assert client.get('/api/admin/pilot/report', headers=headers).json()['agreements'][0]['referrals'] == 0


def test_itinerary_offer_publication_and_click_attribution(pilot):
    client, headers = pilot
    target = 'https://example.com/experience?campaign=masr-family#book'
    draft = {
        'title': 'Synthetic Giza tour', 'city': 'Giza', 'partner': 'Test agency',
        'description': 'A synthetic listing for the itinerary workflow.',
        'target_url': target, 'itinerary_place_id': 'giza-pyramids', 'enabled': False,
    }
    def create(**changes):
        return client.post('/api/admin/offers', headers=headers, json={**draft, **changes})

    assert create(city='Luxor').status_code == 422
    assert create(itinerary_place_id='missing-attraction').status_code == 422
    assert create(itinerary_place_id='').status_code == 422
    created = create()
    assert created.status_code == 201, created.text
    ident = created.json()['id']
    unplaced = create(itinerary_place_id=None, enabled=True).json()['id']
    day_offers = '/api/partner-offers?itinerary_only=true'
    route = f'/api/go/{ident}'
    admin_route = f'/api/admin/offers/{ident}'

    assert client.get(day_offers).json()['offers'] == []
    assert client.get(route + '?from_itinerary=true', follow_redirects=False).status_code == 404
    assert client.get(f'/api/go/{unplaced}?from_itinerary=true', follow_redirects=False).status_code == 404
    assert client.put(admin_route, headers=headers, json={**draft, 'enabled': True}).status_code == 200
    [public] = client.get(day_offers).json()['offers']
    assert public['itinerary_place_id'] == 'giza-pyramids'
    assert public['id'] == ident and 'target_url' not in public
    for path in (route, route + '?from_itinerary=true'):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['location'] == target
    row = next(o for o in client.get('/api/admin/offers', headers=headers).json()['offers'] if o['id'] == ident)
    assert (row['outbound_clicks'], row['itinerary_clicks']) == (2, 1)

    assert contract(client, headers, ident).status_code == 201
    assert client.put(admin_route, headers=headers, json={
        **draft, 'enabled': True, 'target_url': 'https://example.com/replacement',
    }).status_code == 200
    assert client.get(day_offers).json()['offers'] == []
    assert client.get(route + '?from_itinerary=true', follow_redirects=False).status_code == 409
    assert client.put(admin_route, headers=headers, json={
        **draft, 'enabled': True, 'itinerary_place_id': None,
    }).status_code == 200
    assert client.get(route + '?from_itinerary=true', follow_redirects=False).status_code == 404
