from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse


_whitespace_re = re.compile(r"\s+")
_strip_title_re = re.compile(r"[^0-9a-z가-힣]+", re.IGNORECASE)
_deadline_re = re.compile(r"(~\s*[0-9]{1,2}/[0-9]{1,2}|마감\s*[0-9]{1,2}/[0-9]{1,2}|[0-9]{4}[.-][0-9]{1,2}[.-][0-9]{1,2})")
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


def extract_deadline_text(text: str) -> str | None:
    match = _deadline_re.search(text or "")
    return match.group(1).strip() if match else None
