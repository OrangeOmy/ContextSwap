from __future__ import annotations

import asyncio
import json
import re
import sqlite3
from dataclasses import dataclass

from telethon import TelegramClient, events

from tg_manager.db.models import get_running_session_by_chat_thread
from tg_manager.services.session_service import RELAY_FLUSH_MARKER, SESSION_END_MARKER
from tg_manager.services.telethon_relay import TelethonRelay

_MENTION_RE = re.compile(r"@([A-Za-z0-9_]{5,32})")


def _normalize_username(raw: str | None) -> str:
    return (raw or "").strip().lstrip("@").strip().lower()


def _get_reply_to_top_id(message: object) -> int | None:
    reply_to = getattr(message, "reply_to", None)
    if reply_to is None:
        return None
    top_id = getattr(reply_to, "reply_to_top_id", None)
    if isinstance(top_id, int) and top_id > 0:
        return top_id
    fallback = getattr(reply_to, "reply_to_msg_id", None)
    if isinstance(fallback, int) and fallback > 0:
        return fallback
    return None


def _safe_load_metadata(metadata_json: str) -> dict:
    try:
        data = json.loads(metadata_json or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def build_default_mock_bots(*, market_slug: str) -> dict[str, str]:
    slug = market_slug.strip() or "will-donald-trump-win-the-2028-us-presidential-election"
    return {
        "polling_data_bot": (
            f"[Polling Brief] market_slug={slug}; as_of=2026-02-08; "
            "implied_probability=0.46; signal=flat_to_slightly_down; "
            "basis=state-level mixed polling + undecided share persistence."
        ),
        "official_media_bot": (
            f"[Official Media Brief] market_slug={slug}; as_of=2026-02-08; "
            "implied_probability=0.44; signal=cautious; "
            "basis=policy-headline cycle + institutional commentary lag."
        ),
        "social_signal_bot": (
            f"[Social Signal Brief] market_slug={slug}; as_of=2026-02-08; "
            "implied_probability=0.49; signal=noisy_bullish; "
            "basis=engagement acceleration + polarized sentiment skew."
        ),
    }


def parse_mock_bots(*, enabled: bool, raw_json: str | None, market_slug: str) -> dict[str, str]:
    if not enabled:
        return {}
    if not raw_json:
        return build_default_mock_bots(market_slug=market_slug)

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid MOCK_BOTS_JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Invalid MOCK_BOTS_JSON: top-level must be an object")

    parsed: dict[str, str] = {}
    for key, value in payload.items():
        username = _normalize_username(str(key))
        if not username:
            continue
        text = str(value).strip()
        if not text:
            continue
        parsed[username] = text
    return parsed


@dataclass
class MockBotRelay:
    client: TelegramClient
    conn: sqlite3.Connection
    market_chat_id: str
    relay: TelethonRelay
    responses: dict[str, str]
    seller_auto_end: bool = True

    def __post_init__(self) -> None:
        self._lock = asyncio.Lock()
        self._seen_message_ids: set[int] = set()
        self._handler_installed = False

    async def start(self) -> None:
        if self._handler_installed or not self.responses:
            return

        peer = await self.client.get_input_entity(int(str(self.market_chat_id).strip()))
        self.client.add_event_handler(self._on_new_message, events.NewMessage(chats=peer))
        self._handler_installed = True

    async def stop(self) -> None:
        if not self._handler_installed:
            return
        self.client.remove_event_handler(self._on_new_message)
        self._handler_installed = False

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        msg = getattr(event, "message", None)
        if msg is None:
            return

        mid = getattr(msg, "id", None)
        if isinstance(mid, int) and mid in self._seen_message_ids:
            return
        if isinstance(mid, int):
            self._seen_message_ids.add(mid)

        top_id = _get_reply_to_top_id(msg)
        if top_id is None:
            return

        text = (getattr(msg, "raw_text", "") or "").strip()
        if not text:
            return
        if "交易会话已创建（Telegram Topic）" in text:
            return

        mentions = {_normalize_username(m.group(1)) for m in _MENTION_RE.finditer(text)}
        if not mentions:
            return

        async with self._lock:
            session = get_running_session_by_chat_thread(
                self.conn,
                chat_id=str(self.market_chat_id).strip(),
                message_thread_id=int(top_id),
            )

        if session is None:
            return

        metadata = _safe_load_metadata(session.metadata_json)
        seller_username = _normalize_username(str(metadata.get("seller_bot_username") or ""))
        if not seller_username:
            return
        if seller_username not in mentions:
            return

        mock_body = self.responses.get(seller_username, "").strip()
        if not mock_body:
            return

        suffix: list[str] = []
        if self.seller_auto_end:
            suffix.append(SESSION_END_MARKER)
        suffix.append(RELAY_FLUSH_MARKER)
        source_text = f"{mock_body}\n\n{' '.join(suffix)}" if suffix else mock_body

        await self.relay.relay_as_username(
            session,
            sender_username=seller_username,
            source_text=source_text,
        )
