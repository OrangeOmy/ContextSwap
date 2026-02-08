"""
配置加载模块。

设计目标：
1. 统一从环境变量读取配置，避免散落在各处。
2. 提供清晰、中文的错误信息，便于快速排障。
3. 在 MVP 阶段允许部分配置缺省（例如 Telegram 相关），但安全相关配置必须显式提供。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from dotenv import load_dotenv

DEFAULT_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))
LEGACY_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
DEFAULT_DEMO_MARKET_SLUG = "will-donald-trump-win-the-2028-us-presidential-election"


class ConfigError(ValueError):
    """配置错误（缺失、格式不正确等）。"""


def _读取环境变量(
    environ: Mapping[str, str],
    key: str,
) -> str | None:
    value = environ.get(key)
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _读取必填环境变量(
    environ: Mapping[str, str],
    key: str,
) -> str:
    value = _读取环境变量(environ, key)
    if value is None:
        raise ConfigError(f"缺少必填环境变量：{key}")
    return value


def _读取整数环境变量(
    environ: Mapping[str, str],
    key: str,
    *,
    default: int | None = None,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    raw = _读取环境变量(environ, key)
    if raw is None:
        if default is None:
            raise ConfigError(f"缺少必填环境变量：{key}")
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {key} 必须是整数，当前值：{raw!r}") from exc
    if min_value is not None and value < min_value:
        raise ConfigError(f"环境变量 {key} 不能小于 {min_value}，当前值：{value}")
    if max_value is not None and value > max_value:
        raise ConfigError(f"环境变量 {key} 不能大于 {max_value}，当前值：{value}")
    return value


def _读取布尔环境变量(
    environ: Mapping[str, str],
    key: str,
    *,
    default: bool,
) -> bool:
    raw = _读取环境变量(environ, key)
    if raw is None:
        return default
    lowered = raw.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"环境变量 {key} 必须是布尔值（true/false），当前值：{raw!r}")


@dataclass(frozen=True)
class Settings:
    """项目配置。

字段说明：
    api_auth_token:
        对外 HTTP API 的鉴权 token（MVP 先做静态 token）。
    market_chat_id:
        预置超级群 chat_id（方案 B：Topic 会话需要）。
    telethon_api_id:
        Telethon 的 API ID（整数，MTProto 用户账号）。
    telethon_api_hash:
        Telethon 的 API HASH（字符串）。
    telethon_session:
        Telethon StringSession（必须是已授权状态，服务端不做交互登录）。
    session_timeout_minutes:
        会话默认超时（分钟）。
    sqlite_path:
        SQLite 数据库文件路径（后续步骤会使用）。
    log_level:
        日志等级（INFO/DEBUG...），当前仅作为配置保留。
    """

    api_auth_token: str
    market_chat_id: str | None
    telethon_api_id: int | None
    telethon_api_hash: str | None
    telethon_session: str | None
    session_timeout_minutes: int
    sqlite_path: str
    log_level: str
    delegation_market_slug: str
    delegation_question_dir: str
    delegation_wait_seconds: int
    mock_bots_enabled: bool
    mock_bots_json: str | None
    mock_seller_auto_end: bool


def load_settings(
    environ: Mapping[str, str] | None = None,
    *,
    env_path: str | None = None,
) -> Settings:
    """从环境变量加载配置。

注意：
    - 为了方便测试，允许注入 environ。
    - 安全相关配置（API_AUTH_TOKEN）必须存在。
    - Telegram 相关配置在步骤 4 才强制要求，因此这里允许为空。
    """

    if environ is None:
        if env_path is not None:
            load_dotenv(env_path)
        else:
            loaded = load_dotenv(DEFAULT_ENV_PATH)
            if not loaded:
                load_dotenv(LEGACY_ENV_PATH)
        env = os.environ
    else:
        env = environ

    api_auth_token = _读取必填环境变量(env, "API_AUTH_TOKEN")

    market_chat_id = _读取环境变量(env, "MARKET_CHAT_ID")

    telethon_api_id_raw = _读取环境变量(env, "TELETHON_API_ID")
    telethon_api_id: int | None
    if telethon_api_id_raw is None:
        telethon_api_id = None
    else:
        try:
            telethon_api_id = int(telethon_api_id_raw)
        except ValueError as exc:
            raise ConfigError(f"环境变量 TELETHON_API_ID 必须是整数，当前值：{telethon_api_id_raw!r}") from exc

    telethon_api_hash = _读取环境变量(env, "TELETHON_API_HASH")
    telethon_session = _读取环境变量(env, "TELETHON_SESSION")

    session_timeout_minutes = _读取整数环境变量(
        env,
        "SESSION_TIMEOUT_MINUTES",
        default=10,
        min_value=1,
        max_value=24 * 60,
    )

    sqlite_path = (
        _读取环境变量(env, "SQLITE_PATH")
        or _读取环境变量(env, "TG_MANAGER_SQLITE_PATH")
        or _读取环境变量(env, "CONTEXTSWAP_SQLITE_PATH")
        or "./db/contextswap.sqlite3"
    )
    log_level = _读取环境变量(env, "LOG_LEVEL") or "INFO"
    delegation_market_slug = _读取环境变量(env, "OPENCLAW_MARKET_SLUG") or DEFAULT_DEMO_MARKET_SLUG
    delegation_question_dir = _读取环境变量(env, "OPENCLAW_QUESTION_DIR") or "~/.openclaw/question"
    delegation_wait_seconds = _读取整数环境变量(env, "OPENCLAW_WAIT_SECONDS", default=120, min_value=1)
    mock_bots_enabled = _读取布尔环境变量(env, "MOCK_BOTS_ENABLED", default=False)
    mock_bots_json = _读取环境变量(env, "MOCK_BOTS_JSON")
    mock_seller_auto_end = _读取布尔环境变量(env, "MOCK_SELLER_AUTO_END", default=True)

    return Settings(
        api_auth_token=api_auth_token,
        market_chat_id=market_chat_id,
        telethon_api_id=telethon_api_id,
        telethon_api_hash=telethon_api_hash,
        telethon_session=telethon_session,
        session_timeout_minutes=session_timeout_minutes,
        sqlite_path=sqlite_path,
        log_level=log_level,
        delegation_market_slug=delegation_market_slug,
        delegation_question_dir=delegation_question_dir,
        delegation_wait_seconds=delegation_wait_seconds,
        mock_bots_enabled=mock_bots_enabled,
        mock_bots_json=mock_bots_json,
        mock_seller_auto_end=mock_seller_auto_end,
    )
