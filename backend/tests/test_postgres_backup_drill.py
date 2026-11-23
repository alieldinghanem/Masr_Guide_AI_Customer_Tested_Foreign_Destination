"""Restore a real CI backup into a disposable database; never target production."""
import importlib.util
import os
from pathlib import Path
import shutil
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'postgres_backup.py'
spec = importlib.util.spec_from_file_location('postgres_backup_tool', SCRIPT)
backup_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup_tool)


def test_postgres_backup_rejects_repository_destination_and_unsafe_tls():
    with pytest.raises(ValueError):
        backup_tool._private_path(SCRIPT.parent / 'accounts.dump')
    with pytest.raises(ValueError):
        backup_tool._settings('postgresql://user:password@remote.example/db?sslmode=disable')
    with pytest.raises(ValueError):
        backup_tool.restore_drill('postgresql://user:password@localhost/db', 'postgresql://different:password@localhost/db', '/never-read.dump')
    assert backup_tool._settings('postgresql://user:password@remote.example/db')['PGSSLMODE'] == 'require'


@pytest.mark.skipif(not os.getenv('MASR_TEST_POSTGRES_URL') or not shutil.which('pg_dump') or not shutil.which('pg_restore'),
                    reason='Isolated CI PostgreSQL and client tools required')
def test_real_backup_restore_and_account_trip_ownership(tmp_path, monkeypatch):
    import psycopg
    from psycopg import sql
    from fastapi.testclient import TestClient
    from app import accounts, security
    from app.main import app

    source = os.environ['MASR_TEST_POSTGRES_URL']
    # Only the explicitly supplied loopback CI database may create a scratch DB.
    parsed = urlsplit(source)
    assert parsed.hostname in ('localhost', '127.0.0.1', '::1')
    target_name = 'masr_restore_qa_' + uuid4().hex
    target = urlunsplit(parsed._replace(path='/' + target_name))
    email = 'restore-' + uuid4().hex + '@example.org'
    password = 'Restore-QA-Password-2026!'
    monkeypatch.setattr(accounts, '_DB', None)
    monkeypatch.setenv('NEON_DATABASE_URL', source)
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'catalog.sqlite3'))
    monkeypatch.setenv('MASR_DURABLE_STORAGE_CONFIRMED', 'true')
    monkeypatch.setenv('ADMIN_API_TOKEN', 'isolated-backup-test-staff-token')
    security._guard_hits.clear()
    with TestClient(app) as client:
        created = client.post('/api/auth/register', json={'email': email, 'password': password})
        assert created.status_code == 201
        user_id = created.json()['user']['id']
        headers = {'Authorization': 'Bearer ' + created.json()['token']}
        trip = client.post('/api/my/trips', headers=headers, json={'title': 'Restore rehearsal', 'itinerary': {'days': [{'day': 1, 'city': 'Cairo', 'stops': []}]}})
        assert trip.status_code == 201, trip.text
        trip_id = trip.json()['id']
        # A linked legacy account must keep its identity and password after restore.
        with accounts._open() as db:
            db.execute('INSERT INTO account_google_identities VALUES (?,?,?,?)', ('restore-sub-' + user_id, user_id, 1, accounts._now().isoformat()))
        post = client.post('/api/community/posts', headers=headers, json={
            'client_id': uuid4().hex, 'body': 'Community post retained through an isolated backup restore.', 'topic': 'tip'})
        assert post.status_code == 201, post.text
        post_id = post.json()['post']['id']
        like_path = '/api/community/posts/' + post_id + '/like'
        assert client.put(like_path, headers=headers).json()['post']['likes_count'] == 1
        assert client.put(like_path, headers=headers).json()['post']['likes_count'] == 1
        assert client.delete(like_path, headers=headers).json()['post']['likes_count'] == 0
        assert client.put(like_path, headers=headers).json()['post']['likes_count'] == 1
        reply = client.post('/api/community/posts/' + post_id + '/replies', headers=headers,
                            json={'client_id': uuid4().hex, 'body': 'A reply preserved through backup and restore.'})
        assert reply.status_code == 201, reply.text
    with psycopg.connect(source, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(target_name)))
    try:
        archive = tmp_path / 'private-backup.dump'
        assert backup_tool.backup(source, archive)['archive_verified']
        restored = backup_tool.restore_drill(source, target, archive)
        assert restored['restored'] and restored['counts']['account_users'] >= 1
        with pytest.raises(ValueError, match='not empty'):
            backup_tool.restore_drill(source, target, archive)
        monkeypatch.setenv('NEON_DATABASE_URL', target)
        security._guard_hits.clear()
        with TestClient(app) as restored_app:
            logged_in = restored_app.post('/api/auth/login', json={'email': email, 'password': password})
            assert logged_in.status_code == 200
            assert logged_in.json()['auth_methods'] == {'google': True, 'password': True}
            headers = {'Authorization': 'Bearer ' + logged_in.json()['token']}
            assert restored_app.get('/api/my/trips/' + trip_id, headers=headers).json()['title'] == 'Restore rehearsal'
            restored_post = restored_app.get('/api/community/posts/' + post_id, headers=headers).json()['post']
            assert restored_post['is_owner'] and restored_post['liked'] and restored_post['likes_count'] == 1
            assert restored_post['replies_count'] == 1
            restored_reply = restored_app.get('/api/community/posts/' + post_id + '/replies', headers=headers).json()['replies'][0]
            assert restored_reply['body'] == 'A reply preserved through backup and restore.' and restored_reply['is_owner']
            outsider = restored_app.post('/api/auth/register', json={'email': 'other-' + uuid4().hex + '@example.org', 'password': password})
            assert outsider.status_code == 201
            assert restored_app.get('/api/my/trips/' + trip_id, headers={'Authorization': 'Bearer ' + outsider.json()['token']}).status_code == 404
        # Original source data remains intact after the drill.
        with psycopg.connect(source) as db:
            assert db.execute('SELECT user_id FROM account_trips WHERE id=%s', (trip_id,)).fetchone()[0] == user_id
    finally:
        with psycopg.connect(source, autocommit=True) as admin:
            admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(target_name)))
            admin.execute('DELETE FROM account_users WHERE id=%s', (user_id,))
