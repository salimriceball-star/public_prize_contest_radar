from __future__ import annotations

import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict
from typing import Iterable

from bs4 import BeautifulSoup, Tag

from .models import RawListing, SourceSpec
from .normalize import canonicalize_url, collapse_whitespace

_SSL_CONTEXT = ssl.create_default_context()


def fetch_html(url: str, timeout_seconds: int, user_agent: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=timeout_seconds, context=_SSL_CONTEXT) as response:
        return response.read().decode("utf-8", "ignore")


def _matches_any(text: str, patterns: Iterable[str]) -> bool:
    if not patterns:
        return True
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def _build_link(source: SourceSpec, anchor: Tag) -> str | None:
    href = (anchor.get("href") or "").strip()
    if href and not href.lower().startswith("javascript"):
        return canonicalize_url(urllib.parse.urljoin(source.url, href))
    if source.link_builder == "thinkcontest_contest":
        contest_pk = anchor.get("data-contest_pk")
        if contest_pk:
            return f"https://www.thinkcontest.com/thinkgood/user/contest/view.do?contest_pk={contest_pk}"
    return None


def _path_allowed(source: SourceSpec, url: str) -> bool:
    lowered = url.lower()
    if source.path_allow_patterns and not any(pattern.lower() in lowered for pattern in source.path_allow_patterns):
        return False
    if source.path_deny_patterns and any(pattern.lower() in lowered for pattern in source.path_deny_patterns):
        return False
    return True


def _extract_snippet(anchor: Tag) -> str:
    parent = anchor.parent.get_text(" ", strip=True) if anchor.parent else ""
    snippet = collapse_whitespace(parent)
    title = collapse_whitespace(anchor.get_text(" ", strip=True))
    if snippet.startswith(title):
        snippet = snippet[len(title) :].strip(" -·|:")
    return snippet[:280]


def collect_anchor_scan(source: SourceSpec, defaults: dict[str, object]) -> list[RawListing]:
    timeout_seconds = int(defaults.get("request_timeout_seconds", 20))
    user_agent = str(defaults.get("user_agent", "Mozilla/5.0"))
    min_len = int(defaults.get("min_anchor_text_length", 6))
    max_len = int(defaults.get("max_anchor_text_length", 140))
    html = fetch_html(source.url, timeout_seconds=timeout_seconds, user_agent=user_agent)
    soup = BeautifulSoup(html, "html.parser")
    results: list[RawListing] = []
    seen: set[tuple[str, str]] = set()
    for anchor in soup.find_all("a", href=True):
        title = collapse_whitespace(anchor.get_text(" ", strip=True))
        if not title or len(title) < min_len or len(title) > max_len:
            continue
        if not _matches_any(title, source.text_allow_patterns):
            continue
        if source.text_deny_patterns and _matches_any(title, source.text_deny_patterns):
            continue
        target_url = _build_link(source, anchor)
        if not target_url or not _path_allowed(source, target_url):
            continue
        key = (title, target_url)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            RawListing(
                source_id=source.id,
                source_name=source.name,
                source_url=source.url,
                title=title,
                url=target_url,
                snippet=_extract_snippet(anchor),
                extras={
                    "source": asdict(source),
                    "anchor_attributes": {k: str(v) for k, v in anchor.attrs.items()},
                },
            )
        )
    return results


def collect_source(source: SourceSpec, defaults: dict[str, object]) -> list[RawListing]:
    if not source.enabled:
        return []
    if source.kind != "anchor_scan":
        raise ValueError(f"Unsupported source kind: {source.kind}")
    return collect_anchor_scan(source, defaults)


def safe_collect_source(source: SourceSpec, defaults: dict[str, object]) -> tuple[list[RawListing], str | None]:
    try:
        return collect_source(source, defaults), None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return [], f"{type(exc).__name__}: {exc}"
