import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
LEGACY_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "env", ".env"))


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
    )
