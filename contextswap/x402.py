import base64
import json
from typing import Any, Dict

from web3 import Web3

CHAIN_ID = 71
NETWORK_ID = f"eip155:{CHAIN_ID}"


def b64encode_json(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def b64decode_json(payload_b64: str) -> Dict[str, Any]:
    raw = base64.b64decode(payload_b64.encode("ascii"))
    return json.loads(raw.decode("utf-8"))


def make_requirements(
    pay_to: str,
    amount_wei: int,
    asset: str = "CFX",
    description: str = "Get current weather data",
    mime_type: str = "application/json",
) -> Dict[str, Any]:
    return {
        "x402Version": 2,
        "accepts": [
            {
                "scheme": "exact",
                "network": NETWORK_ID,
                "payTo": Web3.to_checksum_address(pay_to),
                "amountWei": str(amount_wei),
                "asset": asset,
            }
        ],
        "description": description,
        "mimeType": mime_type,
    }


def build_payment(
    requirements: Dict[str, Any],
    w3: Web3,
    buyer_address: str,
    buyer_private_key: str,
) -> Dict[str, Any]:
    accepts = requirements.get("accepts", [])
    if not accepts:
        raise RuntimeError("No payment requirements")

    requirement = accepts[0]
    pay_to = Web3.to_checksum_address(requirement["payTo"])
    amount = int(requirement["amountWei"])

    nonce = w3.eth.get_transaction_count(buyer_address)
    try:
        gas_price = w3.eth.gas_price
    except Exception:  # noqa: BLE001
        gas_price = w3.to_wei(1, "gwei")

    tx = {
        "to": pay_to,
        "value": amount,
        "gas": 21000,
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": CHAIN_ID,
    }

    signed = w3.eth.account.sign_transaction(tx, buyer_private_key)
    raw_tx = signed.raw_transaction.hex()

    return {
        "x402Version": requirements.get("x402Version", 2),
        "scheme": requirement.get("scheme", "exact"),
        "network": requirement.get("network", NETWORK_ID),
        "from": buyer_address,
        "to": pay_to,
        "amountWei": str(amount),
        "rawTransaction": raw_tx,
    }
