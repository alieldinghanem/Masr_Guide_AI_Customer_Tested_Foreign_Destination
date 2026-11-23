"""Optional daily counters only: no identity, address, prompt or conversation text."""
from datetime import datetime, timezone
import os
import sqlite3
from psycopg import Error as PostgresError
from fastapi import APIRouter, Header
from . import accounts
from .commerce import require_staff

router = APIRouter(prefix='/api/admin', tags=['aggregate-metrics'])
EVENTS = {'plan_created', 'plan_edited', 'trip_saved', 'gemini_reply', 'fallback_reply'}


def enabled():
    return os.getenv('MASR_AGGREGATE_METRICS_ENABLED', '').lower() in ('true', '1', 'yes')


def setup():
    with accounts._open() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS aggregate_metrics (
            day TEXT NOT NULL,event TEXT NOT NULL,count INTEGER NOT NULL,
            PRIMARY KEY(day,event))''')


def record(event):
    if not enabled() or event not in EVENTS:
        return
    try:
        with accounts._open() as db:
            db.execute('''INSERT INTO aggregate_metrics VALUES (?,?,1)
                ON CONFLICT(day,event) DO UPDATE SET count=aggregate_metrics.count+1''',
                (datetime.now(timezone.utc).date().isoformat(), event))
    except (sqlite3.Error, PostgresError):
        # Analytics must never turn a successful account/trip action into a failure.
        return


def consultation(result, had_trip):
    if result.get('itinerary'):
        record('plan_edited' if had_trip else 'plan_created')
    if result.get('mode') in ('gemini-rag', 'gemini-search-grounded', 'gemini-rag-no-live-citations', 'gemini-dialogue+local-planner', 'hotel-gemini-assisted'):
        record('gemini_reply')
    elif result.get('mode') in ('offline-fallback', 'provider-error'):
        record('fallback_reply')
    return result


@router.get('/metrics')
def counts(x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with accounts._open() as db:
        rows = db.execute('SELECT day,event,count FROM aggregate_metrics ORDER BY day DESC,event LIMIT 180').fetchall()
    return {'enabled': enabled(), 'counts': [dict(row) for row in rows], 'contains_personal_data': False}
