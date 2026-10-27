"""Small sqlite store: favourites, settings, cached replies, external ids.

Every call opens and closes its own connection. Streamlit runs the script on a
thread per session and a shared sqlite connection is not safe across threads;
the tables here hold tens of rows, so the overhead is irrelevant.

Values are stored as JSON so callers can keep passing plain dicts, and a
schema change never needs a migration as long as the keys stay compatible.
"""

import json
import sqlite3
import time
from typing import Any, Dict, Iterable, List, Optional

from models.performer import Performer
from paths import db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS favorites (
    slug       TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    payload    TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cache (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS external_ids (
    slug        TEXT NOT NULL,
    source      TEXT NOT NULL,
    external_id TEXT NOT NULL,
    payload     TEXT,
    PRIMARY KEY (slug, source)
);
"""


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(db_path(), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.executescript(_SCHEMA)
    return connection


def _query(sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    connection = _connect()
    try:
        return connection.execute(sql, params).fetchall()
    finally:
        connection.close()


def _write(sql: str, params: tuple = ()) -> None:
    connection = _connect()
    try:
        with connection:
            connection.execute(sql, params)
    finally:
        connection.close()


# --- favourites -----------------------------------------------------------

def add_favorite(performer: Performer) -> None:
    """Store (or refresh) a performer as a favourite.

    The whole ``to_dict()`` payload is kept, so favourites still render after
    the source page is gone or the filters no longer match them.
    """
    _write(
        "INSERT OR REPLACE INTO favorites (slug, name, payload, created_at) VALUES (?, ?, ?, ?)",
        (performer.slug, performer.name, json.dumps(performer.to_dict()), time.time()),
    )


def remove_favorite(slug: str) -> None:
    _write("DELETE FROM favorites WHERE slug = ?", (slug,))


def is_favorite(slug: str) -> bool:
    return bool(_query("SELECT 1 FROM favorites WHERE slug = ? LIMIT 1", (slug,)))


def toggle_favorite(performer: Performer) -> bool:
    """Flip a performer's favourite state; return the new state."""
    if is_favorite(performer.slug):
        remove_favorite(performer.slug)
        return False
    add_favorite(performer)
    return True


def favorite_slugs() -> set:
    return {row["slug"] for row in _query("SELECT slug FROM favorites")}


def list_favorites(limit: Optional[int] = None) -> List[Performer]:
    """Return favourites, newest first."""
    sql = "SELECT payload FROM favorites ORDER BY created_at DESC"
    params: tuple = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (limit,)

    performers = []
    for row in _query(sql, params):
        try:
            performers.append(Performer.from_dict(json.loads(row["payload"])))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue  # a hand-edited or half-written row must not break the grid
    return performers


def export_favorites() -> List[Dict[str, Any]]:
    """Return favourites as JSON-serialisable dicts."""
    return [json.loads(row["payload"]) for row in _query("SELECT payload FROM favorites")]


def import_favorites(rows: Iterable[Dict[str, Any]]) -> int:
    """Merge exported dicts into the store; return how many were new."""
    existing = favorite_slugs()
    added = 0
    for row in rows or []:
        try:
            performer = Performer.from_dict(row)
        except (TypeError, ValueError):
            continue
        if performer.slug not in existing:
            add_favorite(performer)
            existing.add(performer.slug)
            added += 1
    return added


# --- settings -------------------------------------------------------------

def get_setting(key: str, default: Any = None) -> Any:
    rows = _query("SELECT value FROM settings WHERE key = ?", (key,))
    if not rows:
        return default
    try:
        return json.loads(rows[0]["value"])
    except json.JSONDecodeError:
        return default


def set_setting(key: str, value: Any) -> None:
    _write(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, json.dumps(value)),
    )


# --- cached replies -------------------------------------------------------

def cache_get(key: str) -> Any:
    """Return a cached value, or ``None`` when missing or expired."""
    rows = _query("SELECT value, expires_at FROM cache WHERE key = ?", (key,))
    if not rows:
        return None
    if rows[0]["expires_at"] < time.time():
        _write("DELETE FROM cache WHERE key = ?", (key,))
        return None
    try:
        return json.loads(rows[0]["value"])
    except json.JSONDecodeError:
        return None


def cache_set(key: str, value: Any, ttl_seconds: float) -> None:
    now = time.time()
    _write(
        "INSERT OR REPLACE INTO cache (key, value, fetched_at, expires_at) VALUES (?, ?, ?, ?)",
        (key, json.dumps(value), now, now + ttl_seconds),
    )


def cache_clear(prefix: str = "") -> None:
    _write("DELETE FROM cache WHERE key LIKE ?", (f"{prefix}%",))


# --- external ids ---------------------------------------------------------

def set_external_id(
    slug: str, source: str, external_id: str, payload: Optional[Dict[str, Any]] = None
) -> None:
    _write(
        "INSERT OR REPLACE INTO external_ids (slug, source, external_id, payload)"
        " VALUES (?, ?, ?, ?)",
        (slug, source, external_id, json.dumps(payload) if payload is not None else None),
    )


def get_external_id(slug: str, source: str) -> Optional[str]:
    rows = _query(
        "SELECT external_id FROM external_ids WHERE slug = ? AND source = ?", (slug, source)
    )
    return rows[0]["external_id"] if rows else None


def get_external_record(slug: str, source: str) -> Optional[Dict[str, Any]]:
    rows = _query(
        "SELECT external_id, payload FROM external_ids WHERE slug = ? AND source = ?",
        (slug, source),
    )
    if not rows:
        return None
    payload = rows[0]["payload"]
    return {
        "external_id": rows[0]["external_id"],
        "payload": json.loads(payload) if payload else {},
    }
