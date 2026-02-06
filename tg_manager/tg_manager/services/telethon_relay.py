"""
Topic 内 buyer/seller bot 消息中继（MVP）。

目标：
- buyer bot 发言 -> userbot 发送新消息并 @seller 转述
- seller bot 发言 -> userbot 发送新消息并 @buyer 转述

说明：
- 这是为了绕开“bot 收不到 bot 消息”的 Telegram Bot API 限制。
- 只在 session.status == running 时生效。
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import dataclass

from telethon import TelegramClient, events

from tg_manager.db.models import Session, get_running_session_by_chat_thread
from tg_manager.services.session_service import RELAY_FLUSH_MARKER, SESSION_END_MARKER, end_session_with_telegram_cleanup
from tg_manager.services.telethon_service import TelethonService


def _safe_load_metadata(metadata_json: str) -> dict:
    try:
        data = json.loads(metadata_json or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _normalize_username(raw: str | None) -> str:
    return (raw or "").strip().lstrip("@").strip().lower()


def _truncate(text: str, *, limit: int = 3600) -> str:
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return t[:limit] + "\n…（已截断）"


def _get_reply_to_top_id(message: object) -> int | None:
    reply_to = getattr(message, "reply_to", None)
    if reply_to is None:
        return None
    top_id = getattr(reply_to, "reply_to_top_id", None)
    if isinstance(top_id, int) and top_id > 0:
        return top_id
    # 兼容：某些场景可能只有 reply_to_msg_id
    top_id = getattr(reply_to, "reply_to_msg_id", None)
    if isinstance(top_id, int) and top_id > 0:
        return top_id
    return None


def _contains_marker(text: str, marker: str) -> bool:
    t = (text or "").strip()
    m = (marker or "").strip()
    if not t or not m:
        return False
    return m.casefold() in t.casefold()


def _strip_marker(text: str, marker: str) -> str:
    t = text or ""
    m = (marker or "").strip()
    if not m:
        return t.strip()
    return t.replace(m, "").strip()


@dataclass
class TelethonRelay:
    client: TelegramClient
    conn: sqlite3.Connection
    market_chat_id: str
    end_marker: str = SESSION_END_MARKER
    relay_flush_marker: str = RELAY_FLUSH_MARKER

    def __post_init__(self) -> None:
        if not (self.end_marker or "").strip():
            raise ValueError("结束标记不能为空")
        if not (self.relay_flush_marker or "").strip():
            raise ValueError("转发触发标记不能为空")
        self._lock = asyncio.Lock()
        self._seen_message_ids: set[int] = set()
        self._pending_by_role: dict[tuple[str, str], list[str]] = {}
        self._handler_installed = False

    async def start(self) -> None:
        """注册事件处理器。"""

        if self._handler_installed:
            return

        peer = await self.client.get_input_entity(int(str(self.market_chat_id).strip()))
        self.client.add_event_handler(self._on_new_message, events.NewMessage(chats=peer))
        self._handler_installed = True

    async def stop(self) -> None:
        """卸载事件处理器。"""

        if not self._handler_installed:
            return
        self.client.remove_event_handler(self._on_new_message)
        self._handler_installed = False

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        msg = getattr(event, "message", None)
        if msg is None:
            return

        # 忽略自己发出的消息，避免自我回环
        if getattr(msg, "out", False):
            return

        mid = getattr(msg, "id", None)
        if isinstance(mid, int) and mid in self._seen_message_ids:
            return
        if isinstance(mid, int):
            self._seen_message_ids.add(mid)

        top_id = _get_reply_to_top_id(msg)
        if top_id is None:
            return

        text = getattr(msg, "raw_text", "") or ""
        if not text.strip():
            return

        # 获取 sender username（仅用于识别 buyer/seller）
        sender = await event.get_sender()
        sender_username = _normalize_username(getattr(sender, "username", None))
        if not sender_username:
            return

        async with self._lock:
            session = get_running_session_by_chat_thread(
                self.conn,
                chat_id=str(self.market_chat_id).strip(),
                message_thread_id=int(top_id),
            )

        if session is None:
            return

        await self._maybe_relay(session, sender_username=sender_username, source_text=text)

    async def _maybe_relay(self, session: Session, *, sender_username: str, source_text: str) -> None:
        metadata = _safe_load_metadata(session.metadata_json)
        buyer = _normalize_username(str(metadata.get("buyer_bot_username") or ""))
        seller = _normalize_username(str(metadata.get("seller_bot_username") or ""))
        if not buyer or not seller:
            return

        if sender_username == buyer:
            target = seller
            role = "buyer"
        elif sender_username == seller:
            target = buyer
            role = "seller"
        else:
            return

        relay_body = self._append_pending_and_flush_if_ready(
            session=session,
            sender_username=sender_username,
            source_text=source_text,
        )
        if relay_body is None:
            return

        # 避免把中继消息再次触发（我们只处理中继前的 bot 消息；中继消息来自 userbot，因此 msg.out=True 已挡住）
        relay_text = "\n".join(
            [
                f"@{target}",
                "",
                f"对方（{role}:{sender_username}）说：",
                _truncate(relay_body),
                "",
                "请直接在本 Topic 回复。",
            ]
        )

        peer = await self.client.get_input_entity(int(str(session.chat_id).strip()))
        # 关键：Forum Topic 内发言仍需带 reply_to=topic 顶层消息 id 才能落到正确线程；
        # 这里不再引用“对方原消息”，仅绑定到 topic 根消息，满足“干净消息 + @对方”的要求。
        await self.client.send_message(peer, relay_text, reply_to=int(session.message_thread_id))

        # 关键改动：由服务端决定销毁时机。
        # seller 的消息携带结束标记时，先完成最后一次转发，再立即关闭 Topic 并将会话落库为 ended。
        if role == "seller" and _contains_marker(relay_body, self.end_marker):
            await self._auto_end_session_after_final_forward(session)

    async def _auto_end_session_after_final_forward(self, session: Session) -> None:
        async with self._lock:
            await end_session_with_telegram_cleanup(
                self.conn,
                transaction_id=session.transaction_id,
                reason="end_marker",
                telegram=TelethonService(client=self.client),
            )
            self._clear_pending_for_session(session)

    def _pending_key(self, session: Session, sender_username: str) -> tuple[str, str]:
        return (session.transaction_id, sender_username)

    def _clear_pending_for_session(self, session: Session) -> None:
        tx = session.transaction_id
        for key in [k for k in self._pending_by_role.keys() if k[0] == tx]:
            self._pending_by_role.pop(key, None)

    def _append_pending_and_flush_if_ready(
        self,
        *,
        session: Session,
        sender_username: str,
        source_text: str,
    ) -> str | None:
        key = self._pending_key(session, sender_username)
        queue = self._pending_by_role.setdefault(key, [])
        queue.append(source_text)

        if not _contains_marker(source_text, self.relay_flush_marker):
            return None

        merged = "\n\n".join(queue).strip()
        self._pending_by_role.pop(key, None)
        cleaned = _strip_marker(merged, self.relay_flush_marker)
        if not cleaned:
            return None
        return cleaned
