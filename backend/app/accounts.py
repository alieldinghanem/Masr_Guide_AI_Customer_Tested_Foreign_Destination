"""SQLite-backed first-party accounts and saved trips for MVP (not a booking/payment processor)."""
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr, Field, ValidationError

from .schemas import TripState
from .database import get_place
from .conversation_router import payment_sensitive
from .durable_storage import configured as postgres_configured, connect_traveler

router = APIRouter(prefix='/api', tags=['traveler-account'])
# None means resolve configured storage lazily (after backend/.env is loaded).
# Tests may still inject an isolated Path through _DB.
_DB: Path | None = None


def _db_path() -> Path:
    return _DB if _DB is not None else Path(os.getenv('MASR_USER_DB', str(Path(__file__).resolve().parents[1] / 'data' / 'traveler.sqlite3')))


@contextmanager
def _open():
    """One transaction per operation; always release its connection."""
    if _DB is None and postgres_configured():
        conn = connect_traveler()
        try:
            with conn:
                yield conn
        finally:
            conn.close()
        return
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=10000')
        with conn:
            yield conn
    finally:
        conn.close()


def setup():
    with _open() as c:
        c.executescript('''
          CREATE TABLE IF NOT EXISTS account_users (
            id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            salt TEXT NOT NULL, created_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS account_identities (
            provider TEXT NOT NULL, subject TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            PRIMARY KEY (provider, subject),
            UNIQUE (provider, user_id));
          CREATE INDEX IF NOT EXISTS idx_account_identity_owner ON account_identities(user_id);
          CREATE TABLE IF NOT EXISTS account_tokens (
            token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS account_trips (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
            title TEXT NOT NULL, itinerary TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS account_conversations (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
            title TEXT NOT NULL, messages_json TEXT NOT NULL,
            trip_state_json TEXT, itinerary_json TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
          CREATE INDEX IF NOT EXISTS idx_conv_owner_updated ON account_conversations(user_id,updated_at);
          CREATE TABLE IF NOT EXISTS account_favorites (
            user_id TEXT NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
            place_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, place_id));
          CREATE TABLE IF NOT EXISTS partner_interest (
            id TEXT PRIMARY KEY, company TEXT NOT NULL, email TEXT NOT NULL, website TEXT,
            city TEXT, description TEXT, created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new');
        ''')


def _now():
    return datetime.now(timezone.utc)


def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310000).hex()


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)


class GoogleCredential(BaseModel):
    # The signed Google Identity Services ID token, never a Gmail password.
    credential: str = Field(min_length=50, max_length=8192)


