"""
FastAPI 依赖注入（鉴权、配置、数据库连接等）。
"""

from __future__ import annotations

import sqlite3

from fastapi import Header, HTTPException, Request

from tg_manager.core.config import Settings
from tg_manager.core.security import parse_bearer_token
from tg_manager.services.telethon_service import TelethonService


def get_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        raise RuntimeError("应用未初始化 settings（不应发生）")
    return settings


def get_db(request: Request) -> sqlite3.Connection:
    conn = getattr(request.app.state, "db", None)
    if conn is None:
        raise RuntimeError("应用未初始化数据库连接（不应发生）")
    return conn


def get_telegram(request: Request) -> TelethonService | object | None:
    """获取 Telegram/Telethon 服务对象（若未配置则返回 None）。"""

    return getattr(request.app.state, "telegram", None)


def require_auth(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """校验 Bearer token。

返回：
    - 鉴权通过：返回 None
    - 鉴权失败：抛出 HTTPException（401/403）
    """

    settings = get_settings(request)
    token = parse_bearer_token(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="缺少或不合法的 Authorization 头（需要 Bearer token）")
    if token != settings.api_auth_token:
        raise HTTPException(status_code=403, detail="鉴权失败：token 不匹配")
