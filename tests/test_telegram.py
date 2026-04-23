from __future__ import annotations

import unittest
from unittest.mock import patch

from contest_radar.telegram import resolve_master_ids, send_message


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


if __name__ == "__main__":
    unittest.main()
