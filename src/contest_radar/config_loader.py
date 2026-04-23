from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import SourceSpec

_BROWSEROS_DETAIL_DEFAULTS = {
    "detail_title_selectors": ["h1", "h2", "[class*='title']", ".title", ".tit", ".subject"],
    "detail_date_selectors": ["time", "[class*='date']", "[class*='time']", "[class*='write']", "[class*='reg']", "[class*='day']", ".info", ".meta", ".summary"],
    "detail_content_selectors": ["article", "main", ".article", ".content", ".view_cont", ".board_view", ".detail", ".entry-content", "[class*='content']", "[class*='view']"],
}


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES_PATH = PROJECT_ROOT / "config" / "sources.yaml"
DEFAULT_CATEGORIES_PATH = PROJECT_ROOT / "config" / "categories.yaml"
DEFAULT_RUNTIME_PATH = PROJECT_ROOT / "config" / "runtime.yaml"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "contest_radar.sqlite3"


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def load_sources(path: str | Path = DEFAULT_SOURCES_PATH) -> tuple[dict[str, Any], list[SourceSpec]]:
    payload = load_yaml(path)
    defaults = payload.get("defaults", {}) or {}
    sources = []
    for raw_source in payload.get("sources", []):
        raw = dict(raw_source)
        if raw.get("kind") == "browseros_anchor_scan" and raw.get("detail_fetch") == "browseros_detail":
            for key, fallback in _BROWSEROS_DETAIL_DEFAULTS.items():
                raw.setdefault(key, defaults.get(key, fallback))
        sources.append(SourceSpec(**raw))
    return defaults, sources


def load_categories(path: str | Path = DEFAULT_CATEGORIES_PATH) -> dict[str, Any]:
    return load_yaml(path)


def load_runtime_config(path: str | Path = DEFAULT_RUNTIME_PATH) -> dict[str, Any]:
    return load_yaml(path)
