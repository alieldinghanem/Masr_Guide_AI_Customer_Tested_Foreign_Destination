"""Test real account database snapshots and reject corrupted/unsafe backups."""
import importlib.util
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from app import accounts

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'storage_backup.py'
spec = importlib.util.spec_from_file_location('storage_backup_v78', SCRIPT)
backup_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup_tool)


def test_online_backup_rehearsal(tmp_path, monkeypatch):
    source = tmp_path / 'live.sqlite3'
    monkeypatch.setenv('MASR_USER_DB', str(source))
    accounts._DB = source
    try:
        accounts.setup()
        with accounts._open() as con:
            con.execute('INSERT INTO account_users VALUES (?,?,?,?,?)',
                        ('test-user', 'example@example.org', 'hash', 'salt', '2026-10-15T00:00:00+00:00'))
        backup_dir = tmp_path / 'backups'
        result = backup_tool.backup(backup_dir)
        assert backup_tool.verify_db(result)['users'] == 1
        with closing(sqlite3.connect(source)) as con:
            con.execute('DELETE FROM account_users')
        assert backup_tool.verify_db(result)['users'] == 1, 'Backup must remain an independent snapshot'
        with closing(sqlite3.connect(result)) as con:
            con.execute('DROP TABLE account_users')
        with pytest.raises(ValueError, match='Required account tables'):
            backup_tool.verify_db(result)
    finally:
        accounts._DB = None


def test_refuses_project_directory(tmp_path, monkeypatch):
    source = tmp_path / 'accounts.sqlite3'
    monkeypatch.setenv('MASR_USER_DB', str(source))
    accounts._DB = source
    try:
        accounts.setup()
        with pytest.raises(ValueError, match='OUTSIDE the project'):
            backup_tool.backup(backup_tool.ROOT / 'data-private')
    finally:
        accounts._DB = None


def test_review_backup_preserves_votes_and_comments(tmp_path, monkeypatch):
    from app.database import initialize
    from app.ratings import setup as setup_ratings

    source = tmp_path / 'tourism.sqlite3'
    monkeypatch.setenv('DATABASE_PATH', str(source))
    initialize()
    setup_ratings()
    with closing(sqlite3.connect(source)) as con:
        con.execute("INSERT INTO visitor_ratings (target_id, voter_hash, rating) VALUES ('giza-pyramids', 'account:test', 5)")
        con.execute("INSERT INTO visitor_comments (target_id, voter_hash, display_name, comment) VALUES ('giza-pyramids', 'account:test', 'Traveler #1', 'A memorable visit.')")
        con.commit()

    saved = backup_tool.backup_reviews(tmp_path / 'private-backups')
    assert backup_tool.verify_reviews_db(saved)['ratings'] == 1
    assert backup_tool.verify_reviews_db(saved)['comments'] == 1
    with closing(sqlite3.connect(source)) as con:
        con.execute('DELETE FROM visitor_ratings')
        con.execute('DELETE FROM visitor_comments')
        con.commit()
    assert backup_tool.verify_reviews_db(saved)['ratings'] == 1
    with closing(sqlite3.connect(saved)) as con:
        con.execute('DROP TABLE visitor_comments')
    with pytest.raises(ValueError, match='Required rating and comment tables'):
        backup_tool.verify_reviews_db(saved)
    with pytest.raises(ValueError, match='OUTSIDE the project'):
        backup_tool.backup_reviews(backup_tool.ROOT / 'data-private')
