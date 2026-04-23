from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .browseros_cdp import capture_url_screenshot
from .config_loader import DEFAULT_CATEGORIES_PATH, DEFAULT_DB_PATH, DEFAULT_SOURCES_PATH
from .pipeline import run_once
from .reporting import render_digest, render_due_soon_digest
from .schedule import DEFAULT_SCHEDULE_PATH, describe_schedule, filter_due_soon_records, render_crontab
from .storage import connect, fetch_all_records, init_db
from .telegram import TelegramError, resolve_master_ids, send_message, send_message_with_photos


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "logs" / "output"


def _env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value else None


def _cmd_init_db(args: argparse.Namespace) -> int:
    init_db(args.db)
    print(f"Initialized DB: {args.db}")
    return 0


def _cmd_show_schedule(args: argparse.Namespace) -> int:
    print(describe_schedule(args.schedule))
    return 0


def _cmd_render_crontab(args: argparse.Namespace) -> int:
    print(render_crontab(args.schedule))
    return 0


def _cmd_resolve_master_id(args: argparse.Namespace) -> int:
    token = args.bot_token or _env("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN not set", file=sys.stderr)
        return 2
    chats = resolve_master_ids(token)
    if not chats:
        print("No Telegram updates found. Send /start or any message to the bot, then run again.")
        return 1
    for chat in chats:
        label = chat.title or chat.username or chat.first_name or "unknown"
        print(
            json.dumps(
                {
                    "chat_id": chat.chat_id,
                    "chat_type": chat.chat_type,
                    "label": label,
                    "last_message_text": chat.last_message_text,
                },
                ensure_ascii=False,
            )
        )
    return 0


def _cmd_send_test(args: argparse.Namespace) -> int:
    token = args.bot_token or _env("TELEGRAM_BOT_TOKEN")
    chat_id = args.chat_id or _env("TELEGRAM_MASTER_ID")
    if not token or not chat_id:
        print("Need TELEGRAM_BOT_TOKEN and TELEGRAM_MASTER_ID (or --chat-id)", file=sys.stderr)
        return 2
    send_message(token, chat_id, args.text)
    print(f"Sent test message to {chat_id}")
    return 0


def _save_output(path_value: str | None, body: str) -> Path | None:
    if not path_value:
        return None
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = Path(path_value)
    if not output_path.is_absolute():
        output_path = DEFAULT_OUTPUT_DIR / output_path
    output_path.write_text(body + "\n", encoding="utf-8")
    return output_path


def _safe_screenshot_stem(record: object, fallback: str) -> str:
    fingerprint = str(getattr(record, "fingerprint", "") or "").strip()
    title = str(getattr(record, "title", "") or "").strip()
    source_id = str(getattr(record, "source_id", "") or "").strip()
    raw = fingerprint or "-".join(part for part in [source_id, title[:40]] if part) or fallback
    safe = re.sub(r"[^0-9A-Za-z가-힣._-]+", "-", raw).strip("-._")
    return (safe or fallback)[:80]