class TripSave(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    itinerary: dict


class ConversationTurn(BaseModel):
    role: str = Field(pattern='^(user|assistant)$')
    text: str = Field(min_length=1, max_length=1500)


class ConversationSave(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    messages: list[ConversationTurn] = Field(min_length=1, max_length=100)
    trip_state: dict | None = None
    itinerary: dict | None = None


def _validate_saved_itinerary(plan: dict) -> str:
    """Prevent corrupt/hostile imported itinerary documents from being saved.

    Empty days remain a valid editable draft for backwards compatibility. Full
    generated trips must have unique, contiguous positive day numbers.
    """
    try:
        raw = json.dumps(plan, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, detail='Itinerary contains invalid numeric or object values') from exc
    days = plan.get('days')
    if len(raw) > 150000 or not isinstance(days, list) or len(days) > 30:
        raise HTTPException(422, detail='Invalid or oversized itinerary')
    seen = set()
    # Persist travel requirements as part of the saved plan, with a strict
    # boolean type so a malformed imported trip cannot misrepresent them.
    if 'accessibility_needs' in plan and type(plan['accessibility_needs']) is not bool:
        raise HTTPException(422, detail='Invalid accessibility requirement flag')
    if isinstance(plan.get('total_places'), bool) or (
        'total_places' in plan and (not isinstance(plan['total_places'], int) or plan['total_places'] < 0)
    ):
        raise HTTPException(422, detail='Invalid itinerary place count')
    for idx, day in enumerate(days, start=1):
        if not isinstance(day, dict) or not isinstance(day.get('day'), int) or isinstance(day.get('day'), bool):
            raise HTTPException(422, detail='Itinerary days require a valid day number')
        if day['day'] != idx or day['day'] in seen:
            raise HTTPException(422, detail='Itinerary days must be consecutive and unique')
        seen.add(day['day'])
        city = day.get('city')
        if not isinstance(city, str) or not 1 <= len(city.strip()) <= 100:
            raise HTTPException(422, detail='Each itinerary day must have a city')
        if 'activity_ideas' in day and (
            not isinstance(day['activity_ideas'], list)
            or len(day['activity_ideas']) > 25
            or any(not isinstance(v, str) or len(v) > 400 for v in day['activity_ideas'])
        ):
            raise HTTPException(422, detail='Malformed activity ideas')
        if day.get('travel') is not None:
            travel = day['travel']
            if (not isinstance(travel, dict) or not isinstance(travel.get('from_city'), str)
                    or not travel['from_city'].strip() or type(travel.get('minutes')) not in (int, float)
                    or not math.isfinite(travel['minutes']) or travel['minutes'] < 0):
                raise HTTPException(422, detail='Malformed travel details')
        stops = day.get('stops')
        if not isinstance(stops, list) or len(stops) > 25:
            raise HTTPException(422, detail='Too many or malformed stops on one day')
        for stop in stops:
            if not isinstance(stop, dict) or not isinstance(stop.get('place'), dict):
                raise HTTPException(422, detail='Every stop must contain a valid place')
            place = stop['place']
            if not all(isinstance(place.get(key), str) and 1 <= len(place[key].strip()) <= 160
                       for key in ('id', 'name')):
                raise HTTPException(422, detail='Every stop needs a place ID and name')
    return raw


def _validated_trip_state(state: dict | None) -> tuple[str | None, TripState | None]:
    if state is None:
        return None, None
    try:
        validated = TripState.model_validate(state)
        raw = json.dumps(validated.model_dump(), ensure_ascii=False, allow_nan=False)
    except (ValidationError, TypeError, ValueError, RecursionError) as exc:
        raise HTTPException(422, detail='Invalid saved trip constraints') from exc
    return raw, validated


def _check_phase_allocation(state: TripState, plan: dict):
    """A 13 Cairo + 7 Hurghada constraint must not save as a 14/6 itinerary.

    Checking only total days was insufficient: a malformed yet well-shaped AI
    response could previously overwrite the correctly stated traveler intent.
    """
    days = plan['days']
    if len(days) != state.days:
        raise HTTPException(422, detail='Itinerary day count conflicts with trip constraints')
    offset = 0
    for phase in state.phases:
        segment = days[offset:offset + phase.days]
        if (len(segment) != phase.days
                or any(day['city'] not in phase.cities or
                       ('phase_kind' in day and day['phase_kind'] != phase.kind)
                       for day in segment)
                or any(not any(day['city'] == city for day in segment) for city in phase.cities)):
            raise HTTPException(422, detail='Itinerary destinations conflict with trip constraints')
        offset += phase.days


def _conversation_payload(body: ConversationSave):
    # Chat data are not a payment processor; never persist unmasked card input
    # even if a caller bypasses the browser-side guard.
    from .conversation_router import redact_payment_data
    if any(redact_payment_data(text) != text for text in
           [body.title] + [turn.text for turn in body.messages]):
        raise HTTPException(422, detail='Do not save payment card numbers or security codes in chat')
    raw_messages = json.dumps([x.model_dump() for x in body.messages], ensure_ascii=False)
    trip, trip_state = _validated_trip_state(body.trip_state)
    # A saved conversation can contain dialogue without a plan. If both the
    # constraints and itinerary are present, their allocations must agree.
    plan = _validate_saved_itinerary(body.itinerary) if body.itinerary is not None else None
    if trip_state is not None and body.itinerary is not None:
        _check_phase_allocation(trip_state, body.itinerary)
    if sum(len(x or '') for x in (raw_messages, trip, plan)) > 150000:
        raise HTTPException(422, detail='Conversation exceeds maximum size')
    return raw_messages, trip, plan


class AccountDeletion(BaseModel):
    password: str | None = Field(default=None, min_length=12, max_length=128)
    google_credential: str | None = Field(default=None, min_length=50, max_length=8192)
    confirmation: str = Field(pattern=r'^DELETE MY ACCOUNT


def _strict_writes() -> bool:
    return os.getenv('APP_ENV', '').lower() == 'production' or os.getenv('REQUIRE_CONDITIONAL_WRITES', '').lower() in ('1', 'true', 'yes')


class PartnerInterest(BaseModel):
    company: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    website: str | None = Field(default=None, max_length=250)
    city: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


def _validate_email(value):
    value = value.strip().lower()
    # Restrict this MVP login identifier to ordinary email addresses. Avoid
    # ambiguous Unicode/control characters that enable account spoofing.
    pattern = r'[a-z0-9][a-z0-9._%+\-]{0,63}@[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?)+'
    if len(value) > 254 or not re.fullmatch(pattern, value, flags=re.ASCII):
        raise HTTPException(422, 'Enter a valid email address')
    return value


def _issue(c, user_id):
    token = secrets.token_urlsafe(40)
    expiry = _now() + timedelta(days=7)
    c.execute('INSERT INTO account_tokens VALUES (?,?,?)',
              (hashlib.sha256(token.encode()).hexdigest(), user_id, expiry.isoformat()))
    return {'token': token, 'token_type': 'bearer', 'expires_at': expiry.isoformat()}


def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, detail='Sign in first', headers={'WWW-Authenticate': 'Bearer'})
    token = authorization[7:].strip()
    if len(token) < 35:
        raise HTTPException(401, detail='Invalid session')
    digest = hashlib.sha256(token.encode()).hexdigest()
    with _open() as c:
        row = c.execute('''SELECT u.id, u.email, t.expires_at FROM account_tokens t
                           JOIN account_users u ON u.id=t.user_id WHERE t.token_hash=?''', (digest,)).fetchone()
    if not row or datetime.fromisoformat(row['expires_at']) <= _now():
        raise HTTPException(401, detail='Session expired or invalid')
    return {'id': row['id'], 'email': row['email'], 'token_hash': digest}


def _verify_google_credential(credential: str) -> tuple[str, str]:
    """Validate signed GIS token (signature, expiration, audience, issuer, verified email)."""
    client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    if not client_id:
        raise HTTPException(503, detail='Google sign-in is not configured')
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
        claims = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
    except (ValueError, Exception) as exc:
        # Never expose the Google credential or verification exception to clients/logs.
        raise HTTPException(401, detail='Google sign-in token is invalid or expired') from None
    if (claims.get('iss') not in ('accounts.google.com', 'https://accounts.google.com')
            or claims.get('email_verified') is not True
            or not isinstance(claims.get('sub'), str)
            or not 1 <= len(claims['sub']) <= 255
            or not isinstance(claims.get('email'), str)):
        raise HTTPException(401, detail='Google account identity is not verified')
    return _validate_email(claims['email']), claims['sub']


def _google_linked(c, uid: str) -> bool:
    return c.execute('SELECT 1 FROM account_identities WHERE provider=? AND user_id=?',
                     ('google', uid)).fetchone() is not None


def registration_enabled() -> bool:
    # Render previews can be deployed without the Blueprint's APP_ENV setting.
    # Require a durability declaration before accepting new accounts on Render
    # or a portfolio preview. Local development remains usable.
    public_preview = (os.getenv('APP_ENV', '').lower() == 'portfolio' or
                      os.getenv('RENDER', '').lower() == 'true')
    durable = os.getenv('MASR_DURABLE_STORAGE_CONFIRMED', '').lower() in ('1', 'true', 'yes')
    return not public_preview or durable


@router.get('/auth/google/config')
def google_auth_config():
    # OAuth client IDs are public; this endpoint never returns API keys or secrets.
    return {'client_id': os.getenv('GOOGLE_CLIENT_ID', '').strip(),
            'registration_enabled': registration_enabled()}


@router.post('/auth/google')
def google_sign_in(body: GoogleCredential):
    email, subject = _verify_google_credential(body.credential)
    setup()
    try:
        with _open() as c:
            identity = c.execute(
                'SELECT u.id,u.email FROM account_identities i '
                'JOIN account_users u ON u.id=i.user_id WHERE i.provider=? AND i.subject=?',
                ('google', subject)).fetchone()
            if identity:
                return {'user': {'id': identity['id'], 'email': identity['email'], 'google_linked': True},
                        **_issue(c, identity['id'])}
            if not registration_enabled():
                raise HTTPException(503, detail='New accounts require durable storage on this preview')
            if c.execute('SELECT id FROM account_users WHERE email=?', (email,)).fetchone():
                raise HTTPException(409, detail='This email already has an account. Sign in with your password and link Google in My Account.')
            uid = uuid4().hex
            # Unusable random password verifier for Google-only accounts.
            c.execute('INSERT INTO account_users VALUES (?,?,?,?,?)',
                      (uid, email, secrets.token_hex(32), secrets.token_hex(16), _now().isoformat()))
            c.execute('INSERT INTO account_identities VALUES (?,?,?,?)',
                      ('google', subject, uid, _now().isoformat()))
            return {'user': {'id': uid, 'email': email, 'google_linked': True}, **_issue(c, uid)}
    except sqlite3.IntegrityError:
        raise HTTPException(409, detail='The Google identity or email is already linked to an account')


@router.post('/auth/google/link')
def link_google(body: GoogleCredential, user=Depends(current_user)):
    email, subject = _verify_google_credential(body.credential)
    if email != user['email']:
        raise HTTPException(409, detail='Sign in to Google with the same verified email as your account')
    setup()
    try:
        with _open() as c:
            existing = c.execute('SELECT user_id FROM account_identities WHERE provider=? AND subject=?',
                                 ('google', subject)).fetchone()
            if existing and existing['user_id'] != user['id']:
                raise HTTPException(409, detail='This Google identity belongs to another account')
            linked = c.execute('SELECT subject FROM account_identities WHERE provider=? AND user_id=?',
                               ('google', user['id'])).fetchone()
            if linked and linked['subject'] != subject:
                raise HTTPException(409, detail='This account is already linked to another Google identity')
            if not linked:
                c.execute('INSERT INTO account_identities VALUES (?,?,?,?)',
                          ('google', subject, user['id'], _now().isoformat()))
    except sqlite3.IntegrityError:
        raise HTTPException(409, detail='This Google identity is already linked')
    return {'linked': True}


@router.post('/auth/register', status_code=201)
def register(body: Credentials):
    if not registration_enabled():
        raise HTTPException(503, detail='Account registration is unavailable on temporary-storage previews')
    setup()
    email = _validate_email(body.email)
    salt = secrets.token_hex(16)
    uid = uuid4().hex
    try:
        with _open() as c:
            c.execute('INSERT INTO account_users VALUES (?,?,?,?,?)',
                      (uid, email, _hash_password(body.password, salt), salt, _now().isoformat()))
            credential = _issue(c, uid)
    except sqlite3.IntegrityError:
        raise HTTPException(409, detail='Account already exists')
    return {'user': {'id': uid, 'email': email}, **credential}


@router.post('/auth/login')
def login(body: Credentials):
    email = _validate_email(body.email)
    with _open() as c:
        row = c.execute('SELECT * FROM account_users WHERE email=?', (email,)).fetchone()
        if not row or not hmac.compare_digest(row['password_hash'], _hash_password(body.password, row['salt'])):
            raise HTTPException(401, detail='Incorrect email or password')
        return {'user': {'id': row['id'], 'email': email}, **_issue(c, row['id'])}


@router.get('/auth/me')
def me(user=Depends(current_user)):
    with _open() as c:
        google_linked = _google_linked(c, user['id'])
    return {'user': {'id': user['id'], 'email': user['email'], 'google_linked': google_linked}}


@router.post('/auth/logout')
def logout(user=Depends(current_user)):
    with _open() as c:
        c.execute('DELETE FROM account_tokens WHERE token_hash=?', (user['token_hash'],))
    return {'ok': True}


@router.delete('/my/account')
def delete_account(body: AccountDeletion, user=Depends(current_user)):
    """Permanently remove the authenticated account and all owned data.

    Requires current password and explicit confirmation; all sessions become invalid.
    Commercial partner enquiries are a separate record category, not linked to accounts.
    """
    with _open() as c:
        row = c.execute('SELECT password_hash,salt FROM account_users WHERE id=?',
                        (user['id'],)).fetchone()
        password_ok = bool(body.password and row and
                           hmac.compare_digest(row['password_hash'], _hash_password(body.password, row['salt'])))
        google_ok = False
        if body.google_credential:
            _, subject = _verify_google_credential(body.google_credential)
            google_ok = c.execute('SELECT 1 FROM account_identities WHERE provider=? AND user_id=? AND subject=?',
                                  ('google', user['id'], subject)).fetchone() is not None
        if not (password_ok or google_ok):
            raise HTTPException(403, detail='Confirm using your password or linked Google account')
        from .ratings import delete_account_reviews
        delete_account_reviews(user['id'])
        c.execute('DELETE FROM account_users WHERE id=?', (user['id'],))
    return {'deleted': True}


def _favorite_place_id(place_id: str) -> str:
    # Explicitly allow catalogue slugs, not arbitrary text or external links.
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', place_id) or len(place_id) > 90:
        raise HTTPException(422, detail='Invalid place identifier')
    return place_id


@router.get('/my/favorites')
def my_favorites(user=Depends(current_user)):
    """Cross-device favorite slugs owned by the authenticated traveler."""
    with _open() as c:
        rows = c.execute('SELECT place_id FROM account_favorites WHERE user_id=? ORDER BY created_at,place_id',
                         (user['id'],)).fetchall()
    return {'place_ids': [row['place_id'] for row in rows]}


@router.post('/my/favorites/{place_id}')
def add_favorite(place_id: str, user=Depends(current_user)):
    ident = _favorite_place_id(place_id)
    if get_place(ident) is None:
        raise HTTPException(404, detail='Place not found in the curated catalogue')
    with _open() as c:
        # Write-lock before the cap check; concurrent writes cannot exceed 500.
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT 1 FROM account_favorites WHERE user_id=? AND place_id=?',
                     (user['id'], ident)).fetchone():
            return {'saved': True, 'place_id': ident}
        count = c.execute('SELECT COUNT(*) FROM account_favorites WHERE user_id=?',
                          (user['id'],)).fetchone()[0]
        if count >= 500:
            raise HTTPException(422, detail='A maximum of 500 favorites can be stored')
        c.execute('INSERT INTO account_favorites (user_id,place_id,created_at) VALUES (?,?,?)',
                  (user['id'], ident, _now().isoformat()))
    return {'saved': True, 'place_id': ident}


@router.delete('/my/favorites/{place_id}')
def remove_favorite(place_id: str, user=Depends(current_user)):
    ident = _favorite_place_id(place_id)
    with _open() as c:
        c.execute('DELETE FROM account_favorites WHERE user_id=? AND place_id=?',
                  (user['id'], ident))
    # An idempotent delete supports safe client retries.
    return {'saved': False, 'place_id': ident}


@router.get('/my/export')
def export_account_data(user=Depends(current_user)):
    """Portable account export, limited to the authenticated traveler.

    Never include password hashes, session bearer tokens or unrelated partner
    inquiries. The API's sensitive-route middleware adds Cache-Control: no-store.
    """
    with _open() as c:
        profile = c.execute('SELECT email, created_at FROM account_users WHERE id=?',
                            (user['id'],)).fetchone()
        trips = c.execute('SELECT id,title,itinerary,created_at,updated_at FROM account_trips WHERE user_id=? ORDER BY created_at',
                          (user['id'],)).fetchall()
        conversations = c.execute('SELECT id,title,messages_json,trip_state_json,itinerary_json,created_at,updated_at FROM account_conversations WHERE user_id=? ORDER BY created_at',
                                  (user['id'],)).fetchall()
        favorites = c.execute('SELECT place_id,created_at FROM account_favorites WHERE user_id=? ORDER BY created_at,place_id',
                              (user['id'],)).fetchall()
    from .ratings import account_reviews
    return {
        'format': 'masr-guide-traveler-export-v1',
        'exported_at': _now().isoformat(),
        'profile': {'email': profile['email'], 'created_at': profile['created_at']},
        'favorites': [dict(row) for row in favorites],
        'visitor_reviews': account_reviews(user['id']),
        'trips': [dict(id=row['id'], title=row['title'], itinerary=json.loads(row['itinerary']),
                       created_at=row['created_at'], updated_at=row['updated_at']) for row in trips],
        'conversations': [dict(id=row['id'], title=row['title'],
                               messages=json.loads(row['messages_json']),
                               trip_state=json.loads(row['trip_state_json']) if row['trip_state_json'] else None,
                               itinerary=json.loads(row['itinerary_json']) if row['itinerary_json'] else None,
                               created_at=row['created_at'], updated_at=row['updated_at']) for row in conversations],
        'note': 'Partner enquiries made outside traveler accounts are not associated with this export.'
    }


@router.get('/my/trips')
def trips(user=Depends(current_user)):
    with _open() as c:
        rows = c.execute('SELECT id,title,created_at,updated_at FROM account_trips WHERE user_id=? ORDER BY updated_at DESC', (user['id'],)).fetchall()
    return {'trips': [dict(x) for x in rows]}


@router.post('/my/trips', status_code=201)
def save_trip(body: TripSave, user=Depends(current_user)):
    raw = _validate_saved_itinerary(body.itinerary)
    tid = uuid4().hex
    stamp = _now().isoformat()
    with _open() as c:
        c.execute('INSERT INTO account_trips VALUES (?,?,?,?,?,?)', (tid, user['id'], body.title, raw, stamp, stamp))
    return {'id': tid, 'title': body.title, 'created_at': stamp}


@router.get('/my/trips/{trip_id}')
def trip_detail(trip_id: str, user=Depends(current_user)):
    with _open() as c:
        row = c.execute('SELECT * FROM account_trips WHERE id=? AND user_id=?', (trip_id, user['id'])).fetchone()
    if not row:
        raise HTTPException(404, 'Trip not found')
    return {'id': row['id'], 'title': row['title'], 'itinerary': json.loads(row['itinerary']), 'updated_at': row['updated_at']}


@router.put('/my/trips/{trip_id}')
def edit_trip(trip_id: str, body: TripSave, if_match: str | None = Header(None), user=Depends(current_user)):
    if _strict_writes() and not if_match:
        raise HTTPException(428, detail='If-Match version required; reload before updating')
    raw = _validate_saved_itinerary(body.itinerary)
    with _open() as c:
        if if_match is not None:
            cur = c.execute('''UPDATE account_trips SET title=?, itinerary=?, updated_at=?
                WHERE id=? AND user_id=? AND updated_at=?''',
                (body.title, raw, _now().isoformat(), trip_id, user['id'], if_match))
        else:
            cur = c.execute('''UPDATE account_trips SET title=?, itinerary=?, updated_at=?
                WHERE id=? AND user_id=?''',
                (body.title, raw, _now().isoformat(), trip_id, user['id']))
        if cur.rowcount == 0:
            exists = c.execute('SELECT 1 FROM account_trips WHERE id=? AND user_id=?',
                               (trip_id, user['id'])).fetchone()
            raise HTTPException(409 if exists else 404,
                                'Trip changed; reload before saving' if exists else 'Trip not found')
    return {'ok': True}


@router.delete('/my/trips/{trip_id}')
def delete_trip(trip_id: str, user=Depends(current_user)):
    with _open() as c:
        cur = c.execute('DELETE FROM account_trips WHERE id=? AND user_id=?', (trip_id, user['id']))
    if cur.rowcount == 0:
        raise HTTPException(404, 'Trip not found')
    return {'ok': True}


@router.get('/my/conversations')
def conversation_list(user=Depends(current_user)):
    with _open() as c:
        rows = c.execute('SELECT id,title,created_at,updated_at FROM account_conversations WHERE user_id=? ORDER BY updated_at DESC LIMIT 50', (user['id'],)).fetchall()
    return {'conversations': [dict(row) for row in rows]}


@router.post('/my/conversations', status_code=201)
def conversation_create(body: ConversationSave, user=Depends(current_user)):
    messages, trip, plan = _conversation_payload(body)
    conversation_id, stamp = uuid4().hex, _now().isoformat()
    with _open() as c:
        c.execute('INSERT INTO account_conversations VALUES (?,?,?,?,?,?,?,?)',
                  (conversation_id, user['id'], body.title, messages, trip, plan, stamp, stamp))
    return {'id': conversation_id, 'updated_at': stamp}


@router.get('/my/conversations/{conversation_id}')
def conversation_get(conversation_id: str, user=Depends(current_user)):
    with _open() as c:
        row = c.execute('SELECT * FROM account_conversations WHERE id=? AND user_id=?',
                        (conversation_id, user['id'])).fetchone()
    if not row:
        raise HTTPException(404, detail='Conversation not found')
    return {'id': row['id'], 'title': row['title'], 'messages': json.loads(row['messages_json']),
            'trip_state': json.loads(row['trip_state_json']) if row['trip_state_json'] else None,
            'itinerary': json.loads(row['itinerary_json']) if row['itinerary_json'] else None,
            'updated_at': row['updated_at']}


@router.put('/my/conversations/{conversation_id}')
def conversation_update(conversation_id: str, body: ConversationSave, if_match: str | None = Header(None), user=Depends(current_user)):
    if _strict_writes() and not if_match:
        raise HTTPException(428, detail='If-Match version required; reload before updating')
    messages, trip, plan = _conversation_payload(body)
    stamp = _now().isoformat()
    with _open() as c:
        if if_match is None:
            result = c.execute('UPDATE account_conversations SET title=?, messages_json=?, trip_state_json=?, itinerary_json=?, updated_at=? WHERE id=? AND user_id=?',
                               (body.title, messages, trip, plan, stamp, conversation_id, user['id']))
        else:
            result = c.execute('UPDATE account_conversations SET title=?, messages_json=?, trip_state_json=?, itinerary_json=?, updated_at=? WHERE id=? AND user_id=? AND updated_at=?',
                               (body.title, messages, trip, plan, stamp, conversation_id, user['id'], if_match))
        if not result.rowcount:
            exists = c.execute('SELECT 1 FROM account_conversations WHERE id=? AND user_id=?',
                               (conversation_id, user['id'])).fetchone()
            raise HTTPException(409 if exists else 404,
                                'Conversation changed; reload before saving' if exists else 'Conversation not found')
    return {'ok': True, 'updated_at': stamp}


@router.delete('/my/conversations/{conversation_id}')
def conversation_delete(conversation_id: str, user=Depends(current_user)):
    with _open() as c:
        result = c.execute('DELETE FROM account_conversations WHERE id=? AND user_id=?',
                           (conversation_id, user['id']))
    if not result.rowcount:
        raise HTTPException(404, detail='Conversation not found')
    return {'ok': True}


@router.post('/partners/apply', status_code=201)
def partner_apply(body: PartnerInterest):
    """Interest intake only. No checkout, commission attribution or bookable inventory implied."""
    if not os.getenv('PARTNER_INQUIRIES_ENABLED', '').lower() in ('1', 'true'):
        raise HTTPException(503, 'Partner enquiries are currently closed')
    setup()
    pid = uuid4().hex
    with _open() as c:
        c.execute('INSERT INTO partner_interest (id,company,email,website,city,description,created_at) VALUES (?,?,?,?,?,?,?)',
                  (pid, body.company, _validate_email(body.email), body.website, body.city, body.description, _now().isoformat()))
    return {'received': True, 'reference': pid}
)


