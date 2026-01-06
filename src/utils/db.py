from __future__ import annotations

import sqlite3
from typing import Iterable, Sequence


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def execute_script(conn: sqlite3.Connection, sql: str) -> None:
    conn.executescript(sql)


def bulk_insert(
    conn: sqlite3.Connection,
    table: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[object]],
    chunk_size: int = 5000,
) -> None:
    cols = ",".join(columns)
    placeholders = ",".join(["?"] * len(columns))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"

    buf: list[Sequence[object]] = []
    cur = conn.cursor()
    for r in rows:
        buf.append(r)
        if len(buf) >= chunk_size:
            cur.executemany(sql, buf)
            buf.clear()
    if buf:
        cur.executemany(sql, buf)


def bulk_update(
    conn: sqlite3.Connection,
    sql: str,
    rows: Iterable[Sequence[object]],
    chunk_size: int = 5000,
) -> None:
    buf: list[Sequence[object]] = []
    cur = conn.cursor()
    for r in rows:
        buf.append(r)
        if len(buf) >= chunk_size:
            cur.executemany(sql, buf)
            buf.clear()
    if buf:
        cur.executemany(sql, buf)