def _capture_notification_screenshots(
    records,
    top_n: int,
    output_dir: Path | None = None,
    wait_seconds: float = 3.0,
) -> list[Path]:
    if top_n <= 0:
        return []
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_dir = output_dir or (PROJECT_ROOT / "logs" / "screenshots" / f"telegram-{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshots: list[Path] = []
    for idx, record in enumerate(list(records)[:top_n], start=1):
        url = str(getattr(record, "url", "") or "").strip()
        if not url:
            continue
        output_path = output_dir / f"{idx:02d}-{_safe_screenshot_stem(record, f'record-{idx}')}.png"
        try:
            screenshots.append(capture_url_screenshot(url, output_path, wait_seconds=wait_seconds))
        except Exception as exc:
            print(f"Screenshot capture failed for {url}: {exc}", file=sys.stderr)
    return screenshots


def _notification_screenshot_paths(args: argparse.Namespace, records, default_top: int) -> list[Path]:
    if not getattr(args, "notify", False) or not getattr(args, "attach_screenshots", True):
        return []
    screenshot_top = getattr(args, "screenshot_top", None)
    top_n = default_top if screenshot_top is None else int(screenshot_top)
    screenshot_dir = getattr(args, "screenshot_dir", None)
    output_dir = Path(screenshot_dir) if screenshot_dir else None
    wait_seconds = float(getattr(args, "screenshot_wait_seconds", 3.0))
    return _capture_notification_screenshots(records, top_n=top_n, output_dir=output_dir, wait_seconds=wait_seconds)


def _digest_notification_records(records, top_n: int):
    return sorted(records, key=lambda item: item.score, reverse=True)[:top_n]


def _due_soon_notification_records(records, today=None):
    today = today or datetime.utcnow().date()
    grouped = filter_due_soon_records(records, today=today)
    selected = []
    for bucket in (7, 3, 1):
        selected.extend(grouped.get(bucket, [])[:10])
    return selected


def _maybe_notify(args: argparse.Namespace, body: str, photo_paths: list[str | Path] | None = None) -> int:
    if not getattr(args, "notify", False):
        return 0
    token = args.bot_token or _env("TELEGRAM_BOT_TOKEN")
    chat_id = args.chat_id or _env("TELEGRAM_MASTER_ID")
    if not token or not chat_id:
        print("Notify requested but TELEGRAM_BOT_TOKEN / TELEGRAM_MASTER_ID missing", file=sys.stderr)
        return 2
    photos = list(photo_paths or [])
    try:
        send_message_with_photos(token, chat_id, body, photos)
        suffix = f" with {len(photos)} screenshot(s)" if photos else ""
        print(f"\nTelegram sent to {chat_id}{suffix}")
        return 0
    except TelegramError as exc:
        print(f"Telegram send failed: {exc}", file=sys.stderr)
        return 3


def _apply_record_filters(records, public_only: bool, min_score: int):
    filtered = list(records)
    if public_only:
        filtered = [record for record in filtered if record.public_sector]
    if min_score > 0:
        filtered = [record for record in filtered if record.score >= min_score]
    return filtered


def _cmd_run_once(args: argparse.Namespace) -> int:
    source_ids = set(args.source_id) if args.source_id else None
    result = run_once(db_path=args.db, sources_path=args.sources, categories_path=args.categories, enabled_source_ids=source_ids)
    records_key = "new_records" if args.new_only else "records"
    filtered_records = _apply_record_filters(result[records_key], public_only=args.public_only, min_score=args.min_score)
    digest = render_digest(filtered_records, top_n=args.top)
    print(digest)
    if result["errors"]:
        print("\n[수집 오류]", file=sys.stderr)
        for item in result["errors"]:
            print(f"- {item['source_name']} ({item['source_id']}): {item['error']}", file=sys.stderr)
    output_path = _save_output(args.save_output, digest)
    if output_path:
        print(f"\nSaved digest to {output_path}")
    digest_records = _digest_notification_records(filtered_records, args.top)
    photo_paths = _notification_screenshot_paths(args, digest_records, default_top=args.top)
    notify_code = _maybe_notify(args, digest, photo_paths)
    if notify_code:
        return notify_code
    return 0


def _cmd_due_soon(args: argparse.Namespace) -> int:
    init_db(args.db)
    with connect(args.db) as conn:
        records = fetch_all_records(conn, limit=args.limit)
    filtered_records = _apply_record_filters(records, public_only=args.public_only, min_score=args.min_score)
    today = datetime.utcnow().date()
    digest = render_due_soon_digest(filtered_records, today=today)
    print(digest)
    output_path = _save_output(args.save_output, digest)
    if output_path:
        print(f"\nSaved due-soon digest to {output_path}")
    notification_records = _due_soon_notification_records(filtered_records, today=today)
    photo_paths = _notification_screenshot_paths(args, notification_records, default_top=min(args.limit, 10))
    notify_code = _maybe_notify(args, digest, photo_paths)
    if notify_code:
        return notify_code
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="contest-radar", description="Public prize contest radar")
    parser.set_defaults(func=lambda _args: parser.print_help() or 0)
    sub = parser.add_subparsers(dest="command")

    init_db_parser = sub.add_parser("init-db", help="Initialize the SQLite database")
    init_db_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    init_db_parser.set_defaults(func=_cmd_init_db)

    schedule_parser = sub.add_parser("show-schedule", help="Show monitoring and alert schedule")
    schedule_parser.add_argument("--schedule", default=str(DEFAULT_SCHEDULE_PATH))
    schedule_parser.set_defaults(func=_cmd_show_schedule)

    crontab_parser = sub.add_parser("render-crontab", help="Render the managed UTC crontab block")
    crontab_parser.add_argument("--schedule", default=str(DEFAULT_SCHEDULE_PATH))
    crontab_parser.set_defaults(func=_cmd_render_crontab)

    resolve_parser = sub.add_parser("resolve-master-id", help="Resolve Telegram chat ids from bot updates")
    resolve_parser.add_argument("--bot-token")
    resolve_parser.set_defaults(func=_cmd_resolve_master_id)

    send_parser = sub.add_parser("send-test", help="Send a Telegram test message")
    send_parser.add_argument("--bot-token")
    send_parser.add_argument("--chat-id")
    send_parser.add_argument("--text", default="contest radar test")
    send_parser.set_defaults(func=_cmd_send_test)

    run_parser = sub.add_parser("run-once", help="Collect, score, store, and optionally notify")
    run_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    run_parser.add_argument("--sources", default=str(DEFAULT_SOURCES_PATH))
    run_parser.add_argument("--categories", default=str(DEFAULT_CATEGORIES_PATH))
    run_parser.add_argument("--top", type=int, default=10)
    run_parser.add_argument("--source-id", action="append")
    run_parser.add_argument("--notify", action="store_true")
    run_parser.add_argument("--new-only", action="store_true", help="Render/notify only records first inserted in this run")
    run_parser.add_argument("--public-only", action="store_true")
    run_parser.add_argument("--min-score", type=int, default=0)
    run_parser.add_argument("--bot-token")
    run_parser.add_argument("--chat-id")
    run_parser.add_argument("--screenshot-top", type=int, help="Attach screenshots for the first N notified records; defaults to --top")
    run_parser.add_argument("--screenshot-dir", help="Directory for Telegram notification screenshots")
    run_parser.add_argument("--screenshot-wait-seconds", type=float, default=3.0)
    run_parser.add_argument("--no-screenshots", dest="attach_screenshots", action="store_false", help="Disable screenshot attachments when notifying")
    run_parser.set_defaults(attach_screenshots=True)
    run_parser.add_argument("--save-output", default=f"latest-digest-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.txt")
    run_parser.set_defaults(func=_cmd_run_once)

    due_parser = sub.add_parser("due-soon", help="Render D-7/D-3/D-1 due-soon alerts from stored records")
    due_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    due_parser.add_argument("--limit", type=int, default=500)
    due_parser.add_argument("--notify", action="store_true")
    due_parser.add_argument("--public-only", action="store_true")
    due_parser.add_argument("--min-score", type=int, default=0)
    due_parser.add_argument("--bot-token")
    due_parser.add_argument("--chat-id")
    due_parser.add_argument("--screenshot-top", type=int, default=10, help="Attach screenshots for the first N due-soon records")
    due_parser.add_argument("--screenshot-dir", help="Directory for Telegram notification screenshots")
    due_parser.add_argument("--screenshot-wait-seconds", type=float, default=3.0)
    due_parser.add_argument("--no-screenshots", dest="attach_screenshots", action="store_false", help="Disable screenshot attachments when notifying")
    due_parser.set_defaults(attach_screenshots=True)
    due_parser.add_argument("--save-output", default=f"due-soon-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.txt")
    due_parser.set_defaults(func=_cmd_due_soon)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
