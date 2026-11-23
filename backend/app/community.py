"""Public traveler posts. Mutations belong to accounts; reports bind to versions."""
from contextlib import closing
from datetime import datetime, timezone
import re
import os
import sqlite3
import unicodedata
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .accounts import current_user, registration_enabled
from .commerce import require_staff
from .ratings import _account_hash, _connect_reviews, _valid_target

router = APIRouter(prefix='/api', tags=['traveler-community'])


def posting_enabled():
    return bool(os.getenv('ADMIN_API_TOKEN', '').strip()) and registration_enabled()


def require_posting():
    if not posting_enabled():
        raise HTTPException(503, 'Community posting is not available yet')


def _connect():
    db = _connect_reviews()
    if isinstance(db, sqlite3.Connection):
        db.execute('PRAGMA foreign_keys=ON')
    return db


@router.get('/community/status')
def status():
    return {'posting_enabled': posting_enabled()}


def setup():
    with closing(_connect()) as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS community_posts (
                id TEXT PRIMARY KEY, author_hash TEXT NOT NULL, body TEXT NOT NULL,
                topic TEXT NOT NULL, target_id TEXT, search_text TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1, state TEXT NOT NULL DEFAULT 'active');
            CREATE TABLE IF NOT EXISTS community_replies (
                id TEXT PRIMARY KEY, post_id TEXT NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
                author_hash TEXT NOT NULL, body TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1, state TEXT NOT NULL DEFAULT 'active');
            CREATE TABLE IF NOT EXISTS community_likes (
                post_id TEXT NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
                author_hash TEXT NOT NULL, PRIMARY KEY(post_id,author_hash));
            CREATE TABLE IF NOT EXISTS community_content_reports (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, content_id TEXT NOT NULL,
                version INTEGER NOT NULL, reporter_hash TEXT NOT NULL, body TEXT NOT NULL,
                reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL,
                UNIQUE(kind,content_id,version,reporter_hash));
            CREATE INDEX IF NOT EXISTS community_posts_feed ON community_posts(state,created_at,id);
            CREATE INDEX IF NOT EXISTS community_replies_thread ON community_replies(post_id,state,created_at,id);
        ''')
        db.commit()


def normalized(text):
    text = ''.join(char for char in unicodedata.normalize('NFKD', text.casefold())
                   if unicodedata.category(char) != 'Mn' and char != '\u0640')
    return text.translate(str.maketrans({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي', 'ة': 'ه'}))


class Content(BaseModel):
    model_config = ConfigDict(extra='forbid')
    body: str = Field(min_length=5, max_length=2000)

    @field_validator('body')
    @classmethod
    def valid_text(cls, value):
        value = value.strip()
        if len(value) < 5 or re.search(r'https?://|www\.|\S+@\S+', value, re.I):
            raise ValueError('Write at least 5 characters, without links or email addresses')
        return value


class PostCreate(Content):
    topic: str = Field(default='question', pattern='^(question|experience|tip)$')
    target_id: str | None = Field(default=None, max_length=90)
    client_id: str = Field(pattern='^[0-9a-f]{32}$')


class PostEdit(Content):
    version: int = Field(ge=1, strict=True)


class ReplyCreate(Content):
    client_id: str = Field(pattern='^[0-9a-f]{32}$')


class DeleteContent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int = Field(ge=1, strict=True)


class ContentReport(DeleteContent):
    kind: str = Field(pattern='^(post|reply)$')
    content_id: str = Field(pattern='^[0-9a-f]{32}$')
    reason: str = Field(pattern='^(spam|abuse|unsafe|privacy|misinformation)$')


class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: str = Field(pattern='^(hide|restore|dismiss)$')


def viewer(authorization: str | None = Header(None)):
    return current_user(authorization) if authorization else None


def _hash(user):
    return _account_hash(user['id']) if user else ''


def _public(row, user=None):
    result = dict(row)
    author = result.pop('author_hash')
    result.pop('search_text', None)
    result.pop('state', None)
    result['author'] = 'Traveler #' + author.split(':')[-1][:6].upper()
    result['is_owner'] = bool(user and author == _hash(user))
    if 'liked' in result:
        result['liked'] = bool(result['liked'])
    return result


def _post(db, post_id, user=None):
    row = db.execute('''SELECT p.*,
        (SELECT COUNT(*) FROM community_replies r WHERE r.post_id=p.id AND r.state='active') AS replies_count,
        (SELECT COUNT(*) FROM community_likes l WHERE l.post_id=p.id) AS likes_count,
        (SELECT COUNT(*) FROM community_likes l WHERE l.post_id=p.id AND l.author_hash=?) AS liked
        FROM community_posts p WHERE p.id=? AND p.state='active' ''', (_hash(user), post_id)).fetchone()
    if not row:
        raise HTTPException(404, 'Post is no longer available')
    return _public(row, user)


@router.get('/community/posts')
def posts(topic: str | None = Query(None, pattern='^(question|experience|tip)$'),
          target_id: str | None = Query(None, max_length=90), q: str = Query('', max_length=100),
          cursor: str | None = Query(None, pattern='^[0-9a-f]{32}$'),
          limit: int = Query(12, ge=1, le=30), user=Depends(viewer)):
    conditions, args = ["p.state='active'"], []
    if topic:
        conditions.append('p.topic=?'); args.append(topic)
    if target_id:
        conditions.append('p.target_id=?'); args.append(target_id)
    for word in normalized(q).split()[:10]:
        conditions.append("p.search_text LIKE ? ESCAPE '!'")
        args.append('%' + word.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%')
    with closing(_connect()) as db:
        if cursor:
            previous = db.execute('SELECT created_at FROM community_posts WHERE id=?', (cursor,)).fetchone()
            if not previous:
                raise HTTPException(400, 'Invalid feed cursor')
            conditions.append('(p.created_at < ? OR (p.created_at=? AND p.id<?))')
            args.extend([previous['created_at'], previous['created_at'], cursor])
        rows = db.execute('SELECT p.id FROM community_posts p WHERE ' + ' AND '.join(conditions) +
                          ' ORDER BY p.created_at DESC,p.id DESC LIMIT ?', (*args, limit + 1)).fetchall()
        result = [_post(db, row['id'], user) for row in rows[:limit]]
    return {'posts': result, 'next_cursor': rows[limit - 1]['id'] if len(rows) > limit else None}


@router.post('/community/posts', status_code=201)
def create_post(body: PostCreate, user=Depends(current_user)):
    require_posting()
    if body.target_id and not _valid_target(body.target_id):
        raise HTTPException(404, 'Destination not found')
    stamp = datetime.now(timezone.utc).isoformat()
    with closing(_connect()) as db:
        with db:
            db.execute('''INSERT INTO community_posts
                (id,author_hash,body,topic,target_id,search_text,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING''',
                (body.client_id, _hash(user), body.body, body.topic, body.target_id,
                 normalized(body.body), stamp, stamp))
            existing = db.execute('SELECT * FROM community_posts WHERE id=?', (body.client_id,)).fetchone()
            if (existing['author_hash'] != _hash(user) or existing['body'] != body.body
                    or existing['topic'] != body.topic or existing['target_id'] != body.target_id
                    or existing['state'] != 'active'):
                raise HTTPException(409, 'This submission has already changed')
        return {'post': _post(db, body.client_id, user)}


@router.get('/community/posts/{post_id}')
def post_detail(post_id: str, user=Depends(viewer)):
    with closing(_connect()) as db:
        return {'post': _post(db, post_id, user)}


@router.get('/community/posts/{post_id}/replies')
def replies(post_id: str, cursor: str | None = Query(None, pattern='^[0-9a-f]{32}$'),
            limit: int = Query(20, ge=1, le=50), user=Depends(viewer)):
    with closing(_connect()) as db:
        _post(db, post_id)
        args, condition = [post_id], ''
        if cursor:
            previous = db.execute('SELECT created_at FROM community_replies WHERE id=? AND post_id=?', (cursor, post_id)).fetchone()
            if not previous:
                raise HTTPException(400, 'Invalid reply cursor')
            condition = ' AND (created_at>? OR (created_at=? AND id>?))'
            args.extend([previous['created_at'], previous['created_at'], cursor])
        rows = db.execute("SELECT * FROM community_replies WHERE post_id=? AND state='active'" + condition +
                          ' ORDER BY created_at,id LIMIT ?', (*args, limit + 1)).fetchall()
    return {'replies': [_public(row, user) for row in rows[:limit]],
            'next_cursor': rows[limit - 1]['id'] if len(rows) > limit else None}


@router.post('/community/posts/{post_id}/replies', status_code=201)
def reply(post_id: str, body: ReplyCreate, user=Depends(current_user)):
    require_posting()
    stamp = datetime.now(timezone.utc).isoformat()
    with closing(_connect()) as db:
        with db:
            _post(db, post_id)
            db.execute('''INSERT INTO community_replies
                (id,post_id,author_hash,body,created_at,updated_at) VALUES (?,?,?,?,?,?)
                ON CONFLICT(id) DO NOTHING''', (body.client_id, post_id, _hash(user), body.body, stamp, stamp))
            row = db.execute('SELECT * FROM community_replies WHERE id=?', (body.client_id,)).fetchone()
            if row['post_id'] != post_id or row['author_hash'] != _hash(user) or row['body'] != body.body or row['state'] != 'active':
                raise HTTPException(409, 'This submission has already changed')
    return {'reply': _public(row, user)}


def _change(kind, content_id, version, user, text=None):
    table = 'community_posts' if kind == 'post' else 'community_replies'
    with closing(_connect()) as db:
        with db:
            row = db.execute('SELECT * FROM ' + table + ' WHERE id=? AND author_hash=?', (content_id, _hash(user))).fetchone()
            if not row or row['state'] == 'deleted':
                raise HTTPException(404, 'Content not found')
            if kind == 'reply' and text is not None:
                _post(db, row['post_id'])
            if text is not None and row['state'] != 'active':
                raise HTTPException(403, 'This content is under moderation')
            fields = "state='deleted', body=''" if text is None else 'body=?'
            args = [] if text is None else [text]
            if text is None and kind == 'post':
                fields += ", search_text=''"
            if text is not None and kind == 'post':
                fields += ', search_text=?'; args.append(normalized(text))
            stamp = datetime.now(timezone.utc).isoformat()
            updated = db.execute('UPDATE ' + table + ' SET ' + fields + ', version=version+1,updated_at=? '
                                 'WHERE id=? AND author_hash=? AND version=? AND state=?',
                                 (*args, stamp, content_id, _hash(user), version, row['state']))
            if not updated.rowcount:
                raise HTTPException(409, 'Content changed. Reload before editing')
            if text is None:
                db.execute("UPDATE community_content_reports SET body='',status='deleted_by_author' WHERE kind=? AND content_id=?",
                           (kind, content_id))
    return {'ok': True}


@router.patch('/community/posts/{content_id}')
def edit_post(content_id: str, body: PostEdit, user=Depends(current_user)):
    return _change('post', content_id, body.version, user, body.body)


@router.delete('/community/posts/{content_id}')
def delete_post(content_id: str, body: DeleteContent, user=Depends(current_user)):
    return _change('post', content_id, body.version, user)


@router.patch('/community/replies/{content_id}')
def edit_reply(content_id: str, body: PostEdit, user=Depends(current_user)):
    return _change('reply', content_id, body.version, user, body.body)


@router.delete('/community/replies/{content_id}')
def delete_reply(content_id: str, body: DeleteContent, user=Depends(current_user)):
    return _change('reply', content_id, body.version, user)


@router.put('/community/posts/{post_id}/like')
def like(post_id: str, user=Depends(current_user)):
    require_posting()
    with closing(_connect()) as db:
        with db:
            _post(db, post_id)
            db.execute('INSERT INTO community_likes VALUES (?,?) ON CONFLICT DO NOTHING', (post_id, _hash(user)))
        return {'post': _post(db, post_id, user)}


@router.delete('/community/posts/{post_id}/like')
def unlike(post_id: str, user=Depends(current_user)):
    with closing(_connect()) as db:
        with db:
            _post(db, post_id)
            db.execute('DELETE FROM community_likes WHERE post_id=? AND author_hash=?', (post_id, _hash(user)))
        return {'post': _post(db, post_id, user)}


@router.post('/community/content-reports', status_code=202)
def report(body: ContentReport, user=Depends(current_user)):
    table = 'community_posts' if body.kind == 'post' else 'community_replies'
    with closing(_connect()) as db:
        with db:
            row = db.execute('SELECT * FROM ' + table + " WHERE id=? AND state='active'", (body.content_id,)).fetchone()
            if not row:
                raise HTTPException(404, 'Content is no longer available')
            if row['version'] != body.version:
                raise HTTPException(409, 'Content changed. Reload before reporting')
            if body.kind == 'reply':
                _post(db, row['post_id'])
            db.execute('''INSERT INTO community_content_reports
                (id,kind,content_id,version,reporter_hash,body,reason,created_at) VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(kind,content_id,version,reporter_hash) DO NOTHING''',
                (uuid4().hex, body.kind, body.content_id, body.version, _hash(user), row['body'],
                 body.reason, datetime.now(timezone.utc).isoformat()))
    return {'status': 'reported'}


@router.get('/admin/community/content-reports')
def content_reports(x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with closing(_connect()) as db:
        rows = db.execute('''SELECT id,kind,content_id,version,body,reason,status,created_at
            FROM community_content_reports ORDER BY CASE WHEN status='open' THEN 0 ELSE 1 END,
            created_at DESC,id DESC LIMIT 100''').fetchall()
    return {'reports': [dict(row) for row in rows]}


@router.post('/admin/community/content-reports/{report_id}')
def moderate(report_id: str, body: Decision, x_admin_key: str | None = Header(None)):
    require_staff(x_admin_key)
    with closing(_connect()) as db:
        with db:
            item = db.execute('SELECT * FROM community_content_reports WHERE id=?', (report_id,)).fetchone()
            if not item:
                raise HTTPException(404, 'Report not found')
            table = 'community_posts' if item['kind'] == 'post' else 'community_replies'
            row = db.execute('SELECT * FROM ' + table + ' WHERE id=?', (item['content_id'],)).fetchone()
            if not row or row['state'] == 'deleted' or row['version'] != item['version']:
                raise HTTPException(409, 'Content changed. Review the current version')
            if body.action != 'dismiss':
                state = 'hidden' if body.action == 'hide' else 'active'
                changed = db.execute('UPDATE ' + table + " SET state=? WHERE id=? AND version=? AND state!='deleted'",
                                     (state, item['content_id'], item['version']))
                if not changed.rowcount:
                    raise HTTPException(409, 'Content changed during review')
            db.execute('UPDATE community_content_reports SET status=? WHERE kind=? AND content_id=? AND version=?',
                       (body.action, item['kind'], item['content_id'], item['version']))
    return {'status': body.action}


def delete_account_content(user_id):
    author = _account_hash(user_id)
    with closing(_connect()) as db:
        with db:
            db.execute('DELETE FROM community_content_reports WHERE reporter_hash=? OR '
                       "(kind='post' AND content_id IN (SELECT id FROM community_posts WHERE author_hash=?)) OR "
                       "(kind='reply' AND content_id IN (SELECT id FROM community_replies WHERE author_hash=?))", (author, author, author))
            db.execute('DELETE FROM community_posts WHERE author_hash=?', (author,))
            db.execute('DELETE FROM community_replies WHERE author_hash=?', (author,))
            db.execute('DELETE FROM community_likes WHERE author_hash=?', (author,))


def export_account_content(user_id):
    author = _account_hash(user_id)
    with closing(_connect()) as db:
        posts = db.execute('SELECT id,body,topic,target_id,created_at,updated_at,state FROM community_posts WHERE author_hash=?', (author,)).fetchall()
        replies = db.execute('SELECT id,post_id,body,created_at,updated_at,state FROM community_replies WHERE author_hash=?', (author,)).fetchall()
        likes = db.execute('SELECT post_id FROM community_likes WHERE author_hash=?', (author,)).fetchall()
        reports = db.execute('SELECT kind,content_id,reason,status,created_at FROM community_content_reports WHERE reporter_hash=?', (author,)).fetchall()
    return {'posts': [dict(row) for row in posts], 'replies': [dict(row) for row in replies],
            'liked_post_ids': [row['post_id'] for row in likes], 'reports': [dict(row) for row in reports]}
