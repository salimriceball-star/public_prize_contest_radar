from __future__ import annotations

import unittest
from datetime import date

from contest_radar.models import ContestRecord
from contest_radar.schedule import describe_schedule, filter_due_soon_records, render_crontab


class ScheduleTest(unittest.TestCase):
    def test_describe_schedule_includes_monitoring_and_alert_times(self):
        summary = describe_schedule()
        self.assertIn("08:05 KST", summary)
        self.assertIn("12:35 KST", summary)
        self.assertIn("18:35 KST", summary)
        self.assertIn("09:00 KST", summary)

    def test_render_crontab_maps_kst_schedule_to_utc_runtime_commands(self):
        crontab = render_crontab()
        self.assertIn("# public-prize-contest-radar BEGIN", crontab)
        self.assertIn("5 23 * * *", crontab)
        self.assertIn("35 3 * * *", crontab)
        self.assertIn("35 9 * * *", crontab)
        self.assertIn("0 0 * * *", crontab)
        self.assertIn("scripts/run_radar.sh run-once --top 10 --public-only --min-score 40 --notify", crontab)
        self.assertIn("scripts/run_radar.sh due-soon --public-only --min-score 40 --notify", crontab)
        self.assertIn("logs/cron/morning-monitor.log", crontab)

    def test_filter_due_soon_records_groups_7_3_1_day_alerts(self):
        records = [
            ContestRecord(
                fingerprint="a",
                normalized_title="a",
                title="A 공모전",
                url="https://example.com/a",
                source_id="s",
                source_name="Source",
                source_url="https://example.com",
                snippet="",
                observed_at="2026-04-23T00:00:00+00:00",
                lane="policy_idea",
                lane_display_name="정책/아이디어 제안형",
                score=80,
                public_sector=True,
                ai_fit="high",
                user_fit="high",
                repeat_count=0,
                prize_amount_krw=1000000,
                deadline_text="2026-04-30",
                deadline_date_iso="2026-04-30",
                detail_title="A 공모전",
                detail_date_text="접수기간 2026-04-01 ~ 2026-04-30",
                detail_content="상세",
                host_guess="기관",
                reasons=[],
                penalties={},
                raw={},
            ),
            ContestRecord(
                fingerprint="b",
                normalized_title="b",
                title="B 공모전",
                url="https://example.com/b",
                source_id="s",
                source_name="Source",
                source_url="https://example.com",
                snippet="",
                observed_at="2026-04-23T00:00:00+00:00",
                lane="policy_idea",
                lane_display_name="정책/아이디어 제안형",
                score=75,
                public_sector=True,
                ai_fit="high",
                user_fit="high",
                repeat_count=0,
                prize_amount_krw=1000000,
                deadline_text="2026-04-26",
                deadline_date_iso="2026-04-26",
                detail_title="B 공모전",
                detail_date_text="접수기간 2026-04-01 ~ 2026-04-26",
                detail_content="상세",
                host_guess="기관",
                reasons=[],
                penalties={},
                raw={},
            ),
            ContestRecord(
                fingerprint="c",
                normalized_title="c",
                title="C 공모전",
                url="https://example.com/c",
                source_id="s",
                source_name="Source",
                source_url="https://example.com",
                snippet="",
                observed_at="2026-04-23T00:00:00+00:00",
                lane="policy_idea",
                lane_display_name="정책/아이디어 제안형",
                score=70,
                public_sector=True,
                ai_fit="high",
                user_fit="high",
                repeat_count=0,
                prize_amount_krw=1000000,
                deadline_text="2026-04-24",
                deadline_date_iso="2026-04-24",
                detail_title="C 공모전",
                detail_date_text="접수기간 2026-04-01 ~ 2026-04-24",
                detail_content="상세",
                host_guess="기관",
                reasons=[],
                penalties={},
                raw={},
            ),
        ]
        grouped = filter_due_soon_records(records, today=date(2026, 4, 23))
        self.assertEqual([item.title for item in grouped[7]], ["A 공모전"])
        self.assertEqual([item.title for item in grouped[3]], ["B 공모전"])
        self.assertEqual([item.title for item in grouped[1]], ["C 공모전"])

    def test_filter_due_soon_records_ignores_invalid_scraped_deadline_dates(self):
        record = ContestRecord(
            fingerprint="bad",
            normalized_title="bad",
            title="날짜 파싱 오류 공모전",
            url="https://example.com/bad",
            source_id="s",
            source_name="Source",
            source_url="https://example.com",
            snippet="",
            observed_at="2026-04-23T00:00:00+00:00",
            lane="policy_idea",
            lane_display_name="정책/아이디어 제안형",
            score=80,
            public_sector=True,
            ai_fit="high",
            user_fit="high",
            repeat_count=0,
            prize_amount_krw=1000000,
            deadline_text="마감 2026년 13월 40일",
            deadline_date_iso="2026-13-40",
            detail_title="날짜 파싱 오류 공모전",
            detail_date_text="마감 2026년 13월 40일",
            detail_content="상세",
            host_guess="기관",
            reasons=[],
            penalties={},
            raw={},
        )
        self.assertEqual(filter_due_soon_records([record], today=date(2026, 4, 23)), {7: [], 3: [], 1: []})


if __name__ == "__main__":
    unittest.main()
