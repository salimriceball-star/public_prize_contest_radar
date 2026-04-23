from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from .models import ContestRecord
from .normalize import repeat_key_from_title


SCHEMA = """
CREATE TABLE IF NOT EXISTS contests (
    fingerprint TEXT PRIMARY KEY,
    repeat_key TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    snippet TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    lane TEXT NOT NULL,
    lane_display_name TEXT NOT NULL,
    score INTEGER NOT NULL,
    public_sector INTEGER NOT NULL,
    ai_fit TEXT NOT NULL,
    user_fit TEXT NOT NULL,
    repeat_count INTEGER NOT NULL,
    prize_amount_krw INTEGER,
    deadline_text TEXT,
    host_guess TEXT,
    reasons_json TEXT NOT NULL,
    penalties_json TEXT NOT NULL,
    raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_contests_repeat_key ON contests(repeat_key);
CREATE INDEX IF NOT EXISTS idx_contests_score ON contests(score DESC);
CREATE INDEX IF NOT EXISTS idx_contests_last_seen ON contests(last_seen_at DESC);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL,
    item_count INTEGER NOT NULL,
    error_text TEXT
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def lookup_repeat_counts(conn: sqlite3.Connection, titles: Iterable[str]) -> dict[str, int]:
    keys = sorted({repeat_key_from_title(title) for title in titles if title})
    if not keys:
        return {}
    placeholders = ",".join("?" for _ in keys)
    rows = conn.execute(
        f"SELECT repeat_key, COUNT(*) AS seen_count FROM contests WHERE repeat_key IN ({placeholders}) GROUP BY repeat_key",
        keys,
    ).fetchall()
    return {row["repeat_key"]: int(row["seen_count"]) for row in rows}


def upsert_records(conn: sqlite3.Connection, records: Iterable[ContestRecord]) -> int:
    inserted = 0
    for record in records:
        repeat_key = repeat_key_from_title(record.title)
        existing = conn.execute(
            "SELECT fingerprint, first_seen_at FROM contests WHERE fingerprint = ?",
            (record.fingerprint,),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO contests (
                fingerprint, repeat_key, normalized_title, title, url, source_id, source_name, source_url,
                snippet, first_seen_at, last_seen_at, lane, lane_display_name, score, public_sector,
                ai_fit, user_fit, repeat_count, prize_amount_krw, deadline_text, host_guess,
                reasons_json, penalties_json, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                repeat_key=excluded.repeat_key,
                normalized_title=excluded.normalized_title,
                title=excluded.title,
                url=excluded.url,
                source_id=excluded.source_id,
                source_name=excluded.source_name,
                source_url=excluded.source_url,
                snippet=excluded.snippet,
                last_seen_at=excluded.last_seen_at,
                lane=excluded.lane,
                lane_display_name=excluded.lane_display_name,
                score=excluded.score,
                public_sector=excluded.public_sector,
                ai_fit=excluded.ai_fit,
                user_fit=excluded.user_fit,
                repeat_count=excluded.repeat_count,
                prize_amount_krw=excluded.prize_amount_krw,
                deadline_text=excluded.deadline_text,
                host_guess=excluded.host_guess,
                reasons_json=excluded.reasons_json,
                penalties_json=excluded.penalties_json,
                raw_json=excluded.raw_json
            """,
            (
                record.fingerprint,
                repeat_key,
                record.normalized_title,
                record.title,
                record.url,
                record.source_id,
                record.source_name,
                record.source_url,
                record.snippet,
                existing["first_seen_at"] if existing else record.observed_at,
                record.observed_at,
                record.lane,
                record.lane_display_name,
                record.score,
                int(record.public_sector),
                record.ai_fit,
                record.user_fit,
                record.repeat_count,
                record.prize_amount_krw,
                record.deadline_text,
                record.host_guess,
                json.dumps(record.reasons, ensure_ascii=False),
                json.dumps(record.penalties, ensure_ascii=False),
                json.dumps(record.raw, ensure_ascii=False),
            ),
        )
        if not existing:
            inserted += 1
    conn.commit()
    return inserted


def record_run(conn: sqlite3.Connection, run_id: str, started_at: str, source_id: str, status: str, item_count: int, error_text: str | None) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO runs (run_id, started_at, source_id, status, item_count, error_text) VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, started_at, source_id, status, item_count, error_text),
    )
    conn.commit()
