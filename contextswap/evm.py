from typing import Any, Dict, Optional

from eth_account import Account
from eth_account._utils import legacy_transactions
from eth_utils import to_checksum_address


def decode_raw_transaction(raw_hex: str) -> Dict[str, Any]:
    raw_hex = raw_hex.lower()
    if raw_hex.startswith("0x"):
        raw_hex = raw_hex[2:]
    raw_bytes = bytes.fromhex(raw_hex)

    tx = legacy_transactions.Transaction.from_bytes(raw_bytes)
    to_addr = to_checksum_address(tx.to) if tx.to else None

    chain_id: Optional[int]
    if tx.v in (27, 28):
        chain_id = None
    else:
        chain_id = (tx.v - 35) // 2

    sender = Account.recover_transaction("0x" + raw_hex)

    return {
        "to": to_addr,
        "value": int(tx.value),
        "chain_id": chain_id,
        "from": to_checksum_address(sender),
    }