def _strict_writes() -> bool:
    return os.getenv('APP_ENV', '').lower() == 'production' or os.getenv('REQUIRE_CONDITIONAL_WRITES', '').lower() in ('1', 'true', 'yes')


class PartnerInterest(BaseModel):
    company: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    website: str | None = Field(default=None, max_length=250)
    city: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


def _validate_email(value):
    value = value.strip().lower()
    # Restrict this MVP login identifier to ordinary email addresses. Avoid
    # ambiguous Unicode/control characters that enable account spoofing.
    pattern = r'[a-z0-9][a-z0-9._%+\-]{0,63}@[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?)+'
    if len(value) > 254 or not re.fullmatch(pattern, value, flags=re.ASCII):
        raise HTTPException(422, 'Enter a valid email address')
    return value


def _issue(c, user_id):
    token = secrets.token_urlsafe(40)
    expiry = _now() + timedelta(days=7)
    c.execute('INSERT INTO account_tokens VALUES (?,?,?)',
              (hashlib.sha256(token.encode()).hexdigest(), user_id, expiry.isoformat()))
    return {'token': token, 'token_type': 'bearer', 'expires_at': expiry.isoformat()}


def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, detail='Sign in first', headers={'WWW-Authenticate': 'Bearer'})
    token = authorization[7:].strip()
    if len(token) < 35:
        raise HTTPException(401, detail='Invalid session')
    digest = hashlib.sha256(token.encode()).hexdigest()
    with _open() as c:
        row = c.execute('''SELECT u.id, u.email, t.expires_at FROM account_tokens t
                           JOIN account_users u ON u.id=t.user_id WHERE t.token_hash=?''', (digest,)).fetchone()
    if not row or datetime.fromisoformat(row['expires_at']) <= _now():
        raise HTTPException(401, detail='Session expired or invalid')
    return {'id': row['id'], 'email': row['email'], 'token_hash': digest}


