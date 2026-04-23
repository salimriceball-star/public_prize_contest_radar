from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class SourceSpec:
    id: str
    name: str
    kind: str
    url: str
    enabled: bool = True
    link_builder: str | None = None
    text_allow_patterns: list[str] = field(default_factory=list)
    text_deny_patterns: list[str] = field(default_factory=list)
    path_allow_patterns: list[str] = field(default_factory=list)
    path_deny_patterns: list[str] = field(default_factory=list)
    source_bias: int = 0
    public_sector_bias: int = 0
    notes: str = ""


@dataclass(slots=True)
class RawListing:
    source_id: str
    source_name: str
    source_url: str
    title: str
    url: str
    snippet: str = ""
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScoreBreakdown:
    total: int
    lane: str
    lane_display_name: str
    prize_score: int
    user_fit_score: int
    ai_fit_score: int
    repeatable_score: int
    public_sector_score: int
    burden_bonus: int
    penalties: dict[str, int]
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ContestRecord:
    fingerprint: str
    normalized_title: str
    title: str
    url: str
    source_id: str
    source_name: str
    source_url: str
    snippet: str
    observed_at: str
    lane: str
    lane_display_name: str
    score: int
    public_sector: bool
    ai_fit: str
    user_fit: str
    repeat_count: int
    prize_amount_krw: int | None
    deadline_text: str | None
    host_guess: str | None
    reasons: list[str]
    penalties: dict[str, int]
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
