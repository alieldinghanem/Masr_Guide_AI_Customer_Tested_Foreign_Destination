"""Editorial CMS, vetted partner offers and privacy-minimal referral analytics.

No checkout, reservation guarantee, commission calculation, or partner approval is implied.
Staff endpoints require an independently configured server-side ADMIN_API_TOKEN.
"""
import hmac
import ipaddress
import os
import re
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4
from urllib.parse import urlsplit

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator

from . import accounts
from .catalog_extra import CITY_AR
from .database import get_place

router = APIRouter(prefix='/api', tags=['editorial-and-partners'])


def stamp():
    return datetime.now(timezone.utc).isoformat()


def require_staff(x_admin_key: str | None = Header(None)):
    token = os.getenv('ADMIN_API_TOKEN', '').strip()
    if len(token) < 24:
        raise HTTPException(503, 'Staff console not configured')
    if not x_admin_key or not hmac.compare_digest(x_admin_key, token):
        raise HTTPException(403, 'Staff credential required')


def setup():
    with accounts._open() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS editorial_articles (
              id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
              summary TEXT NOT NULL, body TEXT NOT NULL, category TEXT NOT NULL,
              source_url TEXT, published INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS partner_offers (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, city TEXT NOT NULL,
              description TEXT NOT NULL, partner TEXT NOT NULL,
              target_url TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0,
              disclosure TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS affiliate_clicks (
              id TEXT PRIMARY KEY, offer_id TEXT NOT NULL,
              clicked_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS affiliate_clicks_offer_idx ON affiliate_clicks (offer_id);
            CREATE TABLE IF NOT EXISTS itinerary_offer_placements (
              offer_id TEXT PRIMARY KEY REFERENCES partner_offers(id) ON DELETE CASCADE,
              place_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS itinerary_offer_clicks (
              click_id TEXT PRIMARY KEY REFERENCES affiliate_clicks(id),
              offer_id TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS itinerary_offer_clicks_offer_idx
              ON itinerary_offer_clicks (offer_id);
        ''')
        count = c.execute('SELECT COUNT(*) FROM editorial_articles').fetchone()[0]
        if count == 0:
            samples = [
                ('first-time-egypt', 'First time in Egypt', 'Start with culture, geography and realistic travel times.', 'A thoughtful Egypt trip balances ancient landmarks with modern city life, the Nile and coastal escapes. Plan transfers with extra time, check official opening hours before visiting, and choose experiences based on your pace. Ask your accommodation about locally suitable transportation.', 'Planning', 'https://egymonuments.gov.eg/'),
                ('cairo-highlights', 'Cairo beyond the pyramids', 'The capital offers museums, heritage districts and local food.', 'Explore Cairo in layers: museums and historic architecture, cultural neighbourhoods, and Egyptian cuisine. The Giza plateau is outside central Cairo, so group nearby sites and leave space for traffic. Opening times and tickets can change; consult official attraction websites.', 'Destinations', 'https://egymonuments.gov.eg/'),
                ('red-sea-guide', 'Explore Egypt’s Red Sea', 'Coastal destinations for diving, snorkelling and relaxing.', 'Hurghada, Sharm El Sheikh and Marsa Alam offer different styles of coastal travel. Research licensed operators for water activities, observe reef protection rules, and check sea conditions with local professionals before excursions.', 'Experiences', None),
                ('luxor-aswan', 'Luxor and Aswan', 'A starting point for planning a journey through Upper Egypt.', 'Luxor offers major archaeological sites on both sides of the Nile; Aswan offers river scenery and historic monuments. Factor in longer transfers, summer heat, breaks and realistic visits. Use official tourism and monument sources for practical information.', 'Destinations', 'https://egymonuments.gov.eg/'),
            ]
            for slug, title, summary, body, category, source in samples:
                c.execute('''INSERT INTO editorial_articles VALUES (?,?,?,?,?,?,?,?,?,?)''',
                          (uuid4().hex, slug, title, summary, body, category, source, 1, stamp(), stamp()))


class ArticleIn(BaseModel):
    slug: str = Field(min_length=3, max_length=90)
    title: str = Field(min_length=3, max_length=140)
    summary: str = Field(min_length=12, max_length=360)
    body: str = Field(min_length=30, max_length=15000)
    category: str = Field(default='Travel Guide', min_length=2, max_length=50)
    source_url: str | None = Field(default=None, max_length=500)
    published: bool = False

    @field_validator('slug')
    @classmethod
    def slug_format(cls, v):
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', v):
            raise ValueError('Use lowercase slug with hyphens')
        return v

    @field_validator('source_url')
    @classmethod
    def source_format(cls, v):
        if v and (urlsplit(v).scheme != 'https' or not urlsplit(v).hostname):
            raise ValueError('Use a valid https URL')
        return v


class OfferIn(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    city: str = Field(min_length=2, max_length=90)
    description: str = Field(min_length=12, max_length=800)
    partner: str = Field(min_length=2, max_length=140)
    target_url: str = Field(min_length=12, max_length=800)
    disclosure: str = Field(default='External partner. Booking is handled by the provider.', min_length=10, max_length=350)
    enabled: bool = False
    itinerary_place_id: str | None = Field(default=None, pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', max_length=90)

    @field_validator('target_url')
    @classmethod
    def safe_url(cls, v):
        split = urlsplit(v)
        if split.scheme != 'https' or not split.hostname or split.username or split.password:
            raise ValueError('A direct HTTPS partner URL is required')
        host = split.hostname.lower().rstrip('.')
        if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host:
            raise ValueError('A public partner hostname is required')
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError('Partner URL must use a public DNS hostname, not an IP address')
        return v


@router.get('/content/articles')
def articles():
    with accounts._open() as c:
        rows = c.execute('''SELECT id,slug,title,summary,body,category,source_url,updated_at
                            FROM editorial_articles WHERE published=1 ORDER BY created_at''').fetchall()
    return {'articles': [dict(row) for row in rows]}


@router.get('/partner-offers')
def offers(itinerary_only: bool = False):
    with accounts._open() as c:
        rows = c.execute('''SELECT o.id,o.title,o.city,o.description,o.partner,o.disclosure,p.place_id AS itinerary_place_id
                            FROM partner_offers o
                            LEFT JOIN itinerary_offer_placements p ON p.offer_id=o.id
                            LEFT JOIN pilot_contracts a ON a.offer_id=o.id
                            WHERE o.enabled=1 AND (?=0 OR p.place_id IS NOT NULL)
                              AND (a.id IS NULL OR (a.expires_at>? AND a.partner=o.partner AND a.target_url=o.target_url))
                            ORDER BY o.created_at DESC, o.id''', (int(itinerary_only), stamp())).fetchall()
    return {'offers': [dict(row) for row in rows]}


@router.get('/go/{offer_id}')
def go_offer(offer_id: str, from_itinerary: bool = False):
    """Redirect only to enabled offers. Record counts without IP or personal identifiers."""
    with accounts._open() as c:
        row = c.execute('''SELECT o.target_url,p.place_id FROM partner_offers o
                          LEFT JOIN itinerary_offer_placements p ON p.offer_id=o.id
                          WHERE o.id=? AND o.enabled=1''', (offer_id,)).fetchone()
        if not row or (from_itinerary and not row['place_id']):
            raise HTTPException(404, 'Offer not available')
        from .partner_pilot import attributed_url
        target = attributed_url(c, offer_id, row['target_url'])
        click_id = uuid4().hex
        c.execute('INSERT INTO affiliate_clicks VALUES (?,?,?)', (click_id, offer_id, stamp()))
        if from_itinerary:
            c.execute('INSERT INTO itinerary_offer_clicks VALUES (?,?)', (click_id, offer_id))
    return RedirectResponse(target, status_code=302, headers={'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store'})


@router.get('/admin/overview', dependencies=[])
def overview(x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as c:
        counts = {table: c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in (
            'account_users', 'account_trips', 'editorial_articles', 'partner_offers', 'partner_interest', 'affiliate_clicks')}
    return {'counts': counts, 'note': 'Outbound clicks are not bookings or earned commissions.'}


@router.get('/admin/articles')
def staff_articles(x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as c:
        rows = c.execute('SELECT * FROM editorial_articles ORDER BY updated_at DESC').fetchall()
    return {'articles': [dict(row) for row in rows]}


@router.post('/admin/articles', status_code=201)
def create_article(body: ArticleIn, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    ident = uuid4().hex
    with accounts._open() as c:
        try:
            c.execute('INSERT INTO editorial_articles VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (ident, body.slug, body.title, body.summary, body.body, body.category,
                       body.source_url, int(body.published), stamp(), stamp()))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, 'Article slug already exists') from exc
    return {'id': ident}


@router.put('/admin/articles/{article_id}')
def update_article(article_id: str, body: ArticleIn, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as c:
        try:
            r = c.execute('''UPDATE editorial_articles SET slug=?,title=?,summary=?,body=?,category=?,
                          source_url=?,published=?,updated_at=? WHERE id=?''',
                          (body.slug, body.title, body.summary, body.body, body.category,
                           body.source_url, int(body.published), stamp(), article_id))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, 'Article slug already exists') from exc
        if r.rowcount == 0:
            raise HTTPException(404, 'Article not found')
    return {'ok': True}


@router.delete('/admin/articles/{article_id}')
def remove_article(article_id: str, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as c:
        r = c.execute('DELETE FROM editorial_articles WHERE id=?', (article_id,))
        if r.rowcount == 0:
            raise HTTPException(404, 'Article not found')
    return {'ok': True}


@router.get('/admin/offers')
def staff_offers(x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as c:
        rows = c.execute('''SELECT o.*,p.place_id AS itinerary_place_id,
                            (SELECT COUNT(*) FROM affiliate_clicks c WHERE c.offer_id=o.id) AS outbound_clicks,
                            (SELECT COUNT(*) FROM itinerary_offer_clicks c WHERE c.offer_id=o.id) AS itinerary_clicks
                            FROM partner_offers o LEFT JOIN itinerary_offer_placements p ON p.offer_id=o.id
                            ORDER BY o.updated_at DESC''').fetchall()
    return {'offers': [dict(row) for row in rows]}


def validate_placement(body: OfferIn):
    if body.itinerary_place_id is None:
        return
    place = get_place(body.itinerary_place_id)
    if not place:
        raise HTTPException(422, 'Select an attraction from the guide catalogue')
    city = place['city']
    if body.city.strip().casefold() not in (city.casefold(), CITY_AR.get(city, city).casefold()):
        raise HTTPException(422, 'The offer and the selected attraction must be in the same city')


def save_placement(c, offer_id, place_id):
    if place_id is None:
        c.execute('DELETE FROM itinerary_offer_placements WHERE offer_id=?', (offer_id,))
        return
    c.execute('''INSERT INTO itinerary_offer_placements VALUES (?,?)
                 ON CONFLICT (offer_id) DO UPDATE SET place_id=excluded.place_id''', (offer_id, place_id))


@router.post('/admin/offers', status_code=201)
def create_offer(body: OfferIn, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    validate_placement(body)
    ident = uuid4().hex
    with accounts._open() as c:
        c.execute('INSERT INTO partner_offers VALUES (?,?,?,?,?,?,?,?,?,?)',
                  (ident, body.title, body.city, body.description, body.partner, body.target_url,
                   int(body.enabled), body.disclosure, stamp(), stamp()))
        save_placement(c, ident, body.itinerary_place_id)
    return {'id': ident}


@router.put('/admin/offers/{offer_id}')
def update_offer(offer_id: str, body: OfferIn, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    validate_placement(body)
    with accounts._open() as c:
        r = c.execute('''UPDATE partner_offers SET title=?,city=?,description=?,partner=?,
                         target_url=?,enabled=?,disclosure=?,updated_at=? WHERE id=?''',
                      (body.title, body.city, body.description, body.partner, body.target_url,
                       int(body.enabled), body.disclosure, stamp(), offer_id))
        if r.rowcount == 0:
            raise HTTPException(404, 'Offer not found')
        save_placement(c, offer_id, body.itinerary_place_id)
    return {'ok': True}


@router.delete('/admin/offers/{offer_id}')
def remove_offer(offer_id: str, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as c:
        r = c.execute('DELETE FROM partner_offers WHERE id=?', (offer_id,))
        if r.rowcount == 0:
            raise HTTPException(404, 'Offer not found')
    return {'ok': True}


@router.get('/admin/partner-applications')
def applications(x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as c:
        rows = c.execute('SELECT * FROM partner_interest ORDER BY created_at DESC').fetchall()
    return {'applications': [dict(row) for row in rows]}


class ApplicationReview(BaseModel):
    status: str = Field(pattern='^(new|reviewing|contacted|rejected)$')


@router.put('/admin/partner-applications/{application_id}')
def update_application(application_id: str, body: ApplicationReview, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as c:
        r = c.execute('UPDATE partner_interest SET status=? WHERE id=?', (body.status, application_id))
        if r.rowcount == 0:
            raise HTTPException(404, 'Application not found')
    return {'ok': True}