def registration_enabled() -> bool:
    # Render previews can be deployed without the Blueprint's APP_ENV setting.
    # Require a durability declaration before accepting new accounts on Render
    # or a portfolio preview. Local development remains usable.
    public_preview = (os.getenv('APP_ENV', '').lower() == 'portfolio' or
                      os.getenv('RENDER', '').lower() == 'true')
    durable = os.getenv('MASR_DURABLE_STORAGE_CONFIRMED', '').lower() in ('1', 'true', 'yes')
    return not public_preview or durable


@router.post('/auth/register', status_code=201)
def register(body: Credentials):
    if not registration_enabled():
        raise HTTPException(503, detail='Account registration is unavailable on temporary-storage previews')
    setup()
    email = _validate_email(body.email)
    salt = secrets.token_hex(16)
    uid = uuid4().hex
    try:
        with _open() as c:
            c.execute('INSERT INTO account_users VALUES (?,?,?,?,?)',
                      (uid, email, _hash_password(body.password, salt), salt, _now().isoformat()))
            credential = _issue(c, uid)
    except sqlite3.IntegrityError:
        raise HTTPException(409, detail='Account already exists')
    return {'user': {'id': uid, 'email': email}, **credential}


@router.post('/auth/login')
def login(body: Credentials):
    email = _validate_email(body.email)
    with _open() as c:
        row = c.execute('SELECT * FROM account_users WHERE email=?', (email,)).fetchone()
        if not row or not hmac.compare_digest(row['password_hash'], _hash_password(body.password, row['salt'])):
            raise HTTPException(401, detail='Incorrect email or password')
        return {'user': {'id': row['id'], 'email': email}, **_issue(c, row['id'])}


