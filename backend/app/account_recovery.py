"""Single-use account links. Disabled until an operator configures secure mail."""
import hashlib
import os
import secrets
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage
from urllib.parse import urlsplit

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import accounts

router = APIRouter(prefix='/api/auth', tags=['account-recovery'])


def mail_ready():
    origin = urlsplit(os.getenv('PUBLIC_SITE_URL', ''))
    return (origin.scheme == 'https' and bool(origin.netloc) and not origin.username
            and not origin.password and origin.path in ('', '/') and not origin.query and not origin.fragment
            and all(os.getenv(name, '').strip() for name in
                    ('SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD', 'MAIL_FROM'))
            and os.getenv('SMTP_PORT', '587') in ('465', '587'))


def setup():
    with accounts._open() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS account_actions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
                purpose TEXT NOT NULL, expires_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS account_email_status (
                user_id TEXT PRIMARY KEY REFERENCES account_users(id) ON DELETE CASCADE,
                verified_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS account_mail_requests (
                address_hash TEXT PRIMARY KEY, next_at TEXT NOT NULL);
        ''')


class EmailRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(min_length=5, max_length=254)


class LinkToken(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: str = Field(min_length=40, max_length=120, pattern=r'^[A-Za-z0-9_-]+$')


class PasswordReset(LinkToken):
    password: str = Field(min_length=12, max_length=128)


def _send_link(address, purpose, token):
    message = EmailMessage()
    message['From'] = os.environ['MAIL_FROM']
    message['To'] = address
    message['Subject'] = 'Masr Guide AI — ' + ('Reset your password' if purpose == 'reset' else 'Verify your email')
    url = os.environ['PUBLIC_SITE_URL'].rstrip('/') + '/#/account?action=' + purpose + '&token=' + token
    message.set_content('Open this single-use link within 30 minutes:\n' + url +
                        '\n\nIf you did not request this, ignore this message. Do not share the link.')
    context = ssl.create_default_context()
    port = int(os.getenv('SMTP_PORT', '587'))
    factory = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
    kwargs = {'context': context} if port == 465 else {}
    with factory(os.environ['SMTP_HOST'], port, timeout=10, **kwargs) as server:
        if port == 587:
            server.starttls(context=context)
        server.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        server.send_message(message)


def _deliver(address, purpose, token):
    try:
        _send_link(address, purpose, token)
    except (OSError, smtplib.SMTPException):
        with accounts._open() as db:
            db.execute('DELETE FROM account_actions WHERE token_hash=?',
                       (hashlib.sha256(token.encode()).hexdigest(),))


def _request(address, purpose, tasks):
    if not mail_ready():
        raise HTTPException(503, 'Account email is not configured yet')
    address = accounts._validate_email(address)
    now = accounts._now()
    address_hash = hashlib.sha256(address.encode()).hexdigest()
    token = None
    with accounts._open() as db:
        # An atomic claim limits both existing and unknown addresses equally.
        claim = db.execute('''INSERT INTO account_mail_requests VALUES (?,?)
            ON CONFLICT(address_hash) DO UPDATE SET next_at=excluded.next_at
            WHERE account_mail_requests.next_at <= ? RETURNING address_hash''',
            (address_hash, (now + timedelta(minutes=1)).isoformat(), now.isoformat())).fetchone()
        db.execute('DELETE FROM account_actions WHERE expires_at <= ?', (now.isoformat(),))
        db.execute('DELETE FROM account_mail_requests WHERE next_at < ?', ((now - timedelta(days=1)).isoformat(),))
        if claim:
            user = db.execute('SELECT id FROM account_users WHERE email=?', (address,)).fetchone()
            if user and purpose == 'reset':
                from .google_auth import methods
                if not methods(db, user['id'])['password']:
                    user = None  # Google-only accounts recover through Google.
            if user:
                token = secrets.token_urlsafe(40)
                db.execute('DELETE FROM account_actions WHERE user_id=? AND purpose=?', (user['id'], purpose))
                db.execute('INSERT INTO account_actions VALUES (?,?,?,?)',
                           (hashlib.sha256(token.encode()).hexdigest(), user['id'], purpose,
                            (now + timedelta(minutes=30)).isoformat()))
    if token:
        # Delivery happens after responding, avoiding an SMTP timing oracle.
        # A failed send invalidates the token; no token is returned or logged.
        tasks.add_task(_deliver, address, purpose, token)
    return {'status': 'accepted', 'detail': 'If the account is eligible, check its inbox for a link.'}


@router.get('/email-capabilities')
def capabilities():
    return {'password_recovery': bool(mail_ready()), 'email_verification': bool(mail_ready())}


@router.post('/password-reset/request', status_code=202)
def request_reset(body: EmailRequest, tasks: BackgroundTasks):
    return _request(body.email, 'reset', tasks)


@router.post('/email-verification/request', status_code=202)
def request_verification(tasks: BackgroundTasks, user=Depends(accounts.current_user)):
    return _request(user['email'], 'verify', tasks)


@router.get('/email-status')
def email_status(user=Depends(accounts.current_user)):
    with accounts._open() as db:
        row = db.execute('SELECT verified_at FROM account_email_status WHERE user_id=?', (user['id'],)).fetchone()
    return {'verified': bool(row)}


def _consume(db, token, purpose):
    row = db.execute('''DELETE FROM account_actions
        WHERE token_hash=? AND purpose=? AND expires_at>? RETURNING user_id''',
        (hashlib.sha256(token.encode()).hexdigest(), purpose, accounts._now().isoformat())).fetchone()
    if not row:
        raise HTTPException(400, 'This link is invalid, expired or already used')
    return row['user_id']


@router.post('/password-reset/confirm')
def reset_password(body: PasswordReset):
    salt = secrets.token_hex(16)
    password_hash = accounts._hash_password(body.password, salt)
    with accounts._open() as db:
        user_id = _consume(db, body.token, 'reset')
        db.execute('UPDATE account_users SET password_hash=?,salt=? WHERE id=?', (password_hash, salt, user_id))
        db.execute('DELETE FROM account_tokens WHERE user_id=?', (user_id,))
        db.execute('DELETE FROM account_actions WHERE user_id=? AND purpose=?', (user_id, 'reset'))
    return {'status': 'password_updated', 'sign_in_required': True}


@router.post('/email-verification/confirm')
def verify_email(body: LinkToken):
    with accounts._open() as db:
        user_id = _consume(db, body.token, 'verify')
        db.execute('''INSERT INTO account_email_status VALUES (?,?)
            ON CONFLICT(user_id) DO UPDATE SET verified_at=excluded.verified_at''',
                   (user_id, accounts._now().isoformat()))
    return {'verified': True}
