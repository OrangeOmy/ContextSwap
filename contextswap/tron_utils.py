from __future__ import annotations

from typing import Dict

from eth_keys import keys


def evm_to_tron_hex(evm_address: str) -> str:
    addr = evm_address.lower()
    if addr.startswith("0x"):
        addr = addr[2:]
    if len(addr) != 40:
        raise ValueError("EVM address must be 20 bytes")
    return f"41{addr}"


def tron_hex_to_evm(tron_hex: str) -> str:
    addr = tron_hex.lower()
    if addr.startswith("0x"):
        addr = addr[2:]
    if addr.startswith("41") and len(addr) == 42:
        return f"0x{addr[2:]}"
    if len(addr) == 40:
        return f"0x{addr}"
    raise ValueError("Unsupported TRON hex address format")


def sign_txid_hex(txid_hex: str, private_key_hex: str) -> str:
    txid = txid_hex.lower()
    if txid.startswith("0x"):
        txid = txid[2:]
    priv = private_key_hex.lower()
    if priv.startswith("0x"):
        priv = priv[2:]

    if len(txid) != 64:
        raise ValueError("txID must be 32 bytes hex")

    pk = keys.PrivateKey(bytes.fromhex(priv))
    sig = pk.sign_msg_hash(bytes.fromhex(txid))
    signature = sig.r.to_bytes(32, "big") + sig.s.to_bytes(32, "big") + bytes([sig.v])
    return signature.hex()


def extract_transfer_contract(tx: Dict[str, object]) -> Dict[str, object]:
    raw_data = tx.get("raw_data")
    if not isinstance(raw_data, dict):
        raise ValueError("Missing raw_data in transaction")
    contracts = raw_data.get("contract")
    if not isinstance(contracts, list) or not contracts:
        raise ValueError("Missing contract in transaction")
    contract = contracts[0]
    if not isinstance(contract, dict):
        raise ValueError("Invalid contract format")
    parameter = contract.get("parameter", {})
    if not isinstance(parameter, dict):
        raise ValueError("Invalid contract parameter format")
    value = parameter.get("value")
    if not isinstance(value, dict):
        raise ValueError("Invalid contract value format")
    return value
