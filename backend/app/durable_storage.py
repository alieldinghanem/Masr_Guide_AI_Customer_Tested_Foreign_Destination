"""PostgreSQL bridge for persistent traveler data on free web hosting."""
import os
import sqlite3
from urllib.parse import urlparse


def configured() -> bool:
    return bool(os.getenv('NEON_DATABASE_URL', '').strip())


class _Row(dict):
    """Support sqlite.Row's key and numeric lookup contract."""

    def __init__(self, names, values):
        super().__init__(zip(names, values))
        self._values = tuple(values)

    def __getitem__(self, key):
        return self._values[key] if isinstance(key, int) else super().__getitem__(key)


def _row_factory(cursor):
    names = [column.name for column in (cursor.description or ())]
    return lambda values: _Row(names, values)


class PostgresConnection:
    def __init__(self):
        import psycopg

        url = os.environ['NEON_DATABASE_URL'].strip()
        if not url.startswith(('postgresql://', 'postgres://')):
            raise ValueError('NEON_DATABASE_URL must be a PostgreSQL URL')
        host = urlparse(url).hostname
        sslmode = ('disable' if host in {'localhost', '127.0.0.1', '::1'}
                   and os.getenv('APP_ENV', '').lower() != 'production' else 'require')
        self._db = psycopg.connect(url, sslmode=sslmode, connect_timeout=10,
                                   row_factory=_row_factory)

    def execute(self, query, params=()):
        import psycopg

        if query.strip().upper() == 'BEGIN IMMEDIATE':
            # Serialize the favorites cap check as SQLite does.
            query = 'SELECT pg_advisory_xact_lock(83712631)'
        else:
            query = query.replace('?', '%s').replace(
                'DEFAULT CURRENT_TIMESTAMP', 'DEFAULT (CURRENT_TIMESTAMP::TEXT)')
        try:
            return self._db.execute(query, params)
        except psycopg.errors.UniqueViolation as exc:
            raise sqlite3.IntegrityError(str(exc)) from exc

    def executescript(self, script):
        for statement in script.split(';'):
            if statement.strip():
                self.execute(statement)

    def commit(self):
        self._db.commit()

    def close(self):
        self._db.close()

    def __enter__(self):
        self._db.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._db.__exit__(exc_type, exc_value, traceback)


def connect_traveler():
    if not configured():
        raise ValueError('NEON_DATABASE_URL is not configured')
    return PostgresConnection()
