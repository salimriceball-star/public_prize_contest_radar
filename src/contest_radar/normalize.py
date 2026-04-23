from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse


_whitespace_re = re.compile(r"\s+")
_strip_title_re = re.compile(r"[^0-9a-z가-힣]+", re.IGNORECASE)
_FULL_DATE_PATTERN = r"(20[0-9]{2})[./-]\s*([0-9]{1,2})[./-]\s*([0-9]{1,2})"
_PARTIAL_DATE_PATTERN = r"([0-9]{1,2})[./-]\s*([0-9]{1,2})"
_deadline_range_re = re.compile(rf"(접수기간\s*)?{_FULL_DATE_PATTERN}\s*[~\-]\s*(?:{_FULL_DATE_PATTERN}|{_PARTIAL_DATE_PATTERN})")
_deadline_start_end_re = re.compile(rf"시작일\s*{_FULL_DATE_PATTERN}\s*마감일\s*(?:{_FULL_DATE_PATTERN}|{_PARTIAL_DATE_PATTERN})")
_deadline_end_only_re = re.compile(rf"마감일\s*(?:{_FULL_DATE_PATTERN}|{_PARTIAL_DATE_PATTERN})")
_deadline_tilde_re = re.compile(rf"~\s*{_PARTIAL_DATE_PATTERN}")
_deadline_single_re = re.compile(_FULL_DATE_PATTERN)
_full_date_re = re.compile(_FULL_DATE_PATTERN)
_partial_date_re = re.compile(_PARTIAL_DATE_PATTERN)
_year_re = re.compile(r"^20[0-9]{2}")


def collapse_whitespace(text: str) -> str:
    return _whitespace_re.sub(" ", text or "").strip()


def normalize_title(title: str) -> str:
    clean = collapse_whitespace(title).lower()
    clean = _strip_title_re.sub("", clean)
    return clean


def repeat_key_from_title(title: str) -> str:
    return _year_re.sub("", normalize_title(title))


def fingerprint_for(title: str, url: str) -> str:
    material = f"{normalize_title(title)}|{canonicalize_url(url)}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:24]


def canonicalize_url(url: str) -> str:
    parts = urlparse(url)
    clean_path = parts.path.rstrip("/") or "/"
    clean = parts._replace(fragment="", query=parts.query)
    return clean._replace(path=clean_path).geturl()


def host_from_url(url: str) -> str:
    return urlparse(url).netloc.lower()


def _parse_partial_date(month: int, day: int, today: date) -> date | None:
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        return None
    if candidate < today - timedelta(days=30):
        try:
            candidate = date(today.year + 1, month, day)
        except ValueError:
            return None
    return candidate


def _parse_full_date_pieces(year: str | None, month: str | None, day: str | None) -> date | None:
    if not (year and month and day):
        return None
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def _parse_partial_date_pieces(month: str | None, day: str | None, today: date) -> date | None:
    if not (month and day):
        return None
    return _parse_partial_date(int(month), int(day), today)


def _parse_match_date(groups: tuple[str, ...], offset: int, today: date) -> date | None:
    if offset + 2 >= len(groups):
        return None
    return _parse_full_date_pieces(groups[offset], groups[offset + 1], groups[offset + 2])


def _parse_match_partial_date(groups: tuple[str, ...], offset: int, today: date) -> date | None:
    if offset + 1 >= len(groups):
        return None
    return _parse_partial_date_pieces(groups[offset], groups[offset + 1], today)


def extract_deadline_text(text: str) -> str | None:
    clean = collapse_whitespace(text)
    for regex in (_deadline_start_end_re, _deadline_end_only_re, _deadline_range_re, _deadline_tilde_re, _deadline_single_re):
        match = regex.search(clean)
        if match:
            return collapse_whitespace(match.group(0))
    return None


def extract_dates(text: str, today: date | None = None) -> list[date]:
    today = today or datetime.now(timezone.utc).date()
    parsed: list[date] = []
    seen: set[date] = set()
    full_spans: list[tuple[int, int]] = []
    for match in _full_date_re.finditer(text or ""):
        year, month, day = (int(piece) for piece in match.groups())
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if candidate not in seen:
            parsed.append(candidate)
            seen.add(candidate)
        full_spans.append(match.span())

    for match in _partial_date_re.finditer(text or ""):
        span = match.span()
        if any(start <= span[0] < end or start < span[1] <= end for start, end in full_spans):
            continue
        month, day = (int(piece) for piece in match.groups())
        candidate = _parse_partial_date(month, day, today)
        if candidate and candidate not in seen:
            parsed.append(candidate)
            seen.add(candidate)
    parsed.sort()
    return parsed


def extract_deadline_date_iso(text: str, today: date | None = None) -> str | None:
    today = today or datetime.now(timezone.utc).date()
    clean = collapse_whitespace(text)
    start_end_match = _deadline_start_end_re.search(clean)
    if start_end_match:
        groups = start_end_match.groups()
        end_date = _parse_match_date(groups, 3, today) or _parse_match_partial_date(groups, 6, today)
        return end_date.isoformat() if end_date else None
    end_only_match = _deadline_end_only_re.search(clean)
    if end_only_match:
        groups = end_only_match.groups()
        end_date = _parse_match_date(groups, 0, today) or _parse_match_partial_date(groups, 3, today)
        return end_date.isoformat() if end_date else None
    range_match = _deadline_range_re.search(clean)
    if range_match:
        groups = range_match.groups()
        end_date = _parse_match_date(groups, 4, today) or _parse_match_partial_date(groups, 7, today)
        return end_date.isoformat() if end_date else None
    tilde_match = _deadline_tilde_re.search(clean)
    if tilde_match:
        groups = tilde_match.groups()
        end_date = _parse_match_partial_date(groups, 0, today)
        return end_date.isoformat() if end_date else None
    dates = extract_dates(clean, today=today)
    if not dates:
        return None
    return dates[-1].isoformat()
