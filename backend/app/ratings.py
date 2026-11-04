"""Visitor-submitted star ratings. Anonymous votes are not verified visits."""
from contextlib import closing
from hashlib import sha256
import os
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, UUID4, field_validator

from .database import connect, get_place

router = APIRouter(prefix='/api/ratings', tags=['ratings'])

# The coastal destination guides are editorial entries, separate from catalog places.
COASTAL_GUIDE_IDS = {
    'sharm-el-sheikh', 'north-coast-alamein', 'alexandria', 'marsa-matruh',
    'marsa-alam', 'hurghada', 'dahab', 'ain-sokhna', 'nuweiba', 'safaga',
}


class RatingVote(BaseModel):
    visitor_id: UUID4
    rating: int = Field(ge=1, le=5)


class VisitorComment(BaseModel):
    visitor_id: UUID4
    name: str = Field(min_length=2, max_length=40)
    comment: str = Field(min_length=5, max_length=500)

    @field_validator('name', 'comment')
    @classmethod
    def clean_text(cls, value: str, info) -> str:
        value = ' '.join(value.split())
        if len(value) < (2 if info.field_name == 'name' else 5) or re.search(r'https?://|www\.|\S+@\S+', value, flags=re.I):
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
    row = db.execute('SELECT AVG(rating) AS average, COUNT(*) AS count FROM visitor_ratings WHERE target_id = ?', (target_id,)).fetchone()
    return {'average': round(row['average'], 1) if row['count'] else None, 'count': row['count']}


def _temporary_storage():
    return os.getenv('MASR_DURABLE_STORAGE_CONFIRMED', '').lower() not in {'1', 'true', 'yes'}


def _valid_target(target_id: str) -> bool:
    return (target_id.startswith('coast:') and target_id[6:] in COASTAL_GUIDE_IDS) or bool(get_place(target_id))


def _comments(db, target_id: str):
    rows = db.execute('''SELECT display_name AS name, comment, updated_at
                         FROM visitor_comments WHERE target_id = ?
                         ORDER BY updated_at DESC, rowid DESC LIMIT 30''', (target_id,)).fetchall()
    total = db.execute('SELECT COUNT(*) FROM visitor_comments WHERE target_id = ?', (target_id,)).fetchone()[0]
    return {'comments': [dict(row) for row in rows], 'count': total, 'temporary_storage': _temporary_storage()}


@router.get('')
def list_ratings():
    with closing(connect()) as db:
        rows = db.execute('SELECT target_id, ROUND(AVG(rating), 1) AS average, COUNT(*) AS count FROM visitor_ratings GROUP BY target_id').fetchall()
    return {'ratings': {row['target_id']: {'average': row['average'], 'count': row['count']} for row in rows},
            'temporary_storage': _temporary_storage()}


@router.post('/{target_id}')
def submit_rating(target_id: str, vote: RatingVote):
    if not _valid_target(target_id):
        raise HTTPException(404, detail='Place or coastal destination not found')
    voter_hash = sha256(vote.visitor_id.bytes).hexdigest()
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
def submit_comment(target_id: str, body: VisitorComment):
    if not _valid_target(target_id):
        raise HTTPException(404, detail='Place or coastal destination not found')
    voter_hash = sha256(body.visitor_id.bytes).hexdigest()
    with closing(connect()) as db:
        with db:
            db.execute('''INSERT INTO visitor_comments (target_id, voter_hash, display_name, comment)
                          VALUES (?, ?, ?, ?)
                          ON CONFLICT(target_id, voter_hash) DO UPDATE SET
                          display_name = excluded.display_name,
                          comment = excluded.comment,
                          updated_at = CURRENT_TIMESTAMP''',
                       (target_id, voter_hash, body.name, body.comment))
            return _comments(db, target_id)
