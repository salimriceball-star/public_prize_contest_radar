from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOCAL_SITE_PACKAGES = _PROJECT_ROOT / ".local" / "site-packages"
if _LOCAL_SITE_PACKAGES.exists():
    local_path = str(_LOCAL_SITE_PACKAGES)
    if local_path not in sys.path:
        sys.path.insert(0, local_path)

__all__: list[str] = []
