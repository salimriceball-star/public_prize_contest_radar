from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class TelegramError(RuntimeError):
    pass


@dataclass(slots=True)
class TelegramChat:
    chat_id: int
    chat_type: str
    username: str | None
    title: str | None
    first_name: str | None
    last_message_text: str | None


def _api_get(token: str, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    url = f"https://api.telegram.org/bot{token}/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.load(response)
    if not payload.get("ok"):
        raise TelegramError(f"Telegram API error: {payload}")
    return payload


def _api_post(token: str, method: str, data: dict[str, Any]) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not payload.get("ok"):
        raise TelegramError(f"Telegram API error: {payload}")
    return payload


def resolve_master_ids(token: str) -> list[TelegramChat]:
    payload = _api_get(token, "getUpdates")
    chats: dict[int, TelegramChat] = {}
    for update in payload.get("result", []):
        message = update.get("message") or update.get("edited_message") or update.get("channel_post")
        if not message:
            continue
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            continue
        chats[int(chat_id)] = TelegramChat(
            chat_id=int(chat_id),
            chat_type=str(chat.get("type", "unknown")),
            username=chat.get("username"),
            title=chat.get("title"),
            first_name=chat.get("first_name"),
            last_message_text=message.get("text"),
        )
    return list(chats.values())


def send_message(token: str, chat_id: str | int, text: str) -> dict[str, Any]:
    return _api_post(token, "sendMessage", {"chat_id": str(chat_id), "text": text[:4000]})
