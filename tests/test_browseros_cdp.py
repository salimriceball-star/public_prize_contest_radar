from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from contest_radar.browseros_cdp import (
    BrowserOSPage,
    BrowserOSUnavailable,
    CDPPageSession,
    capture_url_screenshot,
    ensure_browseros_running,
    evaluate_url,
    find_reusable_page,
    normalize_cdp_url,
    open_page,
)
from contest_radar.config_loader import load_yaml


class BrowserOSCDPTest(unittest.TestCase):
    def test_find_reusable_page_prefers_exact_existing_tab(self):
        pages = [
            {
                "id": "tab-1",
                "type": "page",
                "url": "https://www.wevity.com/?c=find&s=1&gub=1",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9100/devtools/page/tab-1",
            },
            {
                "id": "tab-2",
                "type": "page",
                "url": "https://www.linkareer.com/list/contest",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9100/devtools/page/tab-2",
            },
        ]
        reused = find_reusable_page("https://www.wevity.com/?c=find&s=1&gub=1#fragment", pages)
        self.assertIsNotNone(reused)
        self.assertEqual(reused.page_id, "tab-1")

    def test_normalize_cdp_url_drops_fragment(self):
        self.assertEqual(
            normalize_cdp_url("https://www.thinkcontest.com/thinkgood/index.do#abc"),
            "https://www.thinkcontest.com/thinkgood/index.do",
        )

    def test_runtime_config_sets_iteration_budget_9999(self):
        payload = load_yaml("/home/vboxuser/public_prize_contest_radar/config/runtime.yaml")
        self.assertEqual(payload["browseros"]["iteration_budget"], 9999)

    def test_runtime_config_closes_new_browseros_tabs_after_use(self):
        payload = load_yaml("/home/vboxuser/public_prize_contest_radar/config/runtime.yaml")
        self.assertIs(payload["browseros"]["close_new_tabs_after_use"], True)

    def test_ensure_browseros_running_accepts_live_cdp_when_health_port_is_down(self):
        def fake_http_json(url, method="GET"):
            if url.endswith("/health"):
                raise OSError("health server down")
            if url.endswith("/json/version"):
                return {"Browser": "Chrome", "webSocketDebuggerUrl": "ws://127.0.0.1:9100/devtools/browser/abc"}
            raise AssertionError(url)

        with patch("contest_radar.browseros_cdp._http_json", side_effect=fake_http_json), patch(
            "contest_radar.browseros_cdp.subprocess.run"
        ) as run:
            ensure_browseros_running()
        run.assert_not_called()

    def test_open_page_falls_back_to_new_tab_when_tab_listing_times_out(self):
        with patch("contest_radar.browseros_cdp.ensure_browseros_running"), patch(
            "contest_radar.browseros_cdp._runtime_browseros_config", return_value={"reuse_existing_tabs": True}
        ), patch(
            "contest_radar.browseros_cdp.find_reusable_page", side_effect=BrowserOSUnavailable("/json/list timed out")
        ), patch(
            "contest_radar.browseros_cdp._http_json",
            return_value={"id": "tab-new", "webSocketDebuggerUrl": "ws://127.0.0.1:9100/devtools/page/tab-new"},
        ):
            page = open_page("https://example.com/contest")
        self.assertEqual(page.page_id, "tab-new")
        self.assertFalse(page.reused)

    def test_cdp_session_closes_new_tabs_by_default_to_prevent_tab_accumulation(self):
        class FakeWebSocket:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        session = CDPPageSession.__new__(CDPPageSession)
        session.page = BrowserOSPage(page_id="tab-new", websocket_url="ws://127.0.0.1:9100/devtools/page/tab-new", reused=False)
        session._ws = FakeWebSocket()
        with patch("contest_radar.browseros_cdp._runtime_browseros_config", return_value={}), patch(
            "contest_radar.browseros_cdp.urllib.request.urlopen"
        ) as urlopen:
            session.close()
        self.assertTrue(session._ws.closed)
        urlopen.assert_called_once()
        self.assertIn("/json/close/tab-new", urlopen.call_args.args[0])

    def test_capture_url_screenshot_saves_png_and_closes_tab(self):
        calls = []

        def fake_send(method, params=None):
            calls.append((method, params or {}))
            if method == "Page.captureScreenshot":
                return {"data": "ZmFrZSBwbmcgYnl0ZXM="}
            return {}

        with tempfile.TemporaryDirectory() as tmpdir, patch("contest_radar.browseros_cdp.open_page") as open_page_mock, patch(
            "contest_radar.browseros_cdp.CDPPageSession"
        ) as session_cls:
            open_page_mock.return_value = BrowserOSPage(
                page_id="tab-shot",
                websocket_url="ws://127.0.0.1:9100/devtools/page/tab-shot",
                reused=False,
            )
            session = session_cls.return_value
            session.send.side_effect = fake_send
            output_path = capture_url_screenshot("https://example.com/post", Path(tmpdir) / "detail.png", wait_seconds=0)

            self.assertEqual(output_path.name, "detail.png")
            self.assertEqual(output_path.read_bytes(), b"fake png bytes")

        self.assertIn(("Page.navigate", {"url": "https://example.com/post"}), calls)
        self.assertIn(("Page.captureScreenshot", {"format": "png", "fromSurface": True, "captureBeyondViewport": True}), calls)
        session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
