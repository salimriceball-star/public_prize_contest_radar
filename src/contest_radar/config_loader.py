from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import SourceSpec


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES_PATH = PROJECT_ROOT / "config" / "sources.yaml"
DEFAULT_CATEGORIES_PATH = PROJECT_ROOT / "config" / "categories.yaml"
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
    sources = [SourceSpec(**raw) for raw in payload.get("sources", [])]
    return defaults, sources


def load_categories(path: str | Path = DEFAULT_CATEGORIES_PATH) -> dict[str, Any]:
    return load_yaml(path)
