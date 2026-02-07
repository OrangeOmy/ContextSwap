import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "env", ".env")


@dataclass(frozen=True)
class Settings:
    sqlite_path: str
    rpc_url: str | None
    facilitator_base_url: str | None
    tg_manager_base_url: str | None
    tg_manager_auth_token: str | None


def load_settings(env_path: str | None = None) -> Settings:
    path = env_path or DEFAULT_ENV_PATH
    load_dotenv(path)

    sqlite_path = os.getenv("CONTEXTSWAP_SQLITE_PATH", "./db/contextswap.sqlite3").strip() or "./db/contextswap.sqlite3"
    rpc_url = os.getenv("CONFLUX_TESTNET_ENDPOINT", "").strip() or None
    facilitator_base_url = os.getenv("FACILITATOR_BASE_URL", "").strip() or None
    tg_manager_base_url = os.getenv("TG_MANAGER_BASE_URL", "").strip() or None
    tg_manager_auth_token = os.getenv("TG_MANAGER_AUTH_TOKEN", "").strip() or None

    if not facilitator_base_url and not rpc_url:
        raise RuntimeError("Missing CONFLUX_TESTNET_ENDPOINT or FACILITATOR_BASE_URL in env")
    if tg_manager_base_url and not tg_manager_auth_token:
        raise RuntimeError("Missing TG_MANAGER_AUTH_TOKEN while TG_MANAGER_BASE_URL is set")

    return Settings(
        sqlite_path=sqlite_path,
        rpc_url=rpc_url,
        facilitator_base_url=facilitator_base_url,
        tg_manager_base_url=tg_manager_base_url,
        tg_manager_auth_token=tg_manager_auth_token,
    )
