from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import anyio

from tg_manager.db.engine import connect_sqlite, init_db
from tg_manager.db.models import Session
from tg_manager.services.session_service import (
    NotFoundError,
    create_or_resume_session_with_telegram,
    end_session_with_telegram_cleanup,
    get_session_or_404,
)
from contextswap.platform.services.session_client import SessionClientError, SessionClientNotFound


_TG_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")


def _normalize_bot_username(label: str, raw: str) -> str:
    value = (raw or "").strip()
    if value.startswith("@"):
        value = value[1:].strip()
    if not value:
        raise ValueError(f"field {label} must not be empty")
    if not _TG_USERNAME_RE.fullmatch(value):
        raise ValueError(f"field {label} must be a valid Telegram username, got: {raw!r}")
    if not value.lower().endswith("bot"):
        raise ValueError(f"field {label} must be a bot username, got: {raw!r}")
    return value


def _run_async(coro):
    # FastAPI 同步路由运行在线程池中：此处必须回到主事件循环执行，
    # 否则 Telethon 连接会因“连接后切换 event loop”而报错。
    try:
        return anyio.from_thread.run(_await_coro, coro)
    except RuntimeError:
        # 非 AnyIO worker thread（如离线脚本/单测）时兜底本地 loop 执行
        return asyncio.run(coro)


async def _await_coro(coro):
    return await coro


def _session_to_dict(session: Session) -> dict[str, Any]:
    return {
        "session_id": session.id,
        "transaction_id": session.transaction_id,
        "chat_id": session.chat_id,
        "message_thread_id": session.message_thread_id,
        "status": session.status,
        "session_start_at": session.session_start_at,
        "session_end_at": session.session_end_at,
        "end_reason": session.end_reason,
        "message_count": session.message_count,
        "participants_json": session.participants_json,
        "metadata_json": session.metadata_json,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


class InProcessTgManagerClient:
    def __init__(
        self,
        *,
        sqlite_path: str,
        auth_token: str,
        market_chat_id: str,
        telegram_service: object | None = None,
    ) -> None:
        token = (auth_token or "").strip()
        if not token:
            raise ValueError("tg_manager auth_token is required")
        chat_id = (market_chat_id or "").strip()
        if not chat_id:
            raise ValueError("tg_manager market_chat_id is required")

        self.auth_token = token
        self.market_chat_id = chat_id
        self.telegram = telegram_service
        self.conn = connect_sqlite(sqlite_path)
        init_db(self.conn)

    def create_session(
        self,
        *,
        transaction_id: str,
        buyer_bot_username: str,
        seller_bot_username: str,
        initial_prompt: str,
        force_reinject: bool = False,
    ) -> dict:
        if self.telegram is None:
            raise SessionClientError(
                "telethon is not configured "
                "(TELETHON_API_ID/TELETHON_API_HASH/TELETHON_SESSION and MARKET_CHAT_ID are required)"
            )

        tx = (transaction_id or "").strip()
        if not tx:
            raise ValueError("transaction_id is required")

        buyer = _normalize_bot_username("buyer_bot_username", buyer_bot_username)
        seller = _normalize_bot_username("seller_bot_username", seller_bot_username)
        prompt = (initial_prompt or "").strip() or None

        metadata = {
            "buyer_bot_username": buyer,
            "seller_bot_username": seller,
            "initial_prompt": prompt,
            "telegram_stub": False,
        }

        session = _run_async(
            create_or_resume_session_with_telegram(
                self.conn,
                transaction_id=tx,
                incoming_metadata_json=json.dumps(metadata, ensure_ascii=False),
                market_chat_id=self.market_chat_id,
                telegram=self.telegram,  # type: ignore[arg-type]
                force_reinject=bool(force_reinject),
            )
        )
        return _session_to_dict(session)

    def get_session(self, *, transaction_id: str) -> dict:
        tx = (transaction_id or "").strip()
        if not tx:
            raise ValueError("transaction_id is required")
        try:
            session = get_session_or_404(self.conn, transaction_id=tx)
        except NotFoundError as exc:
            raise SessionClientNotFound(str(exc)) from exc
        return _session_to_dict(session)

    def end_session(self, *, transaction_id: str, reason: str | None = None) -> dict:
        tx = (transaction_id or "").strip()
        if not tx:
            raise ValueError("transaction_id is required")
        resolved_reason = (reason or "").strip() or "api"
        try:
            session = _run_async(
                end_session_with_telegram_cleanup(
                    self.conn,
                    transaction_id=tx,
                    reason=resolved_reason,
                    telegram=self.telegram,  # type: ignore[arg-type]
                )
            )
        except NotFoundError as exc:
            raise SessionClientNotFound(str(exc)) from exc
        return _session_to_dict(session)

    def close(self) -> None:
        self.conn.close()
