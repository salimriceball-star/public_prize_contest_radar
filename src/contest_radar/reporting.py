from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import ContestRecord


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
        if item.deadline_text:
            lines.append(f"   마감 힌트: {item.deadline_text}")
        if item.snippet:
            lines.append(f"   메모: {item.snippet[:180]}")
        lines.append(f"   판단 근거: {' | '.join(item.reasons[:4])}")
        if item.penalties:
            lines.append(
                "   감점: " + ", ".join(f"{name} {value}" for name, value in item.penalties.items())
            )
        lines.append("")
    return "\n".join(lines).strip()
