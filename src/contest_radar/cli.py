from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config_loader import DEFAULT_CATEGORIES_PATH, DEFAULT_DB_PATH, DEFAULT_SOURCES_PATH
from .pipeline import run_once
from .reporting import render_digest, render_due_soon_digest
from .schedule import DEFAULT_SCHEDULE_PATH, describe_schedule, render_crontab
from .storage import connect, fetch_all_records, init_db
from .telegram import TelegramError, resolve_master_ids, send_message


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


def _maybe_notify(args: argparse.Namespace, body: str) -> int:
    if not getattr(args, "notify", False):
        return 0
    token = args.bot_token or _env("TELEGRAM_BOT_TOKEN")
    chat_id = args.chat_id or _env("TELEGRAM_MASTER_ID")
    if not token or not chat_id:
        print("Notify requested but TELEGRAM_BOT_TOKEN / TELEGRAM_MASTER_ID missing", file=sys.stderr)
        return 2
    try:
        send_message(token, chat_id, body)
        print(f"\nTelegram sent to {chat_id}")
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
    notify_code = _maybe_notify(args, digest)
    if notify_code:
        return notify_code
    return 0


def _cmd_due_soon(args: argparse.Namespace) -> int:
    init_db(args.db)
    with connect(args.db) as conn:
        records = fetch_all_records(conn, limit=args.limit)
    filtered_records = _apply_record_filters(records, public_only=args.public_only, min_score=args.min_score)
    digest = render_due_soon_digest(filtered_records)
    print(digest)
    output_path = _save_output(args.save_output, digest)
    if output_path:
        print(f"\nSaved due-soon digest to {output_path}")
    notify_code = _maybe_notify(args, digest)
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
    due_parser.add_argument("--save-output", default=f"due-soon-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.txt")
    due_parser.set_defaults(func=_cmd_due_soon)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
