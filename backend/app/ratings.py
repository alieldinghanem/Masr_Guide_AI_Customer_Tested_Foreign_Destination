"""Account-owned visitor ratings and comments. Accounts do not verify visits."""
from contextlib import closing
from hashlib import sha256
import os
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .accounts import current_user
from .database import connect, get_place

router = APIRouter(prefix='/api/ratings', tags=['ratings'])

# The coastal destination guides are editorial entries, separate from catalog places.
COASTAL_GUIDE_IDS = {
    'sharm-el-sheikh', 'north-coast-alamein', 'alexandria', 'marsa-matruh',
    'marsa-alam', 'hurghada', 'dahab', 'ain-sokhna', 'nuweiba', 'safaga',
}


class RatingVote(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rating: int = Field(ge=1, le=5)


class VisitorComment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    comment: str = Field(min_length=5, max_length=500)

    @field_validator('comment')
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = ' '.join(value.split())
        if len(value) < 5 or re.search(r'https?://|www\.|\S+@\S+', value, flags=re.I):
            raise ValueError('Links and email addresses are not allowed in comments')
        return value


def setup():
    with closing(connect()) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS visitor_ratings (
            target_id TEXT NOT NULL,
            voter_hash TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (target_id, voter_hash)
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS visitor_comments (
            target_id TEXT NOT NULL,
            voter_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            comment TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (target_id, voter_hash)
        )''')
        db.commit()


def _summary(db, target_id):
    row = db.execute("SELECT AVG(rating) AS average, COUNT(*) AS count FROM visitor_ratings WHERE target_id = ? AND voter_hash LIKE 'account:%'", (target_id,)).fetchone()
    return {'average': round(row['average'], 1) if row['count'] else None, 'count': row['count']}


def _temporary_storage():
    return os.getenv('MASR_DURABLE_STORAGE_CONFIRMED', '').lower() not in {'1', 'true', 'yes'}


def _valid_target(target_id: str) -> bool:
    return (target_id.startswith('coast:') and target_id[6:] in COASTAL_GUIDE_IDS) or bool(get_place(target_id))


def _comments(db, target_id: str):
    rows = db.execute('''SELECT display_name AS name, comment, updated_at
                         FROM visitor_comments WHERE target_id = ? AND voter_hash LIKE 'account:%'
                         ORDER BY updated_at DESC, rowid DESC LIMIT 30''', (target_id,)).fetchall()
    total = db.execute("SELECT COUNT(*) FROM visitor_comments WHERE target_id = ? AND voter_hash LIKE 'account:%'", (target_id,)).fetchone()[0]
    return {'comments': [dict(row) for row in rows], 'count': total, 'temporary_storage': _temporary_storage()}


def _account_hash(user_id: str) -> str:
    return 'account:' + sha256(user_id.encode()).hexdigest()


def delete_account_reviews(user_id: str):
    """Remove public reviews when their account is deleted."""
    with closing(connect()) as db:
        with db:
            voter_hash = _account_hash(user_id)
            db.execute('DELETE FROM visitor_ratings WHERE voter_hash = ?', (voter_hash,))
            db.execute('DELETE FROM visitor_comments WHERE voter_hash = ?', (voter_hash,))


def account_reviews(user_id: str):
    with closing(connect()) as db:
        voter_hash = _account_hash(user_id)
        ratings = db.execute('SELECT target_id, rating, updated_at FROM visitor_ratings WHERE voter_hash = ?', (voter_hash,)).fetchall()
        comments = db.execute('SELECT target_id, comment, updated_at FROM visitor_comments WHERE voter_hash = ?', (voter_hash,)).fetchall()
    return {'ratings': [dict(row) for row in ratings], 'comments': [dict(row) for row in comments]}


@router.get('')
def list_ratings():
    with closing(connect()) as db:
        rows = db.execute("SELECT target_id, ROUND(AVG(rating), 1) AS average, COUNT(*) AS count FROM visitor_ratings WHERE voter_hash LIKE 'account:%' GROUP BY target_id").fetchall()
    return {'ratings': {row['target_id']: {'average': row['average'], 'count': row['count']} for row in rows},
            'temporary_storage': _temporary_storage()}


@router.get('/mine')
def my_ratings(user=Depends(current_user)):
    with closing(connect()) as db:
        rows = db.execute('SELECT target_id, rating FROM visitor_ratings WHERE voter_hash = ?',
                          (_account_hash(user['id']),)).fetchall()
    return {'ratings': {row['target_id']: row['rating'] for row in rows}}


@router.post('/{target_id}')
def submit_rating(target_id: str, vote: RatingVote, user=Depends(current_user)):
    if not _valid_target(target_id):
        raise HTTPException(404, detail='Place or coastal destination not found')
    voter_hash = _account_hash(user['id'])
    with closing(connect()) as db:
        with db:
            db.execute('''INSERT INTO visitor_ratings (target_id, voter_hash, rating)
                          VALUES (?, ?, ?)
                          ON CONFLICT(target_id, voter_hash) DO UPDATE SET
                          rating = excluded.rating, updated_at = CURRENT_TIMESTAMP''',
                       (target_id, voter_hash, vote.rating))
            summary = _summary(db, target_id)
    return {'target_id': target_id, **summary, 'your_rating': vote.rating,
            'temporary_storage': _temporary_storage()}


@router.get('/{target_id}/comments')
def list_comments(target_id: str):
    if not _valid_target(target_id):
        raise HTTPException(404, detail='Place or coastal destination not found')
    with closing(connect()) as db:
        return _comments(db, target_id)


@router.post('/{target_id}/comments')
def submit_comment(target_id: str, body: VisitorComment, user=Depends(current_user)):
    if not _valid_target(target_id):
        raise HTTPException(404, detail='Place or coastal destination not found')
    voter_hash = _account_hash(user['id'])
    display_name = 'Traveler #' + user['id'][:6].upper()
    with closing(connect()) as db:
        with db:
            db.execute('''INSERT INTO visitor_comments (target_id, voter_hash, display_name, comment)
                          VALUES (?, ?, ?, ?)
                          ON CONFLICT(target_id, voter_hash) DO UPDATE SET
                          display_name = excluded.display_name,
                          comment = excluded.comment,
                          updated_at = CURRENT_TIMESTAMP''',
                       (target_id, voter_hash, display_name, body.comment))
            return _comments(db, target_id)
