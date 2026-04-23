from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from contest_radar.pipeline import run_once


class PipelineTest(unittest.TestCase):
    @patch("contest_radar.pipeline.safe_collect_source")
    def test_run_once_dedupes_before_scoring(self, mock_safe_collect_source):
        from contest_radar.models import RawListing

        def fake_collect(source, defaults):
            return [
                RawListing(source_id=source.id, source_name=source.name, source_url=source.url, title="테스트 공모전", url="https://example.com/1"),
                RawListing(source_id=source.id, source_name=source.name, source_url=source.url, title="테스트 공모전", url="https://example.com/1"),
            ], None

        mock_safe_collect_source.side_effect = fake_collect
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "radar.sqlite3")
            result = run_once(db_path=db_path)
        self.assertGreater(result["collected_count"], result["deduped_count"])
        self.assertEqual(len(result["records"]), result["deduped_count"])


if __name__ == "__main__":
    unittest.main()
