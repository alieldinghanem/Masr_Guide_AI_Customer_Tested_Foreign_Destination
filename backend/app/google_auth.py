"""Google Identity Services sign-in with browser-bound single-use challenges."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import timedelta
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request, Response
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from pydantic import BaseModel, ConfigDict, Field
from psycopg import IntegrityError as PostgresIntegrityError

from . import accounts

router = APIRouter(prefix='/api/auth/google', tags=['google-sign-in'])


def client_id():
    value = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    return value if re.fullmatch(r'[A-Za-z0-9_-]+\.apps\.googleusercontent\.com', value) else ''


def setup():
    with accounts._open() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS account_google_identities (
                subject TEXT PRIMARY KEY,
                user_id TEXT UNIQUE NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
                password_enabled INTEGER NOT NULL, linked_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS account_google_challenges (
                nonce_hash TEXT PRIMARY KEY, browser_hash TEXT NOT NULL,
                purpose TEXT NOT NULL, expires_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS account_google_delete_proofs (
                proof_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL);
        ''')


def methods(db, user_id):
    row = db.execute('SELECT password_enabled FROM account_google_identities WHERE user_id=?', (user_id,)).fetchone()
    return {'password': not row or bool(row['password_enabled']), 'google': bool(row)}


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Challenge(BaseModel):
    model_config = ConfigDict(extra='forbid')
    purpose: str = Field(default='login', pattern='^(login|delete)$')


class Credential(BaseModel):
    model_config = ConfigDict(extra='forbid')
    credential: str = Field(min_length=100, max_length=20000)
    nonce: str = Field(min_length=40, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    existing_password: str | None = Field(default=None, min_length=12, max_length=128)


def _cookie(request):
    local = request.url.hostname in ('127.0.0.1', 'localhost', '::1') and os.getenv('APP_ENV', '').lower() != 'production'
    return ('masr-google-browser-local' if local else '__Host-masr-google-browser'), not local


@router.get('/config')
def config():
    return {'enabled': bool(client_id()), 'client_id': client_id() or None}


@router.post('/challenge')
def challenge(body: Challenge, request: Request, response: Response, authorization: str | None = Header(None)):
    if not client_id():
        raise HTTPException(503, 'Google sign-in is not configured')
    if body.purpose == 'delete':
        accounts.current_user(authorization)
    name, secure = _cookie(request)
    browser = request.cookies.get(name, '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', browser):
        browser = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    now = accounts._now()
    with accounts._open() as db:
        db.execute('DELETE FROM account_google_challenges WHERE expires_at<=?', (now.isoformat(),))
        db.execute('DELETE FROM account_google_delete_proofs WHERE expires_at<=?', (now.isoformat(),))
        db.execute('INSERT INTO account_google_challenges VALUES (?,?,?,?)',
                   (_digest(nonce), _digest(browser), body.purpose, (now + timedelta(minutes=5)).isoformat()))
    response.set_cookie(name, browser, max_age=600, httponly=True, secure=secure, samesite='strict', path='/')
    return {'nonce': nonce}


def _verify(body, request, purpose):
    audience = client_id()
    if not audience:
        raise HTTPException(503, 'Google sign-in is not configured')
    browser = request.cookies.get(_cookie(request)[0], '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', browser):
        raise HTTPException(400, 'Start Google sign-in in this browser again')
    with accounts._open() as db:
        row = db.execute('SELECT 1 FROM account_google_challenges WHERE nonce_hash=? AND browser_hash=? '
                         'AND purpose=? AND expires_at>?',
                         (_digest(body.nonce), _digest(browser), purpose, accounts._now().isoformat())).fetchone()
    if not row:
        raise HTTPException(400, 'Google challenge expired or already used')
    transport = GoogleRequest()

    def bounded(*args, **kwargs):
        kwargs['timeout'] = 8
        return transport(*args, **kwargs)

    try:
        claims = id_token.verify_oauth2_token(body.credential, bounded, audience=audience)
    except TransportError as exc:
        raise HTTPException(503, 'Google verification is temporarily unavailable') from exc
    except (ValueError, GoogleAuthError) as exc:
        raise HTTPException(401, 'Google identity could not be verified') from exc
    if (claims.get('aud') != audience or claims.get('iss') not in ('accounts.google.com', 'https://accounts.google.com')
            or not isinstance(claims.get('sub'), str) or not 1 <= len(claims['sub']) <= 255
            or not isinstance(claims.get('nonce'), str)
            or not hmac.compare_digest(claims['nonce'], body.nonce)):
        raise HTTPException(401, 'Google identity could not be verified')
    return claims, _digest(browser)


def _consume(db, nonce, browser_hash, purpose):
    row = db.execute('DELETE FROM account_google_challenges WHERE nonce_hash=? AND browser_hash=? '
                     'AND purpose=? AND expires_at>? RETURNING nonce_hash',
                     (_digest(nonce), browser_hash, purpose, accounts._now().isoformat())).fetchone()
    if not row:
        raise HTTPException(400, 'Google challenge expired or already used')


def _finish_sign_in(body, claims, browser_hash):
    with accounts._open() as db:
        identity = db.execute('SELECT user_id FROM account_google_identities WHERE subject=?', (claims['sub'],)).fetchone()
        if identity:
            user = db.execute('SELECT id,email FROM account_users WHERE id=?', (identity['user_id'],)).fetchone()
            if not user:
                raise HTTPException(409, 'Account changed. Restart Google sign-in')
        else:
            if claims.get('email_verified') is not True:
                raise HTTPException(401, 'Verify the email with Google before signing in')
            email = accounts._validate_email(claims.get('email', '') if isinstance(claims.get('email'), str) else '')
            user = db.execute('SELECT * FROM account_users WHERE email=?', (email,)).fetchone()
            authoritative = email.endswith('@gmail.com') or (isinstance(claims.get('hd'), str) and bool(claims['hd']))
            if user:
                linked = db.execute('SELECT subject FROM account_google_identities WHERE user_id=?', (user['id'],)).fetchone()
                if linked:
                    raise HTTPException(409, 'A different Google identity is already linked to this account')
                if not body.existing_password:
                    # Do not consume the challenge until the existing password
                    # is proved. Email equality alone never links accounts.
                    raise HTTPException(428, 'Enter the existing account password to link Google')
                if not hmac.compare_digest(user['password_hash'], accounts._hash_password(body.existing_password, user['salt'])):
                    raise HTTPException(403, 'Incorrect existing account password')
                enabled = 1
            else:
                if not authoritative:
                    raise HTTPException(422, 'Use email registration first, then link this external-email Google account with its password')
                if not accounts.registration_enabled():
                    raise HTTPException(503, 'New account registration is unavailable')
                uid, salt = uuid4().hex, secrets.token_hex(16)
                # An unissued random verifier preserves the old NOT NULL schema;
                # password login/reset stays disabled for Google-only accounts.
                password_hash = accounts._hash_password(secrets.token_urlsafe(64), salt)
                db.execute('INSERT INTO account_users VALUES (?,?,?,?,?)', (uid, email, password_hash, salt, accounts._now().isoformat()))
                user = {'id': uid, 'email': email}
                enabled = 0
            db.execute('INSERT INTO account_google_identities VALUES (?,?,?,?)',
                       (claims['sub'], user['id'], enabled, accounts._now().isoformat()))
            if authoritative:
                db.execute('INSERT INTO account_email_status VALUES (?,?) ON CONFLICT(user_id) '
                           'DO UPDATE SET verified_at=excluded.verified_at', (user['id'], accounts._now().isoformat()))
        _consume(db, body.nonce, browser_hash, 'login')
        return {'user': {'id': user['id'], 'email': user['email']}, 'auth_methods': methods(db, user['id']), **accounts._issue(db, user['id'])}


@router.post('')
def sign_in(body: Credential, request: Request):
    claims, browser_hash = _verify(body, request, 'login')
    try:
        return _finish_sign_in(body, claims, browser_hash)
    except (sqlite3.IntegrityError, PostgresIntegrityError) as exc:
        raise HTTPException(409, 'Account changed. Restart Google sign-in') from exc


@router.post('/reauth-delete')
def reauthenticate_delete(body: Credential, request: Request, authorization: str | None = Header(None)):
    user = accounts.current_user(authorization)
    claims, browser_hash = _verify(body, request, 'delete')
    proof = secrets.token_urlsafe(40)
    with accounts._open() as db:
        identity = db.execute('SELECT subject FROM account_google_identities WHERE user_id=?', (user['id'],)).fetchone()
        if not identity or not hmac.compare_digest(identity['subject'], claims['sub']):
            raise HTTPException(403, 'Use the Google identity linked to this account')
        _consume(db, body.nonce, browser_hash, 'delete')
        db.execute('INSERT INTO account_google_delete_proofs VALUES (?,?,?)',
                   (_digest(proof), user['id'], (accounts._now() + timedelta(minutes=5)).isoformat()))
    return {'google_proof': proof}


def consume_delete_proof(db, proof, user_id):
    row = db.execute('DELETE FROM account_google_delete_proofs WHERE proof_hash=? AND user_id=? AND expires_at>? RETURNING user_id',
                     (_digest(proof), user_id, accounts._now().isoformat())).fetchone()
    if not row:
        raise HTTPException(403, 'Confirm your Google identity again before deleting the account')
