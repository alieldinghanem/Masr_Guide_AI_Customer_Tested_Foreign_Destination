"""SQLite persistence for the publicly curated places catalog."""
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from .catalog import PLACES

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "tourism.db"


def db_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB)))


def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=10)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    """(Re)build the places table from the code catalogue, atomically.

    The table is a derived cache of `catalog.PLACES`, so it is rebuilt on every start-up to keep
    schema and data in sync across upgrades. The DROP/CREATE/INSERT run in ONE explicit
    transaction (BEGIN IMMEDIATE also serialises concurrent workers), so concurrent readers
    see either the old table or the complete new one, never a missing or half-filled table.
    (Python's sqlite3 does not open a transaction before DDL, hence the explicit BEGIN.)
    """
    db = connect()
    db.isolation_level = None  # manual transaction control
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DROP TABLE IF EXISTS places")
        db.execute("""CREATE TABLE places (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, name_ar TEXT NOT NULL, city TEXT NOT NULL,
          category TEXT NOT NULL, tags TEXT NOT NULL,
          lat REAL NOT NULL, lng REAL NOT NULL, visit_minutes INTEGER NOT NULL,
          description TEXT NOT NULL, summary_ar TEXT NOT NULL, details TEXT NOT NULL,
          tip TEXT NOT NULL, tip_ar TEXT NOT NULL,
          source_url TEXT NOT NULL, family_friendly INTEGER NOT NULL)""")
        db.executemany("""INSERT INTO places
         (id, name, name_ar, city, category, tags, lat, lng, visit_minutes, description,
          summary_ar, details, tip, tip_ar, source_url, family_friendly)
         VALUES (:id, :name, :name_ar, :city, :category, :tags, :lat, :lng, :visit_minutes,
                 :description, :summary_ar, :details, :tip, :tip_ar, :source_url, :family_friendly)""",
         [{**p, "tags": json.dumps(p["tags"]), "family_friendly": int(p["family_friendly"])} for p in PLACES])
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()


def to_place(row):
    if row is None: return None
    d = dict(row)
    d["tags"] = json.loads(d["tags"])
    d["family_friendly"] = bool(d["family_friendly"])
    return d


def all_places(city=None, interest=None, q=None):
    with closing(connect()) as db:
        rows = db.execute("SELECT * FROM places ORDER BY city, name").fetchall()
    items = [to_place(r) for r in rows]
    if city: items = [p for p in items if p["city"].lower() == city.lower()]
    if interest: items = [p for p in items if interest.lower() in p["tags"]]
    if q:
        q = q.casefold().strip()
        items = [p for p in items if q in " ".join(
            [p["name"], p["name_ar"], p["city"], p["description"], p["summary_ar"]]).casefold()]
    return items


def get_place(slug):
    with closing(connect()) as db:
        row = db.execute("SELECT * FROM places WHERE id = ?", (slug,)).fetchone()
    return to_place(row)
