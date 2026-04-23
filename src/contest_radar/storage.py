from __future__ import annotations

import json
import re
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
    deadline_date_iso TEXT,
    detail_title TEXT,
    detail_date_text TEXT,
    detail_content TEXT,
    host_guess TEXT,
    reasons_json TEXT NOT NULL,
    penalties_json TEXT NOT NULL,
    raw_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL,
    item_count INTEGER NOT NULL,
    error_text TEXT
);
"""

INDEX_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_contests_repeat_key ON contests(repeat_key);
CREATE INDEX IF NOT EXISTS idx_contests_score ON contests(score DESC);
CREATE INDEX IF NOT EXISTS idx_contests_last_seen ON contests(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_contests_deadline ON contests(deadline_date_iso);
"""

_REQUIRED_CONTEST_COLUMNS = {
    "deadline_date_iso": "TEXT",
    "detail_title": "TEXT",
    "detail_date_text": "TEXT",
    "detail_content": "TEXT",
}
_COLUMN_IDENTIFIER_RE = re.compile(r"^[a-z_]+$")
_ALLOWED_COLUMN_TYPES = {"TEXT"}


def connect(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema_compatibility(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(contests)").fetchall()}
    for column_name, column_type in _REQUIRED_CONTEST_COLUMNS.items():
        if column_name not in existing:
            if not _COLUMN_IDENTIFIER_RE.match(column_name) or column_type not in _ALLOWED_COLUMN_TYPES:
                raise ValueError(f"Unsafe schema migration column: {column_name} {column_type}")
            statement = "ALTER TABLE contests ADD COLUMN " + column_name + " " + column_type
            conn.execute(statement)
    conn.commit()


def init_db(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _ensure_schema_compatibility(conn)
        conn.executescript(INDEX_SCHEMA)
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


def lookup_existing_fingerprints(conn: sqlite3.Connection, fingerprints: Iterable[str]) -> set[str]:
    keys = sorted({fingerprint for fingerprint in fingerprints if fingerprint})
    if not keys:
        return set()
    placeholders = ",".join("?" for _ in keys)
    rows = conn.execute(
        f"SELECT fingerprint FROM contests WHERE fingerprint IN ({placeholders})",
        keys,
    ).fetchall()
    return {str(row["fingerprint"]) for row in rows}


def row_to_record(row: sqlite3.Row) -> ContestRecord:
    return ContestRecord(
        fingerprint=row["fingerprint"],
        normalized_title=row["normalized_title"],
        title=row["title"],
        url=row["url"],
        source_id=row["source_id"],
        source_name=row["source_name"],
        source_url=row["source_url"],
        snippet=row["snippet"] or "",
        observed_at=row["last_seen_at"],
        lane=row["lane"],
        lane_display_name=row["lane_display_name"],
        score=int(row["score"]),
        public_sector=bool(row["public_sector"]),
        ai_fit=row["ai_fit"],
        user_fit=row["user_fit"],
        repeat_count=int(row["repeat_count"]),
        prize_amount_krw=row["prize_amount_krw"],
        deadline_text=row["deadline_text"],
        deadline_date_iso=row["deadline_date_iso"],
        detail_title=row["detail_title"],
        detail_date_text=row["detail_date_text"],
        detail_content=row["detail_content"],
        host_guess=row["host_guess"],
        reasons=json.loads(row["reasons_json"]),
        penalties=json.loads(row["penalties_json"]),
        raw=json.loads(row["raw_json"]),
    )


def fetch_all_records(conn: sqlite3.Connection, limit: int = 500) -> list[ContestRecord]:
    rows = conn.execute(
        "SELECT * FROM contests ORDER BY score DESC, last_seen_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [row_to_record(row) for row in rows]


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
                ai_fit, user_fit, repeat_count, prize_amount_krw, deadline_text, deadline_date_iso,
                detail_title, detail_date_text, detail_content, host_guess,
                reasons_json, penalties_json, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                deadline_date_iso=excluded.deadline_date_iso,
                detail_title=excluded.detail_title,
                detail_date_text=excluded.detail_date_text,
                detail_content=excluded.detail_content,
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
                record.deadline_date_iso,
                record.detail_title,
                record.detail_date_text,
                record.detail_content,
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
