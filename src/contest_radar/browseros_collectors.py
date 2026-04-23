from __future__ import annotations

from dataclasses import asdict
import re
from typing import Iterable

from .browseros_cdp import evaluate_url
from .config_loader import load_runtime_config
from .models import RawListing, SourceSpec
from .normalize import canonicalize_url, collapse_whitespace, extract_deadline_date_iso, extract_deadline_text, normalize_title

_DEFAULT_TITLE_SELECTORS = [
    "h1",
    "h2",
    "[class*='title']",
    ".title",
    ".tit",
    ".subject",
]
_DEFAULT_DATE_SELECTORS = [
    "time",
    "[class*='date']",
    "[class*='time']",
    "[class*='write']",
    "[class*='reg']",
    "[class*='day']",
    ".info",
    ".meta",
    ".summary",
]
_DEFAULT_CONTENT_SELECTORS = [
    "article",
    "main",
    ".article",
    ".content",
    ".view_cont",
    ".board_view",
    ".detail",
    ".entry-content",
    "[class*='content']",
    "[class*='view']",
]
_GENERIC_TITLE_NOISE = ("메인메뉴", "뉴스레터", "주간 조회수", "방금 본 프로젝트", "분야", "응모대상", "주최", "홈페이지")
_GENERIC_CONTENT_NOISE = (
    "전체 공모전 대외활동",
    "주간 조회수 베스트",
    "뉴스레터 신청",
    "방금 본 프로젝트",
    "사이트맵 광고안내",
)
_DETAIL_CONTENT_TERMS = ("참가자격", "접수기간", "공모주제", "시상", "제출", "신청", "주최", "응모분야", "시상금")
_DATE_TOKEN_RE = re.compile(r"20\d{2}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}")


def _looks_like_html(text: str) -> bool:
    lowered = text.lower()
    return "<" in text or "/>" in text or "src=" in lowered or "class=" in lowered or "style=" in lowered


def _matches_any(text: str, patterns: Iterable[str]) -> bool:
    if not patterns:
        return True
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def _path_allowed(source: SourceSpec, url: str) -> bool:
    lowered = url.lower()
    if source.path_allow_patterns and not any(pattern.lower() in lowered for pattern in source.path_allow_patterns):
        return False
    if source.path_deny_patterns and any(pattern.lower() in lowered for pattern in source.path_deny_patterns):
        return False
    return True


def _extract_contest_pk_from_javascript(*values: object) -> str | None:
    for value in values:
        text = str(value or "")
        if not text:
            continue
        explicit = re.search(r"contest[_-]?pk\D{0,12}(\d{3,})", text, flags=re.IGNORECASE)
        if explicit:
            return explicit.group(1)
        function_arg = re.search(r"['\"]?(\d{4,})['\"]?", text)
        if function_arg:
            return function_arg.group(1)
    return None


def _build_link(source: SourceSpec, row: dict) -> str | None:
    href = collapse_whitespace(str(row.get("href") or ""))
    full_href = collapse_whitespace(str(row.get("fullHref") or ""))
    if full_href and not full_href.lower().startswith("javascript"):
        return canonicalize_url(full_href)
    if href and not href.lower().startswith("javascript"):
        return canonicalize_url(href)
    if source.link_builder == "thinkcontest_contest":
        contest_pk = row.get("contestPk") or row.get("contest_pk") or _extract_contest_pk_from_javascript(row.get("onclick"), href, full_href)
        if contest_pk:
            return f"https://www.thinkcontest.com/thinkgood/user/contest/view.do?contest_pk={contest_pk}"
    return None


def _extract_snippet(title: str, parent_text: str) -> str:
    snippet = collapse_whitespace(parent_text)
    if snippet.startswith(title):
        snippet = snippet[len(title) :].strip(" -·|:")
    return snippet[:280]


def build_listing_expression() -> str:
    return """(() => {
      const norm = value => (value || '').replace(/\\s+/g, ' ').trim();
      const anchors = Array.from(document.querySelectorAll('a')).map(anchor => ({
        text: norm(anchor.innerText || anchor.textContent || ''),
        altText: norm((anchor.querySelector('img[alt]') || {}).alt || anchor.getAttribute('aria-label') || ''),
        href: anchor.getAttribute('href') || '',
        fullHref: anchor.href || '',
        onclick: anchor.getAttribute('onclick') || '',
        contestPk: anchor.dataset ? (anchor.dataset.contest_pk || anchor.dataset.contestPk || null) : null,
        parentText: norm(anchor.parentElement ? (anchor.parentElement.innerText || anchor.parentElement.textContent || '') : ''),
      })).filter(item => item.text || item.altText);
      return {url: location.href, documentTitle: document.title, anchors};
    })()"""