@router.get('/auth/me')
def me(user=Depends(current_user)):
    return {'user': {'id': user['id'], 'email': user['email']}}


@router.post('/auth/logout')
def logout(user=Depends(current_user)):
    with _open() as c:
        c.execute('DELETE FROM account_tokens WHERE token_hash=?', (user['token_hash'],))
    return {'ok': True}


@router.delete('/my/account')
def delete_account(body: AccountDeletion, user=Depends(current_user)):
    """Permanently remove the authenticated account and all owned data.

    Requires current password and explicit confirmation; all sessions become invalid.
    Commercial partner enquiries are a separate record category, not linked to accounts.
    """
    with _open() as c:
        row = c.execute('SELECT password_hash,salt FROM account_users WHERE id=?',
                        (user['id'],)).fetchone()
        if not row or not hmac.compare_digest(row['password_hash'], _hash_password(body.password, row['salt'])):
            raise HTTPException(403, detail='Incorrect current password')
        from .ratings import delete_account_reviews
        delete_account_reviews(user['id'])
        c.execute('DELETE FROM account_users WHERE id=?', (user['id'],))
    return {'deleted': True}


def _favorite_place_id(place_id: str) -> str:
    # Explicitly allow catalogue slugs, not arbitrary text or external links.
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', place_id) or len(place_id) > 90:
        raise HTTPException(422, detail='Invalid place identifier')
    return place_id


