import json
import sqlite3
import uuid

from web3 import Web3

from contextswap.facilitator.base import FacilitatorClient
from contextswap.platform.db import models
from contextswap.x402 import NETWORK_ID as CONFLUX_NETWORK_ID, b64encode_json, make_requirements
from contextswap.x402_tron import NETWORK_ID as TRON_NETWORK_ID, make_requirements as make_tron_requirements


class NotFoundError(RuntimeError):
    pass


def generate_transaction_id() -> str:
    return f"tx_{uuid.uuid4().hex}"


def build_requirements(seller: models.Seller, *, network: str = "conflux") -> dict:
    if network == "tron":
        if seller.price_tron_sun is None:
            raise ValueError("seller does not accept Tron payments")
        return make_tron_requirements(
            pay_to=seller.evm_address,
            amount_sun=seller.price_tron_sun,
            description=f"ContextSwap:{seller.seller_id}",
            mime_type="application/json",
        )
    return make_requirements(
        pay_to=seller.evm_address,
        amount_wei=seller.price_conflux_wei,
        description=f"ContextSwap:{seller.seller_id}",
        mime_type="application/json",
    )


def compute_tx_hash(raw_tx: str) -> str:
    raw = (raw_tx or "").strip()
    if not raw:
        raise ValueError("rawTransaction is required")
    if not raw.startswith("0x"):
        raw = f"0x{raw}"
    return Web3.keccak(hexstr=raw).hex()


def compute_payment_id(payment_payload: dict, *, network: str = "conflux") -> str:
    if network == "tron":
        tx = payment_payload.get("transaction") or payment_payload.get("rawTransaction")
        if isinstance(tx, dict):
            txid = tx.get("txID") or tx.get("txid")
        elif isinstance(tx, str):
            try:
                parsed = json.loads(tx)
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid Tron transaction payload") from exc
            txid = parsed.get("txID") or parsed.get("txid")
        else:
            txid = None
        if not txid:
            raise ValueError("Missing txID in Tron transaction")
        return str(txid)
    raw_tx = payment_payload.get("rawTransaction", "")
    return compute_tx_hash(raw_tx)


def verify_and_settle_payment(
    facilitator_client: FacilitatorClient,
    payment_payload: dict,
    requirements: dict,
) -> str:
    verify_resp = facilitator_client.verify_payment(payment_payload, requirements)
    if not verify_resp.get("verified", True):
        raise ValueError("payment verification failed")
    return facilitator_client.settle_payment(payment_payload, requirements)


def create_transaction(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    seller: models.Seller,
    buyer_address: str,
    price_wei: int,
    payment_payload: dict,
    requirements: dict,
    tx_hash: str,
    metadata: dict,
) -> models.Transaction:
    existing = models.get_transaction_by_id(conn, transaction_id=transaction_id)
    if existing is not None:
        return existing

    return models.create_transaction(
        conn,
        transaction_id=transaction_id,
        seller_id=seller.seller_id,
        buyer_address=buyer_address,
        price_wei=int(price_wei),
        status="paid",
        payment_payload_json=json.dumps(payment_payload, separators=(",", ":")),
        requirements_json=json.dumps(requirements, separators=(",", ":")),
        tx_hash=tx_hash,
        chat_id=None,
        message_thread_id=None,
        metadata_json=json.dumps(metadata, separators=(",", ":")),
        error_reason=None,
    )


def attach_session(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    chat_id: str,
    message_thread_id: int,
) -> models.Transaction:
    return models.update_transaction_fields(
        conn,
        transaction_id=transaction_id,
        fields={
            "chat_id": chat_id,
            "message_thread_id": int(message_thread_id),
            "status": "session_created",
        },
    )


def record_tg_manager_error(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    error_reason: str,
) -> models.Transaction:
    return models.update_transaction_fields(
        conn,
        transaction_id=transaction_id,
        fields={"error_reason": error_reason},
    )


def build_payment_response(tx_hash: str, *, network: str = "conflux") -> str:
    if network == "tron":
        network_id = TRON_NETWORK_ID
    else:
        network_id = CONFLUX_NETWORK_ID
    payload = {
        "x402Version": 2,
        "scheme": "exact",
        "network": network_id,
        "txHash": tx_hash,
    }
    return b64encode_json(payload)


def transaction_to_dict(transaction: models.Transaction) -> dict:
    payment_network = None
    try:
        requirements = json.loads(transaction.requirements_json)
        network = requirements.get("accepts", [{}])[0].get("network")
        if network == TRON_NETWORK_ID:
            payment_network = "tron"
        elif network:
            payment_network = "conflux"
    except Exception:  # noqa: BLE001
        payment_network = None
    payment_chain = transaction.payment_chain or payment_network
    metadata = {}
    try:
        metadata = json.loads(transaction.metadata_json) if transaction.metadata_json else {}
    except Exception:  # noqa: BLE001
        pass
    return {
        "transaction_id": transaction.transaction_id,
        "seller_id": transaction.seller_id,
        "buyer_address": transaction.buyer_address,
        "price_wei": transaction.price_wei,
        "payment_chain": payment_chain,
        "payment_network": payment_network,
        "status": transaction.status,
        "tx_hash": transaction.tx_hash,
        "chat_id": transaction.chat_id,
        "message_thread_id": transaction.message_thread_id,
        "metadata": metadata,
        "error_reason": transaction.error_reason,
        "created_at": transaction.created_at,
        "updated_at": transaction.updated_at,
    }
