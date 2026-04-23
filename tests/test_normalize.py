from __future__ import annotations

import unittest
from datetime import date

from contest_radar.normalize import extract_deadline_date_iso


class NormalizeDeadlineTest(unittest.TestCase):
    def test_extract_deadline_date_iso_handles_partial_range_end_date(self):
        self.assertEqual(
            extract_deadline_date_iso("접수기간 2026-03-25 ~ 5.13", today=date(2026, 4, 23)),
            "2026-05-13",
        )

    def test_extract_deadline_date_iso_handles_partial_end_only_date(self):
        self.assertEqual(
            extract_deadline_date_iso("마감일 5.13", today=date(2026, 4, 23)),
            "2026-05-13",
        )

    def test_extract_deadline_date_iso_handles_start_end_with_partial_deadline(self):
        self.assertEqual(
            extract_deadline_date_iso("시작일 2026.03.25 마감일 5.13", today=date(2026, 4, 23)),
            "2026-05-13",
        )


if __name__ == "__main__":
    unittest.main()
