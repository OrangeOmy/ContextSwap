"""
会话相关接口（步骤 3：先 stub Telegram）。
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from tg_manager.api.deps import get_db, get_settings, get_telegram, require_auth
from tg_manager.db.models import Session
from tg_manager.services.session_service import (
    NotFoundError,
    create_or_resume_session_with_telegram,
    end_session_with_telegram_cleanup,
    get_session_or_404,
)

router = APIRouter(prefix="/v1/session", tags=["session"])


class CreateSessionRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1, description="交易唯一 ID")
    buyer_bot_username: str = Field(..., min_length=1, description="买方 bot 用户名")
    seller_bot_username: str = Field(..., min_length=1, description="卖方 bot 用户名")
    initial_prompt: str | None = Field(default=None, description="可选：注入的初始指令")
    market_slug: str | None = Field(default=None, description="可选：polymarket market slug")
    question_dir: str | None = Field(default=None, description="可选：子 bot 写入 md 的目录")
    wait_seconds: int | None = Field(default=None, ge=1, description="可选：主 bot 回收 md 前等待秒数")
    force_reinject: bool = Field(default=False, description="可选：强制重新注入系统消息（用于排障/修复旧会话）")


class EndSessionRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1, description="交易唯一 ID")
    reason: str | None = Field(default=None, description="可选：结束原因（默认 api）")


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


def _require_non_empty(label: str, value: str) -> str:
    v = value.strip()
    if not v:
        raise HTTPException(status_code=422, detail=f"字段 {label} 不能为空")
    return v


_TG_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")


def _规范化bot用户名(label: str, raw: str) -> str:
    """把 buyer/seller 的 bot 用户名规范化为不带 @ 的形式，并做最小校验。"""

    v = (raw or "").strip()
    if v.startswith("@"):
        v = v[1:].strip()
    if not v:
        raise ValueError(f"字段 {label} 不能为空")
    if not _TG_USERNAME_RE.fullmatch(v):
        raise ValueError(f"字段 {label} 必须是 Telegram 用户名（5-32 位，仅字母/数字/下划线，可选前缀@），当前值：{raw!r}")
    if not v.lower().endswith("bot"):
        raise ValueError(f"字段 {label} 需要是 bot 用户名（通常以 bot 结尾），当前值：{raw!r}")
    return v


@router.post("/create", dependencies=[Depends(require_auth)])
async def create_session(request: Request, body: CreateSessionRequest) -> dict[str, Any]:
    conn = get_db(request)
    settings = get_settings(request)
    telegram = get_telegram(request)
    if telegram is None:
        raise HTTPException(
            status_code=500,
            detail="未配置 Telethon（需要 TELETHON_API_ID/TELETHON_API_HASH/TELETHON_SESSION 与 MARKET_CHAT_ID）",
        )
    if not settings.market_chat_id:
        raise HTTPException(status_code=500, detail="缺少 MARKET_CHAT_ID 配置（不应发生）")

    transaction_id = _require_non_empty("transaction_id", body.transaction_id)
    try:
        buyer = _规范化bot用户名("buyer_bot_username", body.buyer_bot_username)
        seller = _规范化bot用户名("seller_bot_username", body.seller_bot_username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    initial_prompt = body.initial_prompt.strip() if body.initial_prompt is not None else None
    if initial_prompt == "":
        initial_prompt = None

    metadata = {
        "buyer_bot_username": buyer,
        "seller_bot_username": seller,
        "initial_prompt": initial_prompt,
        "market_slug": (body.market_slug or settings.delegation_market_slug).strip(),
        "question_dir": (body.question_dir or settings.delegation_question_dir).strip(),
        "wait_seconds": int(body.wait_seconds or settings.delegation_wait_seconds),
        "telegram_stub": False,
    }

    session = await create_or_resume_session_with_telegram(
        conn,
        transaction_id=transaction_id,
        incoming_metadata_json=json.dumps(metadata, ensure_ascii=False),
        market_chat_id=settings.market_chat_id,
        telegram=telegram,
        force_reinject=bool(body.force_reinject),
    )
    return _session_to_dict(session)


@router.get("/{transaction_id}", dependencies=[Depends(require_auth)])
def get_session(request: Request, transaction_id: str) -> dict[str, Any]:
    conn = get_db(request)
    tx = _require_non_empty("transaction_id", transaction_id)
    try:
        session = get_session_or_404(conn, transaction_id=tx)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _session_to_dict(session)


@router.post("/end", dependencies=[Depends(require_auth)])
async def end_session(request: Request, body: EndSessionRequest) -> dict[str, Any]:
    conn = get_db(request)
    transaction_id = _require_non_empty("transaction_id", body.transaction_id)
    reason = body.reason.strip() if body.reason is not None else ""
    if reason == "":
        reason = "api"

    try:
        telegram = get_telegram(request)
        session = await end_session_with_telegram_cleanup(
            conn,
            transaction_id=transaction_id,
            reason=reason,
            telegram=telegram,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _session_to_dict(session)
