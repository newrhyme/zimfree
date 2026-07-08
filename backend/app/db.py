"""SQLite connection helper for data/processed/app.db."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .schema import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Return a connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def query(sql: str, params: tuple = ()) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    with connection() as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None