def build_detail_expression(source: SourceSpec) -> str:
    title_selectors = source.detail_title_selectors or _DEFAULT_TITLE_SELECTORS
    date_selectors = source.detail_date_selectors or _DEFAULT_DATE_SELECTORS
    content_selectors = source.detail_content_selectors or _DEFAULT_CONTENT_SELECTORS
    title_selector_js = ", ".join(title_selectors)
    date_selector_js = ", ".join(date_selectors)
    content_selector_js = ", ".join(content_selectors)
    return f"""(() => {{
      const norm = value => (value || '').replace(/\\s+/g, ' ').trim();
      const texts = selector => Array.from(document.querySelectorAll(selector)).map(el => norm(el.innerText || el.textContent)).filter(Boolean);
      const meta = selector => Array.from(document.querySelectorAll(selector)).map(el => norm(el.getAttribute('content'))).filter(Boolean);
      return {{
        url: location.href,
        documentTitle: document.title,
        titles: Array.from(new Set([...texts({title_selector_js!r}), ...meta('meta[property="og:title"], meta[name="twitter:title"]'), document.title])).slice(0, 20),
        dates: Array.from(new Set([...texts({date_selector_js!r}), ...meta('meta[property="article:published_time"], meta[name="pubdate"], meta[name="publish-date"]')])).slice(0, 20),
        contents: Array.from(new Set([...texts({content_selector_js!r})])).slice(0, 8),
        sample: norm(document.body.innerText).slice(0, 8000)
      }};
    }})()"""


def _runtime_iteration_budget() -> int:
    payload = load_runtime_config()
    browseros = payload.get("browseros", {}) if isinstance(payload, dict) else {}
    budget = int(browseros.get("iteration_budget", 9999))
    return max(1, budget)


def parse_browseros_listing_payload(source: SourceSpec, payload: dict) -> list[RawListing]:
    anchors = payload.get("anchors", []) if isinstance(payload, dict) else []
    results: list[RawListing] = []
    seen: set[tuple[str, str]] = set()
    listing_budget = min(source.listing_limit, _runtime_iteration_budget())
    for row in anchors:
        title = collapse_whitespace(str(row.get("text") or row.get("altText") or ""))
        parent_text = collapse_whitespace(str(row.get("parentText") or title))
        if _looks_like_html(title):
            title = ""
        if not title and parent_text:
            title = parent_text.split("조회", 1)[0].strip()
        if _looks_like_html(title):
            title = ""
        if not title:
            continue
        if not _matches_any(title, source.text_allow_patterns):
            continue
        if source.text_deny_patterns and _matches_any(title, source.text_deny_patterns):
            continue
        target_url = _build_link(source, row)
        if not target_url or not _path_allowed(source, target_url):
            continue
        key = (title, target_url)
        if key in seen:
            continue
        seen.add(key)
        parent_text = collapse_whitespace(str(row.get("parentText") or title))
        results.append(
            RawListing(
                source_id=source.id,
                source_name=source.name,
                source_url=source.url,
                title=title,
                url=target_url,
                snippet=_extract_snippet(title, parent_text),
                extras={
                    "source": asdict(source),
                    "browseros_listing_row": row,
                    "browseros_listing_page": payload,
                },
            )
        )
        if len(results) >= listing_budget:
            break
    return results


def _pick_best_title(listing: RawListing, detail_payload: dict) -> str | None:
    listing_norm = normalize_title(listing.title)
    candidates = []
    for candidate in detail_payload.get("titles", []):
        text = collapse_whitespace(str(candidate))
        if not text or _looks_like_html(text):
            continue
        score = 0
        candidate_norm = normalize_title(text)
        if listing_norm and listing_norm in candidate_norm:
            score += 100
        if candidate_norm and candidate_norm in listing_norm:
            score += 90
        if any(noise in text for noise in _GENERIC_TITLE_NOISE):
            score -= 40
        score -= abs(len(text) - len(listing.title)) // 4
        candidates.append((score, text))
    if not candidates:
        document_title = collapse_whitespace(str(detail_payload.get("documentTitle") or listing.title))
        if not document_title or _looks_like_html(document_title):
            return listing.title
        return document_title
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _pick_best_date(detail_payload: dict) -> str | None:
    ranked = []
    for candidate in detail_payload.get("dates", []):
        text = collapse_whitespace(str(candidate))
        if not text:
            continue
        score = 0
        if "접수기간" in text:
            score += 80
        if "마감" in text:
            score += 60
        if "~" in text or "-" in text:
            score += 30
        if _DATE_TOKEN_RE.search(text):
            score += 40
        if "20" in text:
            score += 20
        score -= len(text) // 20
        ranked.append((score, text))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked else None


