"""Account-owned reports and authenticated human moderation, bound to comment content."""
from contextlib import closing
from hashlib import sha256

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .accounts import current_user
from .commerce import require_staff

router = APIRouter(prefix='/api', tags=['community-moderation'])
VISIBLE_SQL = '''NOT EXISTS (SELECT 1 FROM visitor_comment_moderation m
    WHERE m.target_id=c.target_id AND m.voter_hash=c.voter_hash
      AND m.comment_text=c.comment AND m.status='hidden')'''


def setup(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS visitor_comment_reports (
            comment_id TEXT NOT NULL, reporter_hash TEXT NOT NULL,
            target_id TEXT NOT NULL, voter_hash TEXT NOT NULL, comment_text TEXT NOT NULL,
            reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open',
            PRIMARY KEY(comment_id,reporter_hash));
        CREATE TABLE IF NOT EXISTS visitor_comment_moderation (
            target_id TEXT NOT NULL, voter_hash TEXT NOT NULL, comment_text TEXT NOT NULL,
            status TEXT NOT NULL, PRIMARY KEY(target_id,voter_hash));
    ''')


def comment_id(target, voter, text):
    return sha256((target + '\0' + voter + '\0' + text).encode()).hexdigest()[:32]


def public_comment(row):
    data = dict(row)
    data['comment_id'] = comment_id(data['target_id'], data.pop('voter_hash'), data['comment'])
    return data


class Report(BaseModel):
    model_config = ConfigDict(extra='forbid')
    comment_id: str = Field(pattern=r'^[0-9a-f]{32}$')
    target_id: str = Field(min_length=1, max_length=160)
    reason: str = Field(pattern='^(spam|abuse|unsafe|privacy|misinformation)$')


class Review(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: str = Field(pattern='^(hide|restore|dismiss)$')


@router.post('/community/reports', status_code=202)
def report_comment(body: Report, user=Depends(current_user)):
    from .ratings import _connect_reviews, _account_hash
    with closing(_connect_reviews()) as db:
        # Resolve only currently visible public comments. Never accept client-supplied identity/text.
        rows = db.execute("SELECT target_id,voter_hash,comment FROM visitor_comments c WHERE target_id=? AND " + VISIBLE_SQL +
                          ' ORDER BY updated_at DESC,voter_hash DESC LIMIT 30', (body.target_id,)).fetchall()
        row = next((r for r in rows if comment_id(r['target_id'], r['voter_hash'], r['comment']) == body.comment_id), None)
        if not row:
            raise HTTPException(404, 'Comment is no longer available')
        with db:
            db.execute('''INSERT INTO visitor_comment_reports
                (comment_id,reporter_hash,target_id,voter_hash,comment_text,reason) VALUES (?,?,?,?,?,?)
                ON CONFLICT(comment_id,reporter_hash) DO UPDATE SET reason=excluded.reason''',
                (body.comment_id, _account_hash(user['id']), row['target_id'], row['voter_hash'], row['comment'], body.reason))
    return {'status': 'reported'}


@router.get('/admin/community/reports')
def reports(x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    from .ratings import _connect_reviews
    with closing(_connect_reviews()) as db:
        rows = db.execute('''SELECT comment_id,target_id,comment_text,reason,status,COUNT(*) AS reports
            FROM visitor_comment_reports GROUP BY comment_id,target_id,comment_text,reason,status
            ORDER BY status DESC, reports DESC LIMIT 100''').fetchall()
    return {'reports': [dict(row) for row in rows]}


@router.post('/admin/community/reports/{report_id}')
def review_report(report_id: str, body: Review, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    from .ratings import _connect_reviews
    with closing(_connect_reviews()) as db:
        with db:
            report = db.execute('SELECT * FROM visitor_comment_reports WHERE comment_id=? LIMIT 1', (report_id,)).fetchone()
            if not report:
                raise HTTPException(404, 'Report not found')
            live = db.execute('SELECT comment FROM visitor_comments WHERE target_id=? AND voter_hash=?',
                              (report['target_id'], report['voter_hash'])).fetchone()
            if not live or live['comment'] != report['comment_text']:
                raise HTTPException(409, 'Comment changed. Review the current version before moderating it.')
            if body.action != 'dismiss':
                db.execute('''INSERT INTO visitor_comment_moderation VALUES (?,?,?,?)
                    ON CONFLICT(target_id,voter_hash) DO UPDATE SET
                    comment_text=excluded.comment_text,status=excluded.status''',
                    (report['target_id'], report['voter_hash'], report['comment_text'],
                     'hidden' if body.action == 'hide' else 'visible'))
            db.execute('UPDATE visitor_comment_reports SET status=? WHERE comment_id=?', (body.action, report_id))
    return {'status': body.action}
