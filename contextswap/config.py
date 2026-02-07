import os
from dataclasses import dataclass

from dotenv import load_dotenv
from eth_utils import to_checksum_address

DEFAULT_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
LEGACY_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "env", ".env"))


@dataclass(frozen=True)
class EnvConfig:
    rpc_url: str
    buyer_address: str
    buyer_private_key: str
    seller_address: str


@dataclass(frozen=True)
class TronEnvConfig:
    rpc_url: str
    api_key: str | None
    buyer_address: str
    buyer_private_key: str
    seller_address: str


def load_env(env_path: str | None = None) -> EnvConfig:
    if env_path is not None:
        load_dotenv(env_path)
    else:
        loaded = load_dotenv(DEFAULT_ENV_PATH)
        if not loaded:
            load_dotenv(LEGACY_ENV_PATH)

    rpc_url = os.getenv("CONFLUX_TESTNET_ENDPOINT", "").strip()
    buyer_address = os.getenv("CONFLUX_TESTNET_SENDER_ADDRESS", "").strip()
    seller_address = os.getenv("CONFLUX_TESTNET_RECIPIENT_ADDRESS", "").strip()
    buyer_private_key = os.getenv("CONFLUX_TESTNET_PRIVATE_KEY_1", "").strip()

    if not rpc_url:
        raise RuntimeError("Missing CONFLUX_TESTNET_ENDPOINT in .env")
    if not buyer_address:
        raise RuntimeError("Missing CONFLUX_TESTNET_SENDER_ADDRESS in .env")
    if not seller_address:
        raise RuntimeError("Missing CONFLUX_TESTNET_RECIPIENT_ADDRESS in .env")
    if not buyer_private_key:
        raise RuntimeError("Missing CONFLUX_TESTNET_PRIVATE_KEY_1 in .env")

    if not buyer_private_key.startswith("0x"):
        buyer_private_key = f"0x{buyer_private_key}"

    return EnvConfig(
        rpc_url=rpc_url,
        buyer_address=to_checksum_address(buyer_address),
        buyer_private_key=buyer_private_key,
        seller_address=to_checksum_address(seller_address),
    )


def load_tron_env(env_path: str | None = None) -> TronEnvConfig:
    if env_path is not None:
        load_dotenv(env_path)
    else:
        loaded = load_dotenv(DEFAULT_ENV_PATH)
        if not loaded:
            load_dotenv(LEGACY_ENV_PATH)

    rpc_url = (
        os.getenv("TRON_NILE_ENDPOINT", "").strip()
        or os.getenv("TRON_TESTNET_ENDPOINT", "").strip()
        or os.getenv("TRON_SHASTA_ENDPOINT", "").strip()
    )
    api_key = os.getenv("TRON_GRID_API_KEY", "").strip() or os.getenv("TRONGRID_API_KEY", "").strip() or None

    buyer_address = os.getenv("TRON_TESTNET_SENDER_ADDRESS", "").strip() or os.getenv(
        "CONFLUX_TESTNET_SENDER_ADDRESS", ""
    ).strip()
    seller_address = os.getenv("TRON_TESTNET_RECIPIENT_ADDRESS", "").strip() or os.getenv(
        "CONFLUX_TESTNET_RECIPIENT_ADDRESS", ""
    ).strip()
    buyer_private_key = os.getenv("TRON_TESTNET_PRIVATE_KEY_1", "").strip() or os.getenv(
        "CONFLUX_TESTNET_PRIVATE_KEY_1", ""
    ).strip()

    if not rpc_url:
        raise RuntimeError("Missing TRON_SHASTA_ENDPOINT or TRON_TESTNET_ENDPOINT in .env")
    if not buyer_address:
        raise RuntimeError("Missing TRON_TESTNET_SENDER_ADDRESS or CONFLUX_TESTNET_SENDER_ADDRESS in .env")
    if not seller_address:
        raise RuntimeError("Missing TRON_TESTNET_RECIPIENT_ADDRESS or CONFLUX_TESTNET_RECIPIENT_ADDRESS in .env")
    if not buyer_private_key:
        raise RuntimeError("Missing TRON_TESTNET_PRIVATE_KEY_1 or CONFLUX_TESTNET_PRIVATE_KEY_1 in .env")

    if not buyer_private_key.startswith("0x"):
        buyer_private_key = f"0x{buyer_private_key}"

    return TronEnvConfig(
        rpc_url=rpc_url,
        api_key=api_key,
        buyer_address=to_checksum_address(buyer_address),
        buyer_private_key=buyer_private_key,
        seller_address=to_checksum_address(seller_address),
    )
