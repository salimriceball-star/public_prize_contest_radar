from __future__ import annotations

import unittest

from contest_radar.config_loader import load_categories
from contest_radar.models import RawListing, SourceSpec
from contest_radar.scoring import score_listing


class ScoringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.categories = load_categories()
        cls.source = SourceSpec(
            id="linkareer-contest",
            name="Linkareer",
            kind="anchor_scan",
            url="https://linkareer.com/list/contest",
            enabled=True,
            source_bias=7,
            public_sector_bias=3,
        )

    def test_high_fit_public_data_listing_scores_high(self):
        listing = RawListing(
            source_id=self.source.id,
            source_name=self.source.name,
            source_url=self.source.url,
            title="[고용노동부] 제5회 고용노동 공공데이터·AI 활용 공모전",
            url="https://example.com/contest-1",
            snippet="대상 500만원, 공공데이터와 AI를 활용한 정책 아이디어 제안",
        )
        record = score_listing(listing, self.source, self.categories, repeat_count=2)
        self.assertGreaterEqual(record.score, 70)
        self.assertEqual(record.lane, "data_ai_startup")
        self.assertTrue(record.public_sector)
        self.assertEqual(record.ai_fit, "high")

    def test_public_vote_and_offline_keywords_apply_penalties(self):
        listing = RawListing(
            source_id=self.source.id,
            source_name=self.source.name,
            source_url=self.source.url,
            title="지역 홍보 숏폼 공모전",
            url="https://example.com/contest-2",
            snippet="좋아요 공개투표 진행, 본선발표 오프라인 PT 필수, 상금 30만원",
        )
        record = score_listing(listing, self.source, self.categories, repeat_count=0)
        self.assertIn("public_vote", record.penalties)
        self.assertIn("offline_burden", record.penalties)
        self.assertLess(record.score, 70)


if __name__ == "__main__":
    unittest.main()