@router.get('/my/favorites')
def my_favorites(user=Depends(current_user)):
    """Cross-device favorite slugs owned by the authenticated traveler."""
    with _open() as c:
        rows = c.execute('SELECT place_id FROM account_favorites WHERE user_id=? ORDER BY created_at,place_id',
                         (user['id'],)).fetchall()
    return {'place_ids': [row['place_id'] for row in rows]}


@router.post('/my/favorites/{place_id}')
def add_favorite(place_id: str, user=Depends(current_user)):
    ident = _favorite_place_id(place_id)
    if get_place(ident) is None:
        raise HTTPException(404, detail='Place not found in the curated catalogue')
    with _open() as c:
        # Write-lock before the cap check; concurrent writes cannot exceed 500.
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT 1 FROM account_favorites WHERE user_id=? AND place_id=?',
                     (user['id'], ident)).fetchone():
            return {'saved': True, 'place_id': ident}
        count = c.execute('SELECT COUNT(*) FROM account_favorites WHERE user_id=?',
                          (user['id'],)).fetchone()[0]
        if count >= 500:
            raise HTTPException(422, detail='A maximum of 500 favorites can be stored')
        c.execute('INSERT INTO account_favorites (user_id,place_id,created_at) VALUES (?,?,?)',
                  (user['id'], ident, _now().isoformat()))
    return {'saved': True, 'place_id': ident}


