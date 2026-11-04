"""Visitor-submitted star ratings. Anonymous votes are not verified visits."""
from contextlib import closing
from hashlib import sha256
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, UUID4

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


def setup():
    with closing(connect()) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS visitor_ratings (
            target_id TEXT NOT NULL,
            voter_hash TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (target_id, voter_hash)
        )''')
        db.commit()


def _summary(db, target_id):
    row = db.execute('SELECT AVG(rating) AS average, COUNT(*) AS count FROM visitor_ratings WHERE target_id = ?', (target_id,)).fetchone()
    return {'average': round(row['average'], 1) if row['count'] else None, 'count': row['count']}


def _temporary_storage():
    return os.getenv('MASR_DURABLE_STORAGE_CONFIRMED', '').lower() not in {'1', 'true', 'yes'}


@router.get('')
def list_ratings():
    with closing(connect()) as db:
        rows = db.execute('SELECT target_id, ROUND(AVG(rating), 1) AS average, COUNT(*) AS count FROM visitor_ratings GROUP BY target_id').fetchall()
    return {'ratings': {row['target_id']: {'average': row['average'], 'count': row['count']} for row in rows},
            'temporary_storage': _temporary_storage()}


@router.post('/{target_id}')
def submit_rating(target_id: str, vote: RatingVote):
    if not (target_id.startswith('coast:') and target_id[6:] in COASTAL_GUIDE_IDS) and not get_place(target_id):
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
