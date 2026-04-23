from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from contest_radar.telegram import resolve_master_ids, send_message, send_message_with_photos


class TelegramTest(unittest.TestCase):
    @patch("contest_radar.telegram._api_get")
    def test_resolve_master_ids_reads_updates(self, mock_api_get):
        mock_api_get.return_value = {
            "ok": True,
            "result": [
                {
                    "update_id": 1,
                    "message": {
                        "text": "/start",
                        "chat": {"id": 123456, "type": "private", "first_name": "TestUser"},
                    },
                }
            ],
        }
        chats = resolve_master_ids("dummy")
        self.assertEqual(len(chats), 1)
        self.assertEqual(chats[0].chat_id, 123456)
        self.assertEqual(chats[0].first_name, "TestUser")

    @patch("contest_radar.telegram._api_post")
    def test_send_message_delegates_to_api_post(self, mock_api_post):
        mock_api_post.return_value = {"ok": True, "result": {"message_id": 1}}
        response = send_message("dummy", 123456, "hello")
        self.assertTrue(response["ok"])
        mock_api_post.assert_called_once()

    @patch("contest_radar.telegram._api_multipart")
    @patch("contest_radar.telegram._api_post")
    def test_send_message_with_photos_sends_text_then_screenshot(self, mock_api_post, mock_api_multipart):
        mock_api_post.return_value = {"ok": True, "result": {"message_id": 1}}
        mock_api_multipart.return_value = {"ok": True, "result": {"message_id": 2}}
        with tempfile.TemporaryDirectory() as tmpdir:
            screenshot_path = Path(tmpdir) / "detail.png"
            screenshot_path.write_bytes(b"fake png bytes")
            response = send_message_with_photos("dummy", 123456, "hello", [screenshot_path])
        self.assertTrue(response["ok"])
        mock_api_post.assert_called_once_with("dummy", "sendMessage", {"chat_id": "123456", "text": "hello"})
        mock_api_multipart.assert_called_once()
        args, _kwargs = mock_api_multipart.call_args
        self.assertEqual(args[0:3], ("dummy", "sendPhoto", {"chat_id": "123456"}))
        self.assertEqual(args[3]["photo"][0], "detail.png")
        self.assertEqual(args[3]["photo"][2], "image/png")


if __name__ == "__main__":
    unittest.main()
