import base64
import json
from typing import Any, Dict

import requests
from eth_utils import to_checksum_address

from contextswap.tron_utils import evm_to_tron_hex, sign_txid_hex

# Tron Shasta JSON-RPC (eth_chainId) returns 0x94a9059e.
CHAIN_ID = 2494104990
NETWORK_ID = f"eip155:{CHAIN_ID}"
SUN_PER_TRX = 10**6
DEFAULT_PRICE_SUN = 1_000_000


def b64encode_json(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def b64decode_json(payload_b64: str) -> Dict[str, Any]:
    raw = base64.b64decode(payload_b64.encode("ascii"))
    return json.loads(raw.decode("utf-8"))


def make_requirements(
    pay_to: str,
    amount_sun: int,
    asset: str = "TRX",
    description: str = "Get current weather data",
    mime_type: str = "application/json",
) -> Dict[str, Any]:
    return {
        "x402Version": 2,
        "accepts": [
            {
                "scheme": "exact",
                "network": NETWORK_ID,
                "payTo": to_checksum_address(pay_to),
                # Tron JSON-RPC uses sun (1 TRX = 1e6) as the base unit.
                "amountWei": str(amount_sun),
                "asset": asset,
            }
        ],
        "description": description,
        "mimeType": mime_type,
    }


def build_payment(
    requirements: Dict[str, Any],
    rpc_url: str,
    buyer_address: str,
    buyer_private_key: str,
    api_key: str | None = None,
) -> Dict[str, Any]:
    accepts = requirements.get("accepts", [])
    if not accepts:
        raise RuntimeError("No payment requirements")

    requirement = accepts[0]
    amount = int(requirement["amountWei"])
    pay_to = requirement["payTo"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["TRON-PRO-API-KEY"] = api_key

    create_payload = {
        "to_address": evm_to_tron_hex(pay_to),
        "owner_address": evm_to_tron_hex(buyer_address),
        "amount": amount,
        "visible": False,
    }
    resp = requests.post(
        f"{rpc_url.rstrip('/')}/wallet/createtransaction",
        json=create_payload,
        headers=headers,
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(resp.text)
    unsigned_tx = resp.json()
    txid = unsigned_tx.get("txID") or unsigned_tx.get("txid")
    if not txid:
        raise RuntimeError("Missing txID in create transaction response")

    signature = sign_txid_hex(txid, buyer_private_key)
    signed_tx = dict(unsigned_tx)
    signed_tx["signature"] = [signature]
    signed_tx.setdefault("visible", False)

    return {
        "x402Version": requirements.get("x402Version", 2),
        "scheme": requirement.get("scheme", "exact"),
        "network": requirement.get("network", NETWORK_ID),
        "from": buyer_address,
        "to": pay_to,
        "amountWei": str(amount),
        "transaction": signed_tx,
    }
