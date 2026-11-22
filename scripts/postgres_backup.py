"""Operator-only PostgreSQL backup and isolated, empty-target restore drill.

Credentials are read from environment, never printed or passed on the command
line. Backups contain sensitive account data and must remain outside the repo.
Uses installed PostgreSQL pg_dump/pg_restore tools; never cleans or overwrites
existing target tables. This is not a claim that a live Neon restore was run.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def _settings(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('postgres', 'postgresql') or not parsed.hostname or not parsed.path.strip('/'):
        raise ValueError('A PostgreSQL database URL is required')
    default_ssl = 'disable' if parsed.hostname in ('localhost', '127.0.0.1', '::1') else 'require'
    sslmode = parse_qs(parsed.query).get('sslmode', [default_ssl])[0]
    if sslmode not in ('require', 'verify-full', 'verify-ca') and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('Remote database connections require TLS')
    return {'PGHOST': parsed.hostname, 'PGPORT': str(parsed.port or 5432),
            'PGDATABASE': unquote(parsed.path.strip('/')), 'PGUSER': unquote(parsed.username or ''),
            'PGPASSWORD': unquote(parsed.password or ''), 'PGSSLMODE': sslmode}


def _private_path(path):
    path = Path(path).expanduser().resolve()
    if path == ROOT or ROOT in path.parents:
        raise ValueError('Store sensitive backups outside the repository')
    return path


def _run(program, args, settings):
    executable = shutil.which(program)
    if not executable:
        raise ValueError('Install matching PostgreSQL client tools first')
    result = subprocess.run([executable, *args], env={**os.environ, **settings}, capture_output=True, timeout=600)
    if result.returncode:
        raise ValueError('PostgreSQL operation failed; no restore success is claimed')


def backup(source_url, destination):
    import psycopg
    settings = _settings(source_url)
    destination = _private_path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidentally replacing an earlier backup.
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with psycopg.connect(source_url, sslmode=settings['PGSSLMODE'], connect_timeout=10) as db:
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            snapshot = db.execute('SELECT pg_export_snapshot()').fetchone()[0]
            counts = {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                      for table in ('account_users', 'account_trips', 'account_conversations', 'visitor_ratings', 'visitor_comments')}
            _run('pg_dump', ['--format=custom', '--no-owner', '--no-privileges', '--snapshot', snapshot, '--file', str(destination)], settings)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        _run('pg_restore', ['--list', str(destination)], settings)
        manifest = destination.with_suffix(destination.suffix + '.json')
        with manifest.open('x', encoding='ascii') as handle:
            json.dump({'sha256': digest, 'counts': counts}, handle)
        manifest.chmod(0o600)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {'sha256': digest, 'archive_verified': True}


def restore_drill(source_url, target_url, archive):
    import psycopg
    source = _settings(source_url)
    target = _settings(target_url)
    if all(source[key] == target[key] for key in ('PGHOST', 'PGPORT', 'PGDATABASE')):
        raise ValueError('Restore target must be a separate empty database')
    archive = _private_path(archive)
    manifest = json.loads(archive.with_suffix(archive.suffix + '.json').read_text(encoding='ascii'))
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError('Backup checksum does not match')
    with psycopg.connect(target_url, sslmode=target['PGSSLMODE'], connect_timeout=10) as db:
        found = db.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')").fetchone()[0]
        if found:
            raise ValueError('Restore target is not empty; no tables were changed')
    _run('pg_restore', ['--dbname', target['PGDATABASE'], '--single-transaction', '--exit-on-error', '--no-owner', '--no-privileges', str(archive)], target)
    with psycopg.connect(target_url, sslmode=target['PGSSLMODE'], connect_timeout=10) as db:
        counts = {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                  for table in ('account_users', 'account_trips', 'account_conversations', 'visitor_ratings', 'visitor_comments')}
        orphaned = db.execute('''SELECT COUNT(*) FROM account_trips t LEFT JOIN account_users u ON u.id=t.user_id
                                 WHERE u.id IS NULL''').fetchone()[0]
        if orphaned:
            raise ValueError('Restored database has orphaned trips')
        if counts != manifest['counts']:
            raise ValueError('Restored counts do not match the backup snapshot')
    return {'restored': True, 'counts': counts}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'restore-drill'])
    parser.add_argument('--file', required=True)
    args = parser.parse_args()
    try:
        source_url = os.environ['NEON_DATABASE_URL']
        result = backup(source_url, args.file) if args.action == 'backup' else restore_drill(source_url, os.environ['MASR_RESTORE_DATABASE_URL'], args.file)
        print(json.dumps(result))
    except Exception:
        raise SystemExit('Operation not completed. Check private configuration, database isolation and client tools. No credentials are printed.')
