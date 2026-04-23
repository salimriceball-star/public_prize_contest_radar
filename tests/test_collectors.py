from __future__ import annotations

import unittest
from unittest.mock import patch

from contest_radar.collectors import collect_anchor_scan, safe_collect_source
from contest_radar.models import SourceSpec


class CollectorsTest(unittest.TestCase):
    @patch("contest_radar.collectors.fetch_html")
    def test_thinkcontest_link_builder_uses_data_contest_pk(self, mock_fetch_html):
        mock_fetch_html.return_value = """
        <html><body>
          <a class='weekitem' data-contest_pk='102641' href='javascript:void(0)'>2026 대한민국 헌혈 공모전</a>
          <a href='/ignore'>회원가입</a>
        </body></html>
        """
        source = SourceSpec(
            id="thinkcontest-home",
            name="Thinkgood Home",
            kind="anchor_scan",
            url="https://www.thinkcontest.com/",
            enabled=True,
            link_builder="thinkcontest_contest",
            text_allow_patterns=["공모전"],
            text_deny_patterns=["회원가입"],
        )
        items = collect_anchor_scan(source, {"request_timeout_seconds": 5, "user_agent": "test", "min_anchor_text_length": 3})
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://www.thinkcontest.com/thinkgood/user/contest/view.do?contest_pk=102641")

    @patch("contest_radar.collectors.fetch_html")
    def test_path_allow_patterns_filter_menu_links(self, mock_fetch_html):
        mock_fetch_html.return_value = """
        <html><body>
          <a href='/?c=find&s=1&gub=1&gbn=view&gp=1&ix=100'>좋은 공모전</a>
          <a href='/?c=find&s=1&gub=1'>전체 공모전</a>
        </body></html>
        """
        source = SourceSpec(
            id="wevity-all",
            name="Wevity",
            kind="anchor_scan",
            url="https://www.wevity.com/?c=find&s=1&gub=1",
            enabled=True,
            text_allow_patterns=["공모전"],
            text_deny_patterns=["전체 공모전"],
            path_allow_patterns=["gbn=view"],
        )
        items = collect_anchor_scan(source, {"request_timeout_seconds": 5, "user_agent": "test", "min_anchor_text_length": 3})
        self.assertEqual([item.title for item in items], ["좋은 공모전"])

    @patch("contest_radar.collectors.collect_source")
    def test_safe_collect_source_converts_unexpected_exception_to_error_text(self, mock_collect_source):
        class CustomError(Exception):
            pass

        source = SourceSpec(id="boom", name="Boom", kind="anchor_scan", url="https://example.com")
        mock_collect_source.side_effect = CustomError("boom")
        items, error_text = safe_collect_source(source, {})
        self.assertEqual(items, [])
        self.assertIn("CustomError: boom", error_text)


if __name__ == "__main__":
    unittest.main()