@router.delete('/my/favorites/{place_id}')
def remove_favorite(place_id: str, user=Depends(current_user)):
    ident = _favorite_place_id(place_id)
    with _open() as c:
        c.execute('DELETE FROM account_favorites WHERE user_id=? AND place_id=?',
                  (user['id'], ident))
    # An idempotent delete supports safe client retries.
    return {'saved': False, 'place_id': ident}


@router.get('/my/export')
def export_account_data(user=Depends(current_user)):
    """Portable account export, limited to the authenticated traveler.

    Never include password hashes, session bearer tokens or unrelated partner
    inquiries. The API's sensitive-route middleware adds Cache-Control: no-store.
    """
    with _open() as c:
        profile = c.execute('SELECT email, created_at FROM account_users WHERE id=?',
                            (user['id'],)).fetchone()
        trips = c.execute('SELECT id,title,itinerary,created_at,updated_at FROM account_trips WHERE user_id=? ORDER BY created_at',
                          (user['id'],)).fetchall()
        conversations = c.execute('SELECT id,title,messages_json,trip_state_json,itinerary_json,created_at,updated_at FROM account_conversations WHERE user_id=? ORDER BY created_at',
                                  (user['id'],)).fetchall()
        favorites = c.execute('SELECT place_id,created_at FROM account_favorites WHERE user_id=? ORDER BY created_at,place_id',
                              (user['id'],)).fetchall()
    from .ratings import account_reviews
    return {
        'format': 'masr-guide-traveler-export-v1',
        'exported_at': _now().isoformat(),
        'profile': {'email': profile['email'], 'created_at': profile['created_at']},
        'favorites': [dict(row) for row in favorites],
        'visitor_reviews': account_reviews(user['id']),
        'trips': [dict(id=row['id'], title=row['title'], itinerary=json.loads(row['itinerary']),
                       created_at=row['created_at'], updated_at=row['updated_at']) for row in trips],
        'conversations': [dict(id=row['id'], title=row['title'],
                               messages=json.loads(row['messages_json']),
                               trip_state=json.loads(row['trip_state_json']) if row['trip_state_json'] else None,
                               itinerary=json.loads(row['itinerary_json']) if row['itinerary_json'] else None,
                               created_at=row['created_at'], updated_at=row['updated_at']) for row in conversations],
        'note': 'Partner enquiries made outside traveler accounts are not associated with this export.'
    }


@router.get('/my/trips')
def trips(user=Depends(current_user)):
    with _open() as c:
        rows = c.execute('SELECT id,title,created_at,updated_at FROM account_trips WHERE user_id=? ORDER BY updated_at DESC', (user['id'],)).fetchall()
    return {'trips': [dict(x) for x in rows]}


@router.post('/my/trips', status_code=201)
def save_trip(body: TripSave, user=Depends(current_user)):
    raw = _validate_saved_itinerary(body.itinerary)
    tid = uuid4().hex
    stamp = _now().isoformat()
    with _open() as c:
        c.execute('INSERT INTO account_trips VALUES (?,?,?,?,?,?)', (tid, user['id'], body.title, raw, stamp, stamp))
    return {'id': tid, 'title': body.title, 'created_at': stamp}


@router.get('/my/trips/{trip_id}')
def trip_detail(trip_id: str, user=Depends(current_user)):
    with _open() as c:
        row = c.execute('SELECT * FROM account_trips WHERE id=? AND user_id=?', (trip_id, user['id'])).fetchone()
    if not row:
        raise HTTPException(404, 'Trip not found')
    return {'id': row['id'], 'title': row['title'], 'itinerary': json.loads(row['itinerary']), 'updated_at': row['updated_at']}


