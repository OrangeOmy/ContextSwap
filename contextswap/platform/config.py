import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
LEGACY_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "env", ".env"))
DEFAULT_DEMO_MARKET_SLUG = "will-donald-trump-win-the-2028-us-presidential-election"


def _read_bool_env(key: str, default: bool) -> bool:
    raw = os.getenv(key, "").strip().lower()
    if raw == "":
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{key} must be a boolean value")


def _read_int_env(key: str, default: int, *, min_value: int) -> int:
    raw = os.getenv(key, "").strip()
    if raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{key} must be int, got: {raw!r}") from exc
    if value < min_value:
        raise RuntimeError(f"{key} must be >= {min_value}, got: {value}")
    return value


@dataclass(frozen=True)
class Settings:
    sqlite_path: str
    rpc_url: str | None
    tron_rpc_url: str | None
    tron_api_key: str | None
    facilitator_base_url: str | None
    tg_manager_mode: str
    tg_manager_base_url: str | None
    tg_manager_auth_token: str | None
    tg_manager_sqlite_path: str
    tg_manager_market_chat_id: str | None
    telethon_api_id: int | None
    telethon_api_hash: str | None
    telethon_session: str | None
    delegation_market_slug: str
    delegation_question_dir: str
    delegation_wait_seconds: int
    mock_bots_enabled: bool
    mock_bots_json: str | None
    mock_seller_auto_end: bool


def load_settings(env_path: str | None = None) -> Settings:
    if env_path is not None:
        load_dotenv(env_path)
    else:
        loaded = load_dotenv(DEFAULT_ENV_PATH)
        if not loaded:
            load_dotenv(LEGACY_ENV_PATH)

    sqlite_path = (
        os.getenv("SQLITE_PATH", "").strip()
        or os.getenv("CONTEXTSWAP_SQLITE_PATH", "").strip()
        or "./db/contextswap.sqlite3"
    )
    rpc_url = os.getenv("CONFLUX_TESTNET_ENDPOINT", "").strip() or None
    tron_rpc_url = (
        os.getenv("TRON_NILE_ENDPOINT", "").strip()
        or os.getenv("TRON_TESTNET_ENDPOINT", "").strip()
        or os.getenv("TRON_SHASTA_ENDPOINT", "").strip()
        or None
    )
    tron_api_key = os.getenv("TRON_GRID_API_KEY", "").strip() or os.getenv("TRONGRID_API_KEY", "").strip() or None
    facilitator_base_url = os.getenv("FACILITATOR_BASE_URL", "").strip() or None
    tg_manager_mode = os.getenv("TG_MANAGER_MODE", "http").strip().lower() or "http"
    tg_manager_base_url = os.getenv("TG_MANAGER_BASE_URL", "").strip() or None
    tg_manager_auth_token = os.getenv("TG_MANAGER_AUTH_TOKEN", "").strip() or None
    tg_manager_sqlite_path = os.getenv("TG_MANAGER_SQLITE_PATH", "").strip() or sqlite_path
    tg_manager_market_chat_id = os.getenv("MARKET_CHAT_ID", "").strip() or None
    telethon_api_id_raw = os.getenv("TELETHON_API_ID", "").strip()
    telethon_api_id: int | None = None
    if telethon_api_id_raw:
        try:
            telethon_api_id = int(telethon_api_id_raw)
        except ValueError as exc:
            raise RuntimeError(f"TELETHON_API_ID must be int, got: {telethon_api_id_raw!r}") from exc
    telethon_api_hash = os.getenv("TELETHON_API_HASH", "").strip() or None
    telethon_session = os.getenv("TELETHON_SESSION", "").strip() or None
    delegation_market_slug = os.getenv("OPENCLAW_MARKET_SLUG", "").strip() or DEFAULT_DEMO_MARKET_SLUG
    delegation_question_dir = os.getenv("OPENCLAW_QUESTION_DIR", "").strip() or "~/.openclaw/question"
    delegation_wait_seconds = _read_int_env("OPENCLAW_WAIT_SECONDS", 120, min_value=1)
    mock_bots_enabled = _read_bool_env("MOCK_BOTS_ENABLED", False)
    mock_bots_json = os.getenv("MOCK_BOTS_JSON", "").strip() or None
    mock_seller_auto_end = _read_bool_env("MOCK_SELLER_AUTO_END", True)

    if not facilitator_base_url and not rpc_url and not tron_rpc_url:
        raise RuntimeError(
            "Missing CONFLUX_TESTNET_ENDPOINT or TRON_NILE_ENDPOINT (or FACILITATOR_BASE_URL) in env"
        )
    if tg_manager_mode not in {"http", "inprocess"}:
        raise RuntimeError("TG_MANAGER_MODE must be one of: http, inprocess")
    if tg_manager_mode == "http" and tg_manager_base_url and not tg_manager_auth_token:
        raise RuntimeError("Missing TG_MANAGER_AUTH_TOKEN while TG_MANAGER_BASE_URL is set")
    if tg_manager_mode == "inprocess":
        if not tg_manager_auth_token:
            raise RuntimeError("Missing TG_MANAGER_AUTH_TOKEN while TG_MANAGER_MODE is inprocess")
        if not tg_manager_market_chat_id:
            raise RuntimeError("Missing MARKET_CHAT_ID while TG_MANAGER_MODE is inprocess")

    return Settings(
        sqlite_path=sqlite_path,
        rpc_url=rpc_url,
        tron_rpc_url=tron_rpc_url,
        tron_api_key=tron_api_key,
        facilitator_base_url=facilitator_base_url,
        tg_manager_mode=tg_manager_mode,
        tg_manager_base_url=tg_manager_base_url,
        tg_manager_auth_token=tg_manager_auth_token,
        tg_manager_sqlite_path=tg_manager_sqlite_path,
        tg_manager_market_chat_id=tg_manager_market_chat_id,
        telethon_api_id=telethon_api_id,
        telethon_api_hash=telethon_api_hash,
        telethon_session=telethon_session,
        delegation_market_slug=delegation_market_slug,
        delegation_question_dir=delegation_question_dir,
        delegation_wait_seconds=delegation_wait_seconds,
        mock_bots_enabled=mock_bots_enabled,
        mock_bots_json=mock_bots_json,
        mock_seller_auto_end=mock_seller_auto_end,
    )
