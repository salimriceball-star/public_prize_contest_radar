from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .config_loader import DEFAULT_CATEGORIES_PATH, DEFAULT_DB_PATH, DEFAULT_SOURCES_PATH
from .pipeline import run_once
from .reporting import render_digest
from .storage import init_db
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
        print(json.dumps({
            "chat_id": chat.chat_id,
            "chat_type": chat.chat_type,
            "label": label,
            "last_message_text": chat.last_message_text,
        }, ensure_ascii=False))
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


def _cmd_run_once(args: argparse.Namespace) -> int:
    source_ids = set(args.source_id) if args.source_id else None
    result = run_once(db_path=args.db, sources_path=args.sources, categories_path=args.categories, enabled_source_ids=source_ids)
    digest = render_digest(result["records"], top_n=args.top)
    print(digest)
    if result["errors"]:
        print("\n[수집 오류]", file=sys.stderr)
        for item in result["errors"]:
            print(f"- {item['source_name']} ({item['source_id']}): {item['error']}", file=sys.stderr)

    if args.save_output:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = Path(args.save_output)
        if not output_path.is_absolute():
            output_path = DEFAULT_OUTPUT_DIR / output_path
        output_path.write_text(digest + "\n", encoding="utf-8")
        print(f"\nSaved digest to {output_path}")

    if args.notify:
        token = args.bot_token or _env("TELEGRAM_BOT_TOKEN")
        chat_id = args.chat_id or _env("TELEGRAM_MASTER_ID")
        if not token or not chat_id:
            print("Notify requested but TELEGRAM_BOT_TOKEN / TELEGRAM_MASTER_ID missing", file=sys.stderr)
            return 2
        try:
            send_message(token, chat_id, digest)
            print(f"\nTelegram sent to {chat_id}")
        except TelegramError as exc:
            print(f"Telegram send failed: {exc}", file=sys.stderr)
            return 3
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="contest-radar", description="Public prize contest radar")
    parser.set_defaults(func=lambda _args: parser.print_help() or 0)
    sub = parser.add_subparsers(dest="command")

    init_db_parser = sub.add_parser("init-db", help="Initialize the SQLite database")
    init_db_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    init_db_parser.set_defaults(func=_cmd_init_db)

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
    run_parser.add_argument("--bot-token")
    run_parser.add_argument("--chat-id")
    run_parser.add_argument("--save-output", default="latest-digest.txt")
    run_parser.set_defaults(func=_cmd_run_once)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
