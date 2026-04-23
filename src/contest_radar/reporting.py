from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Iterable

from .models import ContestRecord
from .schedule import filter_due_soon_records


def format_currency(amount_krw: int | None) -> str:
    return f"{amount_krw:,}원" if amount_krw else "미확인"


def render_digest(records: Iterable[ContestRecord], top_n: int = 10) -> str:
    items = sorted(records, key=lambda item: item.score, reverse=True)[:top_n]
    if not items:
        return "[공공형 상금 공모전 레이더]\n- 새 후보가 없습니다."
    lane_counter = Counter(item.lane_display_name for item in items)
    lines = [
        "[공공형 상금 공모전 레이더]",
        f"- 후보 수: {len(items)}",
        "- 트랙 분포: " + ", ".join(f"{lane} {count}건" for lane, count in lane_counter.items()),
        "",
    ]
    for idx, item in enumerate(items, start=1):
        headline = f"{idx}. [{item.score}점] [{item.lane_display_name}] {item.title}"
        lines.append(headline)
        lines.append(f"   소스: {item.source_name}")
        lines.append(f"   링크: {item.url}")
        lines.append(f"   상금 추정: {format_currency(item.prize_amount_krw)}")
        lines.append(
            "   적합도: 사용자 {user_fit} / AI {ai_fit} / 공공성 {public_sector} / 반복 {repeat_count}".format(
                user_fit=item.user_fit,
                ai_fit=item.ai_fit,
                public_sector="높음" if item.public_sector else "중간",
                repeat_count=item.repeat_count,
            )
        )
        if item.deadline_date_iso:
            lines.append(f"   마감일 추정: {item.deadline_date_iso}")
        elif item.deadline_text:
            lines.append(f"   마감 힌트: {item.deadline_text}")
        if item.detail_date_text:
            lines.append(f"   상세 일정: {item.detail_date_text[:160]}")
        if item.snippet:
            lines.append(f"   메모: {item.snippet[:180]}")
        lines.append(f"   판단 근거: {' | '.join(item.reasons[:5])}")
        if item.penalties:
            lines.append(
                "   감점: " + ", ".join(f"{name} {value}" for name, value in item.penalties.items())
            )
        lines.append("")
    return "\n".join(lines).strip()


def render_due_soon_digest(records: Iterable[ContestRecord], today: date | None = None) -> str:
    today = today or datetime.utcnow().date()
    grouped = filter_due_soon_records(records, today=today)
    if not any(grouped.values()):
        return "[공공형 상금 공모전 마감 알림]\n- D-7/D-3/D-1 대상이 없습니다."
    lines = [f"[공공형 상금 공모전 마감 알림] 기준일 {today.isoformat()}"]
    for bucket in (7, 3, 1):
        items = grouped.get(bucket, [])
        if not items:
            continue
        lines.append(f"\nD-{bucket}")
        for item in items[:10]:
            lines.append(f"- [{item.score}점] {item.title}")
            lines.append(f"  마감일: {item.deadline_date_iso or item.deadline_text}")
            lines.append(f"  소스: {item.source_name}")
            lines.append(f"  링크: {item.url}")
    return "\n".join(lines).strip()
