from __future__ import annotations

import unittest
from unittest.mock import patch

from contest_radar.browseros_collectors import build_listing_expression, enrich_listings_with_browseros_details, extract_detail_metadata, parse_browseros_listing_payload
from contest_radar.config_loader import load_sources
from contest_radar.models import RawListing, SourceSpec


class BrowserOSParsingTest(unittest.TestCase):
    def test_parse_browseros_listing_payload_rebuilds_thinkcontest_links(self):
        source = SourceSpec(
            id="thinkcontest-home",
            name="Thinkgood Home",
            kind="browseros_anchor_scan",
            url="https://www.thinkcontest.com/",
            link_builder="thinkcontest_contest",
            text_allow_patterns=["공모전"],
            text_deny_patterns=["회원가입"],
            listing_limit=5,
        )
        payload = {
            "url": source.url,
            "anchors": [
                {"text": "회원가입", "href": "/join", "fullHref": "https://www.thinkcontest.com/join", "contestPk": None, "parentText": "회원가입"},
                {
                    "text": "2. 2026 서울교통공사 사진·AI이미지 공모전",
                    "href": "javascript:void(0)",
                    "fullHref": "javascript:void(0)",
                    "contestPk": "104383",
                    "parentText": "2. 2026 서울교통공사 사진·AI이미지 공모전",
                },
            ],
        }
        listings = parse_browseros_listing_payload(source, payload)
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].url, "https://www.thinkcontest.com/thinkgood/user/contest/view.do?contest_pk=104383")
        self.assertIn("AI이미지", listings[0].title)

    def test_parse_browseros_listing_payload_rebuilds_thinkcontest_links_from_javascript_onclick(self):
        source = SourceSpec(
            id="thinkcontest-home",
            name="Thinkgood Home",
            kind="browseros_anchor_scan",
            url="https://www.thinkcontest.com/",
            link_builder="thinkcontest_contest",
            text_allow_patterns=["공모전"],
            listing_limit=5,
        )
        payload = {
            "url": source.url,
            "anchors": [
                {
                    "text": "2026 공공데이터 AI 활용 공모전",
                    "href": "javascript:fnContestView('104999')",
                    "fullHref": "javascript:void(0)",
                    "onclick": "fnContestView('104999'); return false;",
                    "parentText": "2026 공공데이터 AI 활용 공모전 접수중",
                },
            ],
        }
        listings = parse_browseros_listing_payload(source, payload)
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].url, "https://www.thinkcontest.com/thinkgood/user/contest/view.do?contest_pk=104999")

    def test_listing_expression_collects_onclick_for_javascript_only_contest_links(self):
        expression = build_listing_expression()
        self.assertIn("onclick", expression)
        self.assertIn("getAttribute('onclick')", expression)

    def test_enabled_browseros_sources_have_detail_parsing_selectors_configured(self):
        _defaults, sources = load_sources()
        enabled_browseros_sources = [source for source in sources if source.enabled and source.kind == "browseros_anchor_scan"]
        self.assertGreaterEqual(len(enabled_browseros_sources), 5)
        for source in enabled_browseros_sources:
            with self.subTest(source=source.id):
                self.assertEqual(source.detail_fetch, "browseros_detail")
                self.assertGreater(len(source.detail_title_selectors), 0)
                self.assertGreater(len(source.detail_date_selectors), 0)
                self.assertGreater(len(source.detail_content_selectors), 0)

    def test_dacon_source_filters_menu_help_links_from_daily_updates(self):
        _defaults, sources = load_sources()
        source = next(item for item in sources if item.id == "dacon-open")
        payload = {
            "anchors": [
                {"text": "대회 참가 방법", "href": "/more/join", "fullHref": "https://www.dacon.io/more/join", "parentText": "더보기 대회 참가 방법"},
                {"text": "공공데이터 AI 경진대회", "href": "/competitions/open/123", "fullHref": "https://www.dacon.io/competitions/open/123", "parentText": "공공데이터 AI 경진대회"},
            ]
        }
        listings = parse_browseros_listing_payload(source, payload)
        self.assertEqual([item.title for item in listings], ["공공데이터 AI 경진대회"])

    def test_kstartup_source_filters_generic_listing_navigation(self):
        _defaults, sources = load_sources()
        source = next(item for item in sources if item.id == "kstartup-biz")
        payload = {
            "anchors": [
                {"text": "사업공고", "href": "/web/contents/bizpbanc-ongoing.do", "fullHref": "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do", "parentText": "사업공고"},
                {"text": "모집중", "href": "/web/contents/bizpbanc-ongoing.do", "fullHref": "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do", "parentText": "모집중"},
                {"text": "2026년 창업지원사업 통합공고", "href": "/web/contents/webFSBIPBANC.do", "fullHref": "https://www.k-startup.go.kr/web/contents/webFSBIPBANC.do", "parentText": "2026년 창업지원사업 통합공고"},
                {"text": "공공데이터 창업 경진대회 참가자 모집 공고", "href": "/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=123", "fullHref": "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=123", "parentText": "공공데이터 창업 경진대회 참가자 모집 공고"},
            ]
        }
        listings = parse_browseros_listing_payload(source, payload)
        self.assertEqual([item.title for item in listings], ["공공데이터 창업 경진대회 참가자 모집 공고"])
        self.assertNotIn(source.url, [item.url for item in listings])

    def test_kstartup_source_rebuilds_javascript_go_view_detail_links(self):
        _defaults, sources = load_sources()
        source = next(item for item in sources if item.id == "kstartup-biz")
        payload = {
            "url": source.url,
            "anchors": [
                {
                    "text": "공공데이터 AI 창업 경진대회 참가자 모집 공고",
                    "href": "javascript:go_view(176892);",
                    "fullHref": "javascript:go_view(176892);",
                    "onclick": "",
                    "parentText": "사업화 D-22 마감일자 2026-05-15 공공데이터 AI 창업 경진대회 참가자 모집 공고 창업진흥원 조회 45,187",
                },
            ],
        }
        listings = parse_browseros_listing_payload(source, payload)
        self.assertEqual(len(listings), 1)
        self.assertEqual(
            listings[0].url,
            "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=176892",
        )

    def test_extract_detail_metadata_prefers_specific_title_date_and_content(self):
        listing = RawListing(
            source_id="wevity-all",
            source_name="Wevity",
            source_url="https://www.wevity.com/?c=find&s=1&gub=1",
            title="[대한민국시도지사협의회] 지방시대 숏폼 영상 공모전",
            url="https://www.wevity.com/?c=find&s=1&gub=1&gbn=view&gp=1&ix=106166",
            snippet="기본 스니펫",
        )
        detail_payload = {
            "documentTitle": "[대한민국시도지사협의회] 지방시대 숏폼 영상 공모전 | 공모전 대외활동 콘테스트 - 위비티",
            "titles": [
                "공모전 대외활동 콘테스트 메인메뉴",
                "[대한민국시도지사협의회] 지방시대 숏폼 영상 공모전",
                "접수기간",
            ],
            "dates": [
                "접수기간 2026-03-25 ~ 2026-05-13 D-20",
                "2026-03-25 ~ 2026-05-13",
            ],
            "contents": [
                "짧은 소개",
                "[대한민국시도지사협의회] 지방시대 숏폼 영상 공모전 ■ 참가자격 : 국내 거주자 누구나 ■ 공모기간 : 2026. 3. 25(수) ~ 5. 13(수) ■ 영상규격 : 세로형 숏폼 영상(15~90초) AI 활용 가능",
            ],
            "sample": "본문 전체 샘플",
        }
        enriched = extract_detail_metadata(listing, detail_payload)
        self.assertEqual(enriched["detail_title"], "[대한민국시도지사협의회] 지방시대 숏폼 영상 공모전")
        self.assertEqual(enriched["detail_date_text"], "접수기간 2026-03-25 ~ 2026-05-13 D-20")
        self.assertIn("영상규격", enriched["detail_content"])
        self.assertEqual(enriched["deadline_date_iso"], "2026-05-13")

    def test_extract_detail_metadata_avoids_menu_noise_when_detail_block_is_available(self):
        listing = RawListing(
            source_id="thinkcontest-home",
            source_name="Thinkgood Home",
            source_url="https://www.thinkcontest.com/",
            title="2026 서울교통공사 사진·AI이미지 공모전",
            url="https://www.thinkcontest.com/thinkgood/user/contest/view.do?contest_pk=104383",
            snippet="목록 스니펫",
        )
        detail_payload = {
            "documentTitle": "2026 서울교통공사 사진·AI이미지 공모전",
            "titles": ["2026 서울교통공사 사진·AI이미지 공모전"],
            "dates": ["접수기간 2026-04-20 00:00 ~ 2026-05-19 17:00"],
            "contents": [
                "전체 공모전 대외활동 교육·강연 주간 조회수 베스트 1. 2026 대한민국 헌혈 공모전 2. 2026 서울교통공사 사진·AI이미지 공모전 3. 제9회 전국동시지방선거 유권자 희망공약 제안 4. 2026 길 사진 공모전",
                "2026 서울교통공사 사진·AI이미지 공모전 주최 서울교통공사 응모분야 디자인 사진 접수기간 2026-04-20 00:00 ~ 2026-05-19 17:00 참가자격 만 18세 이상 누구나 시상금 300만원 AI이미지 제출 가능",
            ],
            "sample": "본문 전체 샘플",
        }
        enriched = extract_detail_metadata(listing, detail_payload)
        self.assertIn("주최 서울교통공사", enriched["detail_content"])
        self.assertNotIn("주간 조회수 베스트", enriched["snippet"])

    def test_enrich_listings_skips_cached_urls_without_detail_fetch(self):
        source = SourceSpec(
            id="thinkcontest-home",
            name="Thinkgood Home",
            kind="browseros_anchor_scan",
            url="https://www.thinkcontest.com/",
            detail_fetch="browseros_detail",
            detail_limit=3,
        )
        listings = [
            RawListing(
                source_id=source.id,
                source_name=source.name,
                source_url=source.url,
                title="이미 본 공모전",
                url="https://example.com/already-seen",
            )
        ]
        with patch("contest_radar.browseros_collectors.evaluate_url") as evaluate_url:
            enriched = enrich_listings_with_browseros_details(source, listings, known_urls={"https://example.com/already-seen"})
        evaluate_url.assert_not_called()
        self.assertIsNone(enriched[0].detail_title)
        self.assertTrue(enriched[0].extras["cache_hit"])


if __name__ == "__main__":
    unittest.main()
