import os
from dataclasses import dataclass

from dotenv import load_dotenv
from eth_utils import to_checksum_address

DEFAULT_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "env", ".env")


@dataclass(frozen=True)
class EnvConfig:
    rpc_url: str
    buyer_address: str
    buyer_private_key: str
    seller_address: str


def load_env(env_path: str | None = None) -> EnvConfig:
    path = env_path or DEFAULT_ENV_PATH
    load_dotenv(path)

    rpc_url = os.getenv("CONFLUX_TESTNET_ENDPOINT", "").strip()
    buyer_address = os.getenv("CONFLUX_TESTNET_SENDER_ADDRESS", "").strip()
    seller_address = os.getenv("CONFLUX_TESTNET_RECIPIENT_ADDRESS", "").strip()
    buyer_private_key = os.getenv("CONFLUX_TESTNET_PRIVATE_KEY_1", "").strip()

    if not rpc_url:
        raise RuntimeError("Missing CONFLUX_TESTNET_ENDPOINT in env/.env")
    if not buyer_address:
        raise RuntimeError("Missing CONFLUX_TESTNET_SENDER_ADDRESS in env/.env")
    if not seller_address:
        raise RuntimeError("Missing CONFLUX_TESTNET_RECIPIENT_ADDRESS in env/.env")
    if not buyer_private_key:
        raise RuntimeError("Missing CONFLUX_TESTNET_PRIVATE_KEY_1 in env/.env")

    if not buyer_private_key.startswith("0x"):
        buyer_private_key = f"0x{buyer_private_key}"

    return EnvConfig(
        rpc_url=rpc_url,
        buyer_address=to_checksum_address(buyer_address),
        buyer_private_key=buyer_private_key,
        seller_address=to_checksum_address(seller_address),
    )
