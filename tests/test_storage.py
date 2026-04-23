from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from contest_radar.storage import init_db


class StorageMigrationTest(unittest.TestCase):
    def test_init_db_migrates_old_contests_table_before_deadline_index_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "old.sqlite3"
            with sqlite3.connect(db_path) as conn:
                conn.executescript(
                    """
                    CREATE TABLE contests (
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
                    """
                )
            init_db(db_path)
            with sqlite3.connect(db_path) as conn:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(contests)").fetchall()}
                indexes = {row[1] for row in conn.execute("PRAGMA index_list(contests)").fetchall()}
            self.assertIn("deadline_date_iso", columns)
            self.assertIn("detail_title", columns)
            self.assertIn("idx_contests_deadline", indexes)


if __name__ == "__main__":
    unittest.main()