def _pick_best_content(listing: RawListing, detail_payload: dict, detail_title: str | None) -> str | None:
    candidates = []
    listing_norm = normalize_title(listing.title)
    detail_title_norm = normalize_title(detail_title or "")
    for candidate in detail_payload.get("contents", []):
        text = collapse_whitespace(str(candidate))
        if len(text) < 40:
            continue
        score = 0
        text_norm = normalize_title(text)
        if listing_norm and listing_norm in text_norm:
            score += 80
            title_position = text_norm.find(listing_norm)
            if title_position >= 0:
                score += max(0, 80 - title_position // 8)
                if title_position == 0:
                    score += 20
        if detail_title_norm and detail_title_norm in text_norm:
            score += 80
            detail_title_position = text_norm.find(detail_title_norm)
            if detail_title_position >= 0:
                score += max(0, 80 - detail_title_position // 8)
                if detail_title_position == 0:
                    score += 20
        term_hits = sum(1 for keyword in _DETAIL_CONTENT_TERMS if keyword in text)
        score += min(100, term_hits * 20)
        if any(noise in text for noise in _GENERIC_CONTENT_NOISE):
            score -= 140
        if len(text) > 3500:
            score -= 20
        candidates.append((score, text))
    if not candidates:
        sample = collapse_whitespace(str(detail_payload.get("sample") or ""))
        return sample[:3000] if sample else None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def extract_detail_metadata(listing: RawListing, detail_payload: dict) -> dict[str, str | None]:
    detail_title = _pick_best_title(listing, detail_payload)
    detail_date_text = _pick_best_date(detail_payload)
    detail_content = _pick_best_content(listing, detail_payload, detail_title)
    if (not detail_date_text or not _DATE_TOKEN_RE.search(detail_date_text)) and detail_content:
        detail_date_text = extract_deadline_text(detail_content) or detail_date_text
    combined = " ".join(part for part in [detail_date_text, detail_content, detail_payload.get("sample")] if part)
    deadline_text = extract_deadline_text(detail_date_text or "") or extract_deadline_text(detail_content or "") or extract_deadline_text(str(detail_payload.get("sample") or ""))
    deadline_date_iso = (
        extract_deadline_date_iso(detail_date_text or "")
        or extract_deadline_date_iso(detail_content or "")
        or extract_deadline_date_iso(str(detail_payload.get("sample") or ""))
    )
    snippet = listing.snippet
    if detail_content:
        snippet = collapse_whitespace(detail_content)[:280]
    return {
        "detail_title": detail_title,
        "detail_date_text": detail_date_text,
        "detail_content": detail_content,
        "deadline_text": deadline_text,
        "deadline_date_iso": deadline_date_iso,
        "snippet": snippet,
    }


def enrich_listings_with_browseros_details(source: SourceSpec, listings: list[RawListing], known_urls: set[str] | None = None) -> list[RawListing]:
    if not listings or source.detail_fetch != "browseros_detail":
        return listings
    known = {canonicalize_url(url) for url in (known_urls or set())}
    detail_expression = build_detail_expression(source)
    detail_budget = min(source.detail_limit, _runtime_iteration_budget())
    details_fetched = 0
    for listing in listings:
        if canonicalize_url(listing.url) in known:
            listing.extras["cache_hit"] = True
            continue
        if details_fetched >= detail_budget:
            break
        detail_payload = evaluate_url(listing.url, detail_expression, wait_seconds=source.detail_wait_seconds)
        details_fetched += 1
        if not isinstance(detail_payload, dict):
            continue
        detail = extract_detail_metadata(listing, detail_payload)
        listing.detail_title = detail.get("detail_title")
        listing.detail_date_text = detail.get("detail_date_text")
        listing.detail_content = detail.get("detail_content")
        listing.deadline_text = detail.get("deadline_text")
        listing.deadline_date_iso = detail.get("deadline_date_iso")
        listing.snippet = detail.get("snippet") or listing.snippet
        listing.extras["browseros_detail"] = detail_payload
    return listings


def collect_browseros_anchor_scan(source: SourceSpec, defaults: dict[str, object], known_urls: set[str] | None = None) -> list[RawListing]:
    wait_seconds = float(source.load_wait_seconds or defaults.get("request_timeout_seconds", 20))
    payload = evaluate_url(source.url, build_listing_expression(), wait_seconds=wait_seconds)
    if not isinstance(payload, dict):
        return []
    listings = parse_browseros_listing_payload(source, payload)
    if known_urls:
        known = {canonicalize_url(url) for url in known_urls}
        listings = [listing for listing in listings if canonicalize_url(listing.url) not in known]
    return enrich_listings_with_browseros_details(source, listings, known_urls=known_urls)
