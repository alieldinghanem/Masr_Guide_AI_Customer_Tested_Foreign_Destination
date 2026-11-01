"""Consistent SQLite account backup and offline restore rehearsal.

Run from the project root:
  python scripts/storage_backup.py backup --output ./private-backups
  python scripts/storage_backup.py verify --file ./private-backups/traveler-....sqlite3

This captures account data with the SQLite backup API even while WAL is active.
Protect backups as sensitive: they contain emails, password verifiers and trips.
Never place backups in Git or the static site directory.
"""
import argparse
import hashlib
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USER_DB = ROOT / 'backend' / 'data' / 'traveler.sqlite3'


def source_path():
    return Path(os.getenv('MASR_USER_DB') or DEFAULT_USER_DB).expanduser().resolve()


def verify_db(path: Path) -> dict:
    if not path.is_file():
        raise ValueError('Database backup file does not exist')
    # SQLite read-only URI ensures verification never modifies the backup.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as con:
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok':
            raise ValueError('SQLite integrity_check failed')
        required = {'account_users', 'account_tokens', 'account_trips', 'account_conversations'}
        found = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required.issubset(found):
            raise ValueError('Required account tables are absent')
        foreign_keys = con.execute('PRAGMA foreign_key_check').fetchall()
        if foreign_keys:
            raise ValueError('Database has orphaned foreign-key references')
        users = con.execute('SELECT count(*) FROM account_users').fetchone()[0]
        trips = con.execute('SELECT count(*) FROM account_trips').fetchone()[0]
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'sha256': checksum, 'users': users, 'trips': trips}


def backup(output: Path) -> Path:
    source = source_path()
    if not source.is_file():
        raise ValueError('Account database does not exist; start the backend first')
    output = output.expanduser().resolve()
    # Never store sensitive backups in project, where they can be published accidentally.
    if output == ROOT or ROOT in output.parents:
        raise ValueError('Choose a private directory OUTSIDE the project for backups')
    output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = output / f'traveler-{timestamp}.sqlite3'
    # SQLite's online backup API gives a consistent snapshot even with WAL writers.
    with closing(sqlite3.connect(source)) as origin:
        with closing(sqlite3.connect(destination)) as dest:
            origin.backup(dest)
    try:
        destination.chmod(0o600)
        result = verify_db(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    # Only non-secret counters/digest are printed; backups must stay private.
    print(f'PASS backup: {destination}\nSHA256: {result["sha256"]}\nRows: users={result["users"]}, trips={result["trips"]}')
    return destination


def main():
    p = argparse.ArgumentParser(description='Private SQLite account backup and integrity verification')
    cmd = p.add_subparsers(dest='command', required=True)
    b = cmd.add_parser('backup'); b.add_argument('--output', required=True, type=Path)
    v = cmd.add_parser('verify'); v.add_argument('--file', required=True, type=Path)
    args = p.parse_args()
    if args.command == 'backup':
        backup(args.output)
    else:
        print(f'PASS verify: {verify_db(args.file.resolve())}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, sqlite3.Error) as exc:
        raise SystemExit(f'FAIL: {exc}') from None
