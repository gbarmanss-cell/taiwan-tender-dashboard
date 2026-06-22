from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS tenders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    agency TEXT,
    notice_date TEXT,
    deadline TEXT,
    budget INTEGER,
    category TEXT,
    source_url TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tenders_notice_date ON tenders(notice_date DESC);
CREATE INDEX IF NOT EXISTS idx_tenders_agency ON tenders(agency);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_tenders(conn: sqlite3.Connection, rows: Iterable[dict]) -> int:
    sql = """
    INSERT INTO tenders (
        source_key, title, agency, notice_date, deadline,
        budget, category, source_url, fetched_at
    ) VALUES (
        :source_key, :title, :agency, :notice_date, :deadline,
        :budget, :category, :source_url, :fetched_at
    )
    ON CONFLICT(source_key) DO UPDATE SET
        title=excluded.title,
        agency=excluded.agency,
        notice_date=excluded.notice_date,
        deadline=excluded.deadline,
        budget=excluded.budget,
        category=excluded.category,
        source_url=excluded.source_url,
        fetched_at=excluded.fetched_at
    """
    count = 0
    with conn:
        for row in rows:
            conn.execute(sql, row)
            count += 1
    return count
