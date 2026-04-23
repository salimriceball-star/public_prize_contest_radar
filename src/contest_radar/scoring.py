from __future__ import annotations

import re
from typing import Any

from .models import ContestRecord, RawListing, ScoreBreakdown, SourceSpec
from .normalize import extract_deadline_date_iso, extract_deadline_text, fingerprint_for, normalize_title

_BRACKET_HOST_RE = re.compile(r"^[\[\(]([^\]\)]+)[\]\)]")


def _fit_points(level: str, max_points: int) -> int:
    table = {
        "high": max_points,
        "medium": round(max_points * 0.6),
        "low": round(max_points * 0.25),
    }
    return table.get(level, round(max_points * 0.2))


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _count_hits(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def _weighted_hits(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(len(keyword) for keyword in keywords if keyword.lower() in lowered)


def detect_lane(text: str, categories: dict[str, Any]) -> tuple[str, dict[str, Any], int]:
    lanes = categories.get("lanes", {})
    fallback_lane = "supporter_selected"
    fallback_config = lanes.get(fallback_lane, {"display_name": "기타", "user_fit": "low", "ai_fit": "low"})
    best_lane = fallback_lane
    best_config = fallback_config
    best_hits = -1
    best_weighted_hits = -1
    for lane, lane_config in lanes.items():
        hits = _count_hits(text, lane_config.get("keywords", []))
        weighted_hits = _weighted_hits(text, lane_config.get("keywords", []))
        if weighted_hits > best_weighted_hits or (weighted_hits == best_weighted_hits and hits > best_hits):
            best_lane = lane
            best_config = lane_config
            best_hits = hits
            best_weighted_hits = weighted_hits
    if best_hits <= 0:
        return fallback_lane, fallback_config, 0
    return best_lane, best_config, max(best_hits, 0)


def parse_prize_amount_krw(text: str, categories: dict[str, Any]) -> int | None:
    values: list[int] = []
    for pattern in categories.get("money_regex", []):
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            amount = match.groupdict().get("amount")
            if not amount:
                continue
            if "만원" in match.group(0):
                values.append(int(amount.replace(",", "")) * 10000)
            else:
                values.append(int(amount.replace(",", "")))
    return max(values) if values else None


def _score_prize(text: str, amount_krw: int | None, categories: dict[str, Any]) -> int:
    max_points = int(categories["weights"]["prize"])
    if amount_krw is None:
        return 8 if _contains_any(text, categories.get("prize_keywords", [])) else 4
    if amount_krw >= 10_000_000:
        return max_points
    if amount_krw >= 5_000_000:
        return 20
    if amount_krw >= 2_000_000:
        return 15
    if amount_krw >= 1_000_000:
        return 12
    if amount_krw >= 300_000:
        return 8
    return 4


def _public_sector_score(text: str, source: SourceSpec, categories: dict[str, Any]) -> tuple[int, bool]:
    max_points = int(categories["weights"]["public_sector"])
    public = _contains_any(text, categories.get("public_sector_keywords", []))
    if public:
        return max_points, True
    if source.public_sector_bias > 0:
        return min(max_points, max(3, source.public_sector_bias)), False
    return 0, False


def _repeatable_score(repeat_count: int, categories: dict[str, Any]) -> int:
    max_points = int(categories["weights"]["repeatable"])
    if repeat_count >= 3:
        return max_points
    if repeat_count == 2:
        return 12
    if repeat_count == 1:
        return 8
    return 0


def _burden_bonus_and_penalties(text: str, amount_krw: int | None, categories: dict[str, Any]) -> tuple[int, dict[str, int]]:
    penalties: dict[str, int] = {}
    penalty_rules = categories.get("penalties", {})
    if _contains_any(text, categories.get("copyright_toxic_keywords", [])):
        penalties["copyright_toxic"] = int(penalty_rules.get("copyright_toxic", -10))
    if _contains_any(text, categories.get("public_vote_keywords", [])):
        penalties["public_vote"] = int(penalty_rules.get("public_vote", -10))
    if _contains_any(text, categories.get("offline_burden_keywords", [])):
        penalties["offline_burden"] = int(penalty_rules.get("offline_burden", -10))
    if _contains_any(text, categories.get("hard_restriction_keywords", [])):
        penalties["hard_restriction"] = int(penalty_rules.get("hard_restriction", -10))
    if _contains_any(text, categories.get("heavy_work_keywords", [])) and (amount_krw or 0) < 500_000:
        penalties["low_prize_heavy_work"] = int(penalty_rules.get("low_prize_heavy_work", -15))

    bonus = 0
    if not penalties and not _contains_any(text, categories.get("heavy_work_keywords", [])):
        bonus = int(categories["weights"].get("low_burden_bonus", 5))
    return bonus, penalties


def _fit_level_from_text(text: str, explicit_level: str, high_keywords: list[str], medium_keywords: list[str]) -> str:
    if explicit_level == "high":
        return "high"
    if _contains_any(text, high_keywords):
        return "high"
    if explicit_level == "medium" or _contains_any(text, medium_keywords):
        return "medium"
    return "low"


def _extract_host_guess(title: str) -> str | None:
    match = _BRACKET_HOST_RE.match(title)
    if match:
        return match.group(1).strip()
    tokens = title.split()
    return tokens[0] if tokens else None


def score_listing(raw: RawListing, source: SourceSpec, categories: dict[str, Any], repeat_count: int = 0) -> ContestRecord:
    title_for_scoring = raw.detail_title or raw.title
    full_text = " ".join(
        part
        for part in [title_for_scoring, raw.detail_date_text, raw.detail_content, raw.snippet]
        if part
    ).strip()
    public_text = " ".join(
        part
        for part in [title_for_scoring, raw.detail_date_text, (raw.detail_content or "")[:500], raw.snippet]
        if part
    ).strip()
    lane, lane_config, lane_hits = detect_lane(full_text, categories)
    amount_krw = parse_prize_amount_krw(full_text, categories)
    prize_score = _score_prize(full_text, amount_krw, categories)
    user_fit_level = _fit_level_from_text(full_text, lane_config.get("user_fit", "low"), [], [])
    ai_fit_level = _fit_level_from_text(
        full_text,
        lane_config.get("ai_fit", "low"),
        categories.get("ai_high_keywords", []),
        categories.get("ai_medium_keywords", []),
    )
    user_fit_score = _fit_points(user_fit_level, int(categories["weights"]["user_fit"]))
    ai_fit_score = _fit_points(ai_fit_level, int(categories["weights"]["ai_fit"]))
    public_sector_score, public_sector = _public_sector_score(public_text, source, categories)
    repeatable_score = _repeatable_score(repeat_count, categories)
    burden_bonus, penalties = _burden_bonus_and_penalties(full_text, amount_krw, categories)
    source_confidence_bonus = min(5, max(0, int(source.source_bias)))
    total = max(
        0,
        min(
            100,
            prize_score
            + user_fit_score
            + ai_fit_score
            + repeatable_score
            + public_sector_score
            + burden_bonus
            + source_confidence_bonus
            + sum(penalties.values()),
        ),
    )
    deadline_text = raw.deadline_text or extract_deadline_text(full_text)
    deadline_date_iso = raw.deadline_date_iso or extract_deadline_date_iso(full_text)
    reasons = [
        f"트랙={lane_config.get('display_name', lane)}({lane_hits}개 키워드 매치)",
        f"사용자 적합도={user_fit_level}",
        f"AI 활용 적합도={ai_fit_level}",
        f"공공성={'높음' if public_sector else '중간'}",
        f"소스 신뢰 가중치={source_confidence_bonus}",
    ]
    if raw.detail_title or raw.detail_date_text or raw.detail_content:
        reasons.append("BrowserOS 상세 파싱 적용")
    if amount_krw:
        reasons.append(f"상금 추정={amount_krw:,}원")
    if deadline_date_iso:
        reasons.append(f"마감일 추정={deadline_date_iso}")
    if repeat_count:
        reasons.append(f"반복 개최 히스토리={repeat_count}회")
    if penalties:
        reasons.append("감점=" + ", ".join(f"{k}:{v}" for k, v in penalties.items()))
    breakdown = ScoreBreakdown(
        total=total,
        lane=lane,
        lane_display_name=lane_config.get("display_name", lane),
        prize_score=prize_score,
        user_fit_score=user_fit_score,
        ai_fit_score=ai_fit_score,
        repeatable_score=repeatable_score,
        public_sector_score=public_sector_score,
        burden_bonus=burden_bonus + source_confidence_bonus,
        penalties=penalties,
        reasons=reasons,
    )
    raw_payload = raw.to_dict()
    raw_payload["score_breakdown"] = breakdown.to_dict()
    return ContestRecord(
        fingerprint=fingerprint_for(raw.title, raw.url),
        normalized_title=normalize_title(title_for_scoring),
        title=title_for_scoring,
        url=raw.url,
        source_id=raw.source_id,
        source_name=raw.source_name,
        source_url=raw.source_url,
        snippet=raw.snippet,
        observed_at=raw.observed_at,
        lane=lane,
        lane_display_name=lane_config.get("display_name", lane),
        score=total,
        public_sector=public_sector or source.public_sector_bias >= 4,
        ai_fit=ai_fit_level,
        user_fit=user_fit_level,
        repeat_count=repeat_count,
        prize_amount_krw=amount_krw,
        deadline_text=deadline_text,
        deadline_date_iso=deadline_date_iso,
        detail_title=raw.detail_title,
        detail_date_text=raw.detail_date_text,
        detail_content=raw.detail_content,
        host_guess=_extract_host_guess(title_for_scoring),
        reasons=reasons,
        penalties=penalties,
        raw=raw_payload,
    )
