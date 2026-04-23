from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from contest_radar.cli import (
    _capture_notification_screenshots,
    _cmd_send_test,
    _digest_notification_records,
    _due_soon_notification_records,
    _maybe_notify,
)


class CLINotificationTest(unittest.TestCase):
    @patch("contest_radar.cli.send_message")
    def test_send_test_keeps_plain_text_telegram_path(self, mock_send):
        args = SimpleNamespace(bot_token="dummy", chat_id=123456, text="ping")
        code = _cmd_send_test(args)
        self.assertEqual(code, 0)
        mock_send.assert_called_once_with("dummy", 123456, "ping")

    @patch("contest_radar.cli.send_message_with_photos")
    def test_maybe_notify_sends_digest_with_screenshot_photos(self, mock_send):
        mock_send.return_value = {"ok": True}
        args = SimpleNamespace(notify=True, bot_token="dummy", chat_id=123456)
        with tempfile.TemporaryDirectory() as tmpdir:
            photo = Path(tmpdir) / "detail.png"
            photo.write_bytes(b"fake png")
            code = _maybe_notify(args, "digest text", [photo])
        self.assertEqual(code, 0)
        mock_send.assert_called_once_with("dummy", 123456, "digest text", [photo])

    @patch("contest_radar.cli.capture_url_screenshot")
    def test_capture_notification_screenshots_captures_top_record_urls(self, mock_capture):
        def fake_capture(url, output_path, wait_seconds=0):
            path = Path(output_path)
            path.write_bytes(f"shot:{url}".encode("utf-8"))
            return path

        mock_capture.side_effect = fake_capture
        records = [
            SimpleNamespace(fingerprint="abc123", title="첫 공공 AI 공모전", url="https://example.com/first"),
            SimpleNamespace(fingerprint="def456", title="둘째 공모전", url="https://example.com/second"),
            SimpleNamespace(fingerprint="ghi789", title="셋째 공모전", url="https://example.com/third"),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = _capture_notification_screenshots(records, top_n=2, output_dir=Path(tmpdir), wait_seconds=0)

        self.assertEqual(len(paths), 2)
        self.assertEqual([call.args[0] for call in mock_capture.call_args_list], ["https://example.com/first", "https://example.com/second"])
        self.assertEqual([path.name for path in paths], ["01-abc123.png", "02-def456.png"])

    def test_due_soon_screenshot_records_match_digest_buckets(self):
        today = date(2026, 4, 23)
        records = [
            SimpleNamespace(url="https://example.com/due-7-high", deadline_date_iso=(today + timedelta(days=7)).isoformat(), score=90),
            SimpleNamespace(url="https://example.com/not-due", deadline_date_iso=(today + timedelta(days=5)).isoformat(), score=99),
            SimpleNamespace(url="https://example.com/due-1", deadline_date_iso=(today + timedelta(days=1)).isoformat(), score=70),
        ]
        selected = _due_soon_notification_records(records, today=today)
        self.assertEqual([record.url for record in selected], ["https://example.com/due-7-high", "https://example.com/due-1"])

    def test_digest_screenshot_records_follow_score_sorted_digest_order(self):
        records = [
            SimpleNamespace(url="https://example.com/low", score=10),
            SimpleNamespace(url="https://example.com/high", score=90),
            SimpleNamespace(url="https://example.com/mid", score=50),
        ]
        selected = _digest_notification_records(records, top_n=2)
        self.assertEqual([record.url for record in selected], ["https://example.com/high", "https://example.com/mid"])


if __name__ == "__main__":
    unittest.main()
