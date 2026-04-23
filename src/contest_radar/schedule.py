from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

import yaml

from .models import ContestRecord

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEDULE_PATH = PROJECT_ROOT / "config" / "schedule.yaml"
CRON_BLOCK_START = "# public-prize-contest-radar BEGIN"
CRON_BLOCK_END = "# public-prize-contest-radar END"


@dataclass(slots=True)
class ScheduleEntry:
    id: str
    purpose: str
    kst_time: str
    cron_utc: str
    notify: bool


def load_schedule(path: str | Path = DEFAULT_SCHEDULE_PATH) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Schedule config must be a mapping: {path}")
    return payload


def schedule_entries(path: str | Path = DEFAULT_SCHEDULE_PATH) -> list[ScheduleEntry]:
    payload = load_schedule(path)
    entries: list[ScheduleEntry] = []
    for raw in payload.get("entries", []):
        entries.append(
            ScheduleEntry(
                id=str(raw["id"]),
                purpose=str(raw["purpose"]),
                kst_time=str(raw["kst_time"]),
                cron_utc=str(raw["cron_utc"]),
                notify=bool(raw.get("notify", False)),
            )
        )
    return entries


def describe_schedule(path: str | Path = DEFAULT_SCHEDULE_PATH) -> str:
    payload = load_schedule(path)
    timezone = payload.get("timezone", "Asia/Seoul")
    lines = [f"Monitoring timezone: {timezone}"]
    for entry in schedule_entries(path):
        notify_label = "알림 전송" if entry.notify else "무음 수집"
        lines.append(f"- {entry.kst_time} KST | {entry.purpose} | {notify_label}")
    return "\n".join(lines)


def command_for_entry(entry: ScheduleEntry, project_root: str | Path = PROJECT_ROOT) -> str:
    root = Path(project_root)
    script = root / "scripts" / "run_radar.sh"
    log_path = root / "logs" / "cron" / f"{entry.id}.log"
    if entry.id == "due-soon-alert":
        args = ["due-soon", "--public-only", "--min-score", "40"]
    else:
        args = ["run-once", "--top", "10", "--public-only", "--min-score", "40"]
    if entry.notify:
        args.append("--notify")
    command = " ".join([str(script), *args])
    return f"cd {root} && mkdir -p logs/cron && {command} >> {log_path} 2>&1"


def render_crontab(path: str | Path = DEFAULT_SCHEDULE_PATH, project_root: str | Path = PROJECT_ROOT) -> str:
    lines = [
        CRON_BLOCK_START,
        "SHELL=/bin/bash",
        "TZ=UTC",
        "# Times are stored as UTC cron expressions for Asia/Seoul schedule entries.",
    ]
    for entry in schedule_entries(path):
        lines.append(f"# {entry.id}: {entry.kst_time} KST | {entry.purpose}")
        lines.append(f"{entry.cron_utc} {command_for_entry(entry, project_root=project_root)}")
    lines.append(CRON_BLOCK_END)
    return "\n".join(lines)


def filter_due_soon_records(records: Iterable[ContestRecord], today: date, buckets: tuple[int, ...] = (7, 3, 1)) -> dict[int, list[ContestRecord]]:
    grouped: dict[int, list[ContestRecord]] = defaultdict(list)
    for record in records:
        if not record.deadline_date_iso:
            continue
        try:
            deadline = date.fromisoformat(record.deadline_date_iso)
        except ValueError:
            continue
        delta = (deadline - today).days
        if delta in buckets:
            grouped[delta].append(record)
    for bucket in buckets:
        grouped[bucket] = sorted(grouped[bucket], key=lambda item: item.score, reverse=True)
    return dict(grouped)
