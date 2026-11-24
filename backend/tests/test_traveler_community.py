from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import accounts, community, security
from app.main import app

STAFF = {'X-Admin-Key': 'community-unit-test-staff-token'}


@pytest.fixture
def social(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, '_DB', tmp_path / 'accounts.sqlite3')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'catalog.sqlite3'))
    monkeypatch.delenv('NEON_DATABASE_URL', raising=False)
    monkeypatch.setenv('APP_ENV', 'local')
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    monkeypatch.setenv('ADMIN_API_TOKEN', STAFF['X-Admin-Key'])
    monkeypatch.setenv('COMMUNITY_WRITE_RATE_PER_MINUTE', '1000')
    monkeypatch.setenv('COMMUNITY_REPORT_RATE_PER_MINUTE', '1000')
    security._guard_hits.clear()
    with TestClient(app) as client:
        def member():
            email = f'community-{uuid4().hex}@example.org'
            result = client.post('/api/auth/register', json={'email': email, 'password': 'Community-test-password-2026!'})
            assert result.status_code == 201
            return {'Authorization': 'Bearer ' + result.json()['token']}, result.json()['user']
        yield client, member


def create(client, headers, **extra):
    payload = {'client_id': uuid4().hex, 'body': 'A practical question about visiting Egypt.', **extra}
    response = client.post('/api/community/posts', headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()['post'], payload


def test_public_reads_and_authenticated_writes_without_identity_disclosure(social):
    client, member = social
    headers, user = member()
    post, payload = create(client, headers, target_id='karnak', topic='tip')
    assert client.post('/api/community/posts', json=payload).status_code == 401
    feed = client.get('/api/community/posts').json()
    assert feed['posts'][0]['id'] == post['id']
    assert not feed['posts'][0]['is_owner']
    assert client.get('/api/community/posts', headers=headers).json()['posts'][0]['is_owner']
    for secret in (user['id'], user['email'], community._hash(user)):
        assert secret not in str(feed)
    assert client.get('/api/community/posts').headers['cache-control'] == 'no-store'


def test_posting_waits_for_moderation_configuration(social, monkeypatch):
    client, member = social
    headers, _ = member()
    monkeypatch.delenv('ADMIN_API_TOKEN')
    assert client.get('/api/community/status').json() == {'posting_enabled': False}
    assert client.post('/api/community/posts', headers=headers, json={'client_id': uuid4().hex, 'body': 'Question about Cairo.'}).status_code == 503
    assert client.get('/api/community/posts').json()['posts'] == []


@pytest.mark.parametrize('body', ['    ', 'abcd', 'https://spam.example', 'mail@example.org', 'x' * 2001])
def test_validates_public_content(social, body):
    client, member = social
    headers, _ = member()
    assert client.post('/api/community/posts', headers=headers, json={'client_id': uuid4().hex, 'body': body}).status_code == 422


def test_destination_and_topic_are_allowlisted(social):
    client, member = social
    headers, _ = member()
    data = {'client_id': uuid4().hex, 'body': 'A useful travel experience.'}
    assert client.post('/api/community/posts', headers=headers, json={**data, 'topic': 'advertisement'}).status_code == 422
    assert client.post('/api/community/posts', headers=headers, json={**data, 'target_id': 'invented-place'}).status_code == 404
    create(client, headers, target_id='coast:dahab', topic='experience')


def test_retries_do_not_duplicate_posts_or_allow_claiming_another_submission(social):
    client, member = social
    owner, _ = member(); other, _ = member()
    post, data = create(client, owner)
    assert client.post('/api/community/posts', headers=owner, json=data).json()['post']['id'] == post['id']
    assert len(client.get('/api/community/posts').json()['posts']) == 1
    assert client.post('/api/community/posts', headers=other, json=data).status_code == 409
    assert client.post('/api/community/posts', headers=owner, json={**data, 'body': 'Changed attempt after submission.'}).status_code == 409


def test_filters_normalized_arabic_literal_search_and_stable_cursor(social):
    client, member = social
    headers, _ = member()
    first, _ = create(client, headers, body='نصيحة عن الإسكندرية والشواطئ', topic='tip', target_id='coast:alexandria')
    second, _ = create(client, headers, body='A question about Luxor museums.', topic='question')
    result = client.get('/api/community/posts', params={'q': 'اسكندريه', 'topic': 'tip', 'target_id': 'coast:alexandria'}).json()
    assert [item['id'] for item in result['posts']] == [first['id']]
    assert client.get('/api/community/posts', params={'q': '%'}).json()['posts'] == []
    page = client.get('/api/community/posts', params={'limit': 1}).json()
    assert page['posts'][0]['id'] == second['id']
    create(client, headers, body='New post inserted between page requests.')
    next_page = client.get('/api/community/posts', params={'limit': 1, 'cursor': page['next_cursor']}).json()
    assert [item['id'] for item in next_page['posts']] == [first['id']]
    assert next_page['next_cursor'] is None
    assert client.get('/api/community/posts', params={'limit': 100}).status_code == 422
    assert client.get('/api/community/posts', params={'cursor': 'z' * 32}).status_code == 422


def test_only_owner_can_edit_and_stale_writes_fail(social):
    client, member = social
    owner, _ = member(); other, _ = member()
    post, _ = create(client, owner)
    path = '/api/community/posts/' + post['id']
    edit = {'body': 'An updated practical travel question.', 'version': 1}
    assert client.patch(path, headers=other, json=edit).status_code == 404
    assert client.patch(path, headers=owner, json=edit).status_code == 200
    assert client.patch(path, headers=owner, json=edit).status_code == 409
    assert client.get(path).json()['post']['version'] == 2
    assert client.request('DELETE', path, headers=owner, json={'version': 1}).status_code == 409
    assert client.request('DELETE', path, headers=owner, json={'version': 2}).status_code == 200
    assert client.get(path).status_code == 404
    with community._connect() as db:
        stored = db.execute('SELECT body,search_text,state FROM community_posts WHERE id=?', (post['id'],)).fetchone()
        assert stored['body'] == stored['search_text'] == '' and stored['state'] == 'deleted'


def test_likes_are_idempotent_and_scoped_to_viewer(social):
    client, member = social
    owner, _ = member(); other, _ = member()
    post, _ = create(client, owner)
    path = '/api/community/posts/' + post['id'] + '/like'
    assert client.put(path).status_code == 401
    for _ in range(2):
        result = client.put(path, headers=owner).json()['post']
        assert result['likes_count'] == 1 and result['liked']
    assert not client.get('/api/community/posts', headers=other).json()['posts'][0]['liked']
    assert client.put(path, headers=other).json()['post']['likes_count'] == 2
    assert client.delete(path, headers=owner).json()['post']['likes_count'] == 1
    assert client.delete(path, headers=owner).json()['post']['likes_count'] == 1


def test_replies_have_idempotency_ownership_pagination_and_parent_visibility(social):
    client, member = social
    owner, _ = member(); other, _ = member()
    post, _ = create(client, owner)
    path = '/api/community/posts/' + post['id'] + '/replies'
    payload = {'client_id': uuid4().hex, 'body': 'Visit early and take a rest at midday.'}
    reply = client.post(path, headers=other, json=payload).json()['reply']
    assert client.post(path, headers=other, json=payload).json()['reply']['id'] == reply['id']
    another, _ = create(client, owner)
    assert client.post('/api/community/posts/' + another['id'] + '/replies', headers=other, json=payload).status_code == 409
    second = client.post(path, headers=owner, json={'client_id': uuid4().hex, 'body': 'Thank you for the useful advice.'}).json()['reply']
    page = client.get(path, params={'limit': 1}).json()
    assert page['replies'][0]['id'] == reply['id']
    assert client.get(path, params={'limit': 1, 'cursor': page['next_cursor']}).json()['replies'][0]['id'] == second['id']
    edit_path = '/api/community/replies/' + reply['id']
    assert client.patch(edit_path, headers=owner, json={'body': 'Unauthorized reply change.', 'version': 1}).status_code == 404
    assert client.patch(edit_path, headers=other, json={'body': 'Bring water and rest in the shade.', 'version': 1}).status_code == 200
    assert client.get('/api/community/posts/' + post['id']).json()['post']['replies_count'] == 2
    client.request('DELETE', '/api/community/posts/' + post['id'], headers=owner, json={'version': 1})
    assert client.get(path).status_code == 404
    assert client.post(path, headers=other, json=payload).status_code == 404


def test_reports_require_accounts_staff_and_current_content_version(social):
    client, member = social
    owner, _ = member(); reporter, _ = member()
    post, _ = create(client, owner)
    report = {'kind': 'post', 'content_id': post['id'], 'version': 1, 'reason': 'unsafe'}
    assert client.post('/api/community/content-reports', json=report).status_code == 401
    for _ in range(2):
        assert client.post('/api/community/content-reports', headers=reporter, json=report).status_code == 202
    assert client.get('/api/admin/community/content-reports').status_code == 403
    reports = client.get('/api/admin/community/content-reports', headers=STAFF).json()['reports']
    assert len(reports) == 1
    path = '/api/community/posts/' + post['id']
    client.patch(path, headers=owner, json={'body': 'A newer safe version of the post.', 'version': 1})
    assert client.post('/api/community/content-reports', headers=reporter, json=report).status_code == 409
    moderation = '/api/admin/community/content-reports/' + reports[0]['id']
    assert client.post(moderation, headers=STAFF, json={'action': 'hide'}).status_code == 409
    assert client.get(path).status_code == 200


@pytest.mark.parametrize('kind', ['post', 'reply'])
def test_hide_restore_and_owner_deletion_cannot_be_undone_by_stale_moderation(social, kind):
    client, member = social
    owner, _ = member(); reporter, _ = member()
    post, _ = create(client, owner)
    replies_path = '/api/community/posts/' + post['id'] + '/replies'
    reply = client.post(replies_path, headers=owner, json={'client_id': uuid4().hex, 'body': 'A reply for moderation review.'}).json()['reply']
    item = post if kind == 'post' else reply
    content_path = '/api/community/' + ('posts/' if kind == 'post' else 'replies/') + item['id']
    report = {'kind': kind, 'content_id': item['id'], 'version': 1, 'reason': 'abuse'}
    client.post('/api/community/content-reports', headers=reporter, json=report)
    rid = client.get('/api/admin/community/content-reports', headers=STAFF).json()['reports'][0]['id']
    review_path = '/api/admin/community/content-reports/' + rid
    assert client.post(review_path, headers=STAFF, json={'action': 'hide'}).status_code == 200
    assert client.patch(content_path, headers=owner, json={'body': 'Try bypassing moderation by editing.', 'version': 1}).status_code == 403
    if kind == 'post':
        assert client.get('/api/community/posts').json()['posts'] == []
        assert client.get(replies_path).status_code == 404
    else:
        assert client.get(replies_path).json()['replies'] == []
    assert client.post(review_path, headers=STAFF, json={'action': 'restore'}).status_code == 200
    assert client.request('DELETE', content_path, headers=owner, json={'version': 1}).status_code == 200
    assert client.post(review_path, headers=STAFF, json={'action': 'restore'}).status_code == 409


def test_account_export_and_removal_include_posts_replies_and_likes(social):
    client, member = social
    owner, user = member(); other, _ = member()
    post, _ = create(client, owner)
    other_post, _ = create(client, other)
    client.post('/api/community/posts/' + post['id'] + '/replies', headers=other, json={'client_id': uuid4().hex, 'body': 'A reply on the account-owned post.'})
    client.post('/api/community/posts/' + other_post['id'] + '/replies', headers=owner, json={'client_id': uuid4().hex, 'body': 'An account-owned reply on another post.'})
    client.put('/api/community/posts/' + other_post['id'] + '/like', headers=owner)
    exported = client.get('/api/my/export', headers=owner).json()['community']
    assert len(exported['posts']) == len(exported['replies']) == 1
    assert client.request('DELETE', '/api/my/account', headers=owner, json={'password': 'Community-test-password-2026!', 'confirmation': 'DELETE MY ACCOUNT'}).status_code == 200
    assert client.get('/api/community/posts/' + post['id']).status_code == 404
    assert client.get('/api/community/posts/' + other_post['id']).json()['post']['likes_count'] == 0
    with community._connect() as db:
        assert db.execute('SELECT COUNT(*) FROM community_replies').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM community_posts WHERE author_hash=?', (community._hash(user),)).fetchone()[0] == 0


def test_community_mutations_are_rate_limited(social, monkeypatch):
    client, member = social
    owner, _ = member()
    monkeypatch.setenv('COMMUNITY_WRITE_RATE_PER_MINUTE', '1')
    create(client, owner)
    response = client.post('/api/community/posts', headers=owner, json={'client_id': uuid4().hex, 'body': 'Second post should be rate limited.'})
    assert response.status_code == 429 and response.headers.get('retry-after')