@router.put('/my/trips/{trip_id}')
def edit_trip(trip_id: str, body: TripSave, if_match: str | None = Header(None), user=Depends(current_user)):
    if _strict_writes() and not if_match:
        raise HTTPException(428, detail='If-Match version required; reload before updating')
    raw = _validate_saved_itinerary(body.itinerary)
    with _open() as c:
        if if_match is not None:
            cur = c.execute('''UPDATE account_trips SET title=?, itinerary=?, updated_at=?
                WHERE id=? AND user_id=? AND updated_at=?''',
                (body.title, raw, _now().isoformat(), trip_id, user['id'], if_match))
        else:
            cur = c.execute('''UPDATE account_trips SET title=?, itinerary=?, updated_at=?
                WHERE id=? AND user_id=?''',
                (body.title, raw, _now().isoformat(), trip_id, user['id']))
        if cur.rowcount == 0:
            exists = c.execute('SELECT 1 FROM account_trips WHERE id=? AND user_id=?',
                               (trip_id, user['id'])).fetchone()
            raise HTTPException(409 if exists else 404,
                                'Trip changed; reload before saving' if exists else 'Trip not found')
    return {'ok': True}


@router.delete('/my/trips/{trip_id}')
def delete_trip(trip_id: str, user=Depends(current_user)):
    with _open() as c:
        cur = c.execute('DELETE FROM account_trips WHERE id=? AND user_id=?', (trip_id, user['id']))
    if cur.rowcount == 0:
        raise HTTPException(404, 'Trip not found')
    return {'ok': True}


@router.get('/my/conversations')
def conversation_list(user=Depends(current_user)):
    with _open() as c:
        rows = c.execute('SELECT id,title,created_at,updated_at FROM account_conversations WHERE user_id=? ORDER BY updated_at DESC LIMIT 50', (user['id'],)).fetchall()
    return {'conversations': [dict(row) for row in rows]}


@router.post('/my/conversations', status_code=201)
def conversation_create(body: ConversationSave, user=Depends(current_user)):
    messages, trip, plan = _conversation_payload(body)
    conversation_id, stamp = uuid4().hex, _now().isoformat()
    with _open() as c:
        c.execute('INSERT INTO account_conversations VALUES (?,?,?,?,?,?,?,?)',
                  (conversation_id, user['id'], body.title, messages, trip, plan, stamp, stamp))
    return {'id': conversation_id, 'updated_at': stamp}


@router.get('/my/conversations/{conversation_id}')
def conversation_get(conversation_id: str, user=Depends(current_user)):
    with _open() as c:
        row = c.execute('SELECT * FROM account_conversations WHERE id=? AND user_id=?',
                        (conversation_id, user['id'])).fetchone()
    if not row:
        raise HTTPException(404, detail='Conversation not found')
    return {'id': row['id'], 'title': row['title'], 'messages': json.loads(row['messages_json']),
            'trip_state': json.loads(row['trip_state_json']) if row['trip_state_json'] else None,
            'itinerary': json.loads(row['itinerary_json']) if row['itinerary_json'] else None,
            'updated_at': row['updated_at']}


@router.put('/my/conversations/{conversation_id}')
def conversation_update(conversation_id: str, body: ConversationSave, if_match: str | None = Header(None), user=Depends(current_user)):
    if _strict_writes() and not if_match:
        raise HTTPException(428, detail='If-Match version required; reload before updating')
    messages, trip, plan = _conversation_payload(body)
    stamp = _now().isoformat()
    with _open() as c:
        if if_match is None:
            result = c.execute('UPDATE account_conversations SET title=?, messages_json=?, trip_state_json=?, itinerary_json=?, updated_at=? WHERE id=? AND user_id=?',
                               (body.title, messages, trip, plan, stamp, conversation_id, user['id']))
        else:
            result = c.execute('UPDATE account_conversations SET title=?, messages_json=?, trip_state_json=?, itinerary_json=?, updated_at=? WHERE id=? AND user_id=? AND updated_at=?',
                               (body.title, messages, trip, plan, stamp, conversation_id, user['id'], if_match))
        if not result.rowcount:
            exists = c.execute('SELECT 1 FROM account_conversations WHERE id=? AND user_id=?',
                               (conversation_id, user['id'])).fetchone()
            raise HTTPException(409 if exists else 404,
                                'Conversation changed; reload before saving' if exists else 'Conversation not found')
    return {'ok': True, 'updated_at': stamp}


@router.delete('/my/conversations/{conversation_id}')
def conversation_delete(conversation_id: str, user=Depends(current_user)):
    with _open() as c:
        result = c.execute('DELETE FROM account_conversations WHERE id=? AND user_id=?',
                           (conversation_id, user['id']))
    if not result.rowcount:
        raise HTTPException(404, detail='Conversation not found')
    return {'ok': True}


@router.post('/partners/apply', status_code=201)
def partner_apply(body: PartnerInterest):
    """Interest intake only. No checkout, commission attribution or bookable inventory implied."""
    if not os.getenv('PARTNER_INQUIRIES_ENABLED', '').lower() in ('1', 'true'):
        raise HTTPException(503, 'Partner enquiries are currently closed')
    setup()
    pid = uuid4().hex
    with _open() as c:
        c.execute('INSERT INTO partner_interest (id,company,email,website,city,description,created_at) VALUES (?,?,?,?,?,?,?)',
                  (pid, body.company, _validate_email(body.email), body.website, body.city, body.description, _now().isoformat()))
    return {'received': True, 'reference': pid}
