"""Staff-reconciled direct partner pilot. No checkout or automated payouts."""
import sqlite3
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from . import accounts
from .commerce import require_staff

router = APIRouter(prefix='/api/admin/pilot', tags=['direct-partner-pilot'])


def now():
    return datetime.now(timezone.utc).isoformat()


def setup():
    with accounts._open() as c:
        c.executescript('''
          CREATE TABLE IF NOT EXISTS pilot_contracts (
            id TEXT PRIMARY KEY, offer_id TEXT NOT NULL UNIQUE, partner TEXT NOT NULL,
            target_url TEXT NOT NULL, agreement_reference TEXT NOT NULL,
            currency TEXT NOT NULL, commission_bps INTEGER NOT NULL,
            expires_at TEXT NOT NULL, created_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS pilot_referrals (
            id TEXT PRIMARY KEY, contract_id TEXT NOT NULL REFERENCES pilot_contracts(id),
            created_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS pilot_bookings (
            id TEXT PRIMARY KEY, referral_id TEXT NOT NULL UNIQUE REFERENCES pilot_referrals(id),
            contract_id TEXT NOT NULL REFERENCES pilot_contracts(id),
            external_booking_id TEXT NOT NULL, eligible_amount_minor BIGINT NOT NULL,
            commission_minor BIGINT NOT NULL, evidence_reference TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(contract_id, external_booking_id));
          CREATE TABLE IF NOT EXISTS pilot_reversals (
            booking_id TEXT PRIMARY KEY REFERENCES pilot_bookings(id),
            evidence_reference TEXT NOT NULL, created_at TEXT NOT NULL);
        ''')


class ContractIn(BaseModel):
    offer_id: str = Field(min_length=1, max_length=80)
    agreement_reference: str = Field(min_length=3, max_length=160)
    currency: str = Field(pattern=r'^(EGP|USD|EUR|GBP)$')
    commission_bps: int = Field(strict=True, ge=1, le=10000)
    expires_at: datetime
    agreement_confirmed: bool = False


@router.post('/contracts', status_code=201)
def create_contract(body: ContractIn, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    if not body.agreement_confirmed:
        raise HTTPException(422, 'Confirm a signed agreement before enabling attribution')
    if body.expires_at.tzinfo is None or body.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(422, 'A future expiry with timezone is required')
    ident = uuid4().hex
    try:
        with accounts._open() as c:
            offer = c.execute('SELECT * FROM partner_offers WHERE id=?', (body.offer_id,)).fetchone()
            if not offer:
                raise HTTPException(404, 'Offer not found')
            c.execute('INSERT INTO pilot_contracts VALUES (?,?,?,?,?,?,?,?,?)',
                      (ident, body.offer_id, offer['partner'], offer['target_url'],
                       body.agreement_reference, body.currency, body.commission_bps,
                       body.expires_at.astimezone(timezone.utc).isoformat(), now()))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, 'Offer already has an immutable pilot agreement; use a new offer for new terms') from exc
    return {'id': ident}


def attributed_url(c, offer_id, target_url):
    """Only contracted, unchanged offers gain an opaque attribution code."""
    contract = c.execute('SELECT * FROM pilot_contracts WHERE offer_id=?', (offer_id,)).fetchone()
    if not contract:
        return target_url
    offer = c.execute('SELECT partner FROM partner_offers WHERE id=?', (offer_id,)).fetchone()
    if (contract['target_url'] != target_url or contract['partner'] != offer['partner']
            or datetime.fromisoformat(contract['expires_at']) <= datetime.now(timezone.utc)):
        raise HTTPException(409, 'Partner offer changed or agreement expired; staff review required')
    ident = uuid4().hex
    c.execute('INSERT INTO pilot_referrals VALUES (?,?,?)', (ident, contract['id'], now()))
    parts = urlsplit(target_url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != 'masr_ref']
    query.append(('masr_ref', ident))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class BookingIn(BaseModel):
    contract_id: str = Field(min_length=1, max_length=80)
    referral_id: str = Field(min_length=1, max_length=80)
    external_booking_id: str = Field(min_length=1, max_length=120)
    eligible_amount_minor: int = Field(strict=True, ge=1, le=10**10)
    evidence_reference: str = Field(min_length=3, max_length=160)
    fulfilled_confirmed: bool = False


@router.post('/bookings', status_code=201)
def confirm_booking(body: BookingIn, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    if not body.fulfilled_confirmed:
        raise HTTPException(422, 'Partner-confirmed fulfilment is required; a click is not a booking')
    try:
        with accounts._open() as c:
            row = c.execute('''SELECT p.commission_bps FROM pilot_referrals r
                JOIN pilot_contracts p ON p.id=r.contract_id WHERE r.id=? AND p.id=?''',
                (body.referral_id, body.contract_id)).fetchone()
            if not row:
                raise HTTPException(404, 'Referral does not belong to this agreement')
            # Integer half-up rounding. Supported currencies all have 100 minor units.
            commission = (body.eligible_amount_minor * row['commission_bps'] + 5000) // 10000
            ident = uuid4().hex
            c.execute('INSERT INTO pilot_bookings VALUES (?,?,?,?,?,?,?,?,?)',
                      (ident, body.referral_id, body.contract_id, body.external_booking_id,
                       body.eligible_amount_minor, commission, body.evidence_reference,
                       'fulfilled', now()))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, 'Booking or referral already reconciled') from exc
    return {'id': ident, 'commission_minor': commission, 'status': 'fulfilled'}


class ReversalIn(BaseModel):
    evidence_reference: str = Field(min_length=3, max_length=160)


@router.post('/bookings/{booking_id}/reverse')
def reverse_booking(booking_id: str, body: ReversalIn, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    try:
        with accounts._open() as c:
            if not c.execute('SELECT id FROM pilot_bookings WHERE id=?', (booking_id,)).fetchone():
                raise HTTPException(404, 'Booking not found')
            c.execute('INSERT INTO pilot_reversals VALUES (?,?,?)', (booking_id, body.evidence_reference, now()))
            c.execute("UPDATE pilot_bookings SET status='reversed' WHERE id=?", (booking_id,))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, 'Booking already reversed') from exc
    return {'ok': True}


@router.get('/report')
def report(x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as c:
        contracts = c.execute('SELECT * FROM pilot_contracts ORDER BY created_at').fetchall()
        rows = []
        for contract in contracts:
            ident = contract['id']
            counts = c.execute('''SELECT COUNT(*) AS confirmed_bookings,
                COALESCE(SUM(CASE WHEN status='fulfilled' THEN commission_minor ELSE 0 END),0) AS commission_minor,
                COALESCE(SUM(CASE WHEN status='reversed' THEN 1 ELSE 0 END),0) AS reversed_bookings
                FROM pilot_bookings WHERE contract_id=?''', (ident,)).fetchone()
            referrals = c.execute('SELECT COUNT(*) FROM pilot_referrals WHERE contract_id=?', (ident,)).fetchone()[0]
            rows.append({**dict(contract), **dict(counts), 'referrals': referrals})
    return {'agreements': rows, 'note': 'Staff-reconciled estimates, not collected revenue or payouts. Currencies must not be added together.'}


@router.get('/activity')
def activity(x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as db:
        referrals = db.execute('SELECT id,contract_id,created_at FROM pilot_referrals ORDER BY created_at DESC LIMIT 100').fetchall()
        bookings = db.execute('SELECT id,contract_id,external_booking_id,status,commission_minor FROM pilot_bookings ORDER BY created_at DESC LIMIT 100').fetchall()
    return {'referrals': [dict(row) for row in referrals], 'bookings': [dict(row) for row in bookings]}
